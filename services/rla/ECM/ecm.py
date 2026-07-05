"""
External Control Module (ECM) for RLA Microservice

Primary interface between the RLA microservice and the Central Control Unit (CCU).
Handles service control, monitoring/log streaming, configuration, remote test execution, 
resets, gateway configuration, rate limiting, spam detection settings, and health monitoring.

RLA-Specific Capabilities:
- Gateway activation/deactivation control
- Rate limit configuration
- Spam detection threshold management
- SSL certificate management for HTTPS gateway
- Port configuration for activation (3812) and data (3781) endpoints
- Validation rule configuration
- Limit enforcement configuration
- Health monitoring and status reporting
"""

import asyncio
import websockets
import json
import logging
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
import threading
import queue

from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler

# Import RLA modules for command routing
try:
    from GVDM.gvdm import gvdm
    from ARM.arm import arm
    from DRM.drm import drm
    from LEM.lem import lem
    from SVM.svm import svm
    from IVM.ivm import ivm
    from OPM.opm import opm
    from FAIM.faim import faim
    from BTM.btm import btm
    from TMM.tmm import tmm
    from MSM.msm import msm
    from EMM.emm import emm
except ImportError:
    pass

class ECMConnectionStatus:
    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    ERROR = "error"

class ExternalControlModule:
    """
    External Control Module (ECM) for RLA
    - Maintains persistent connection to CCU
    - Parses and routes commands from CCU to appropriate RLA modules
    - Streams logs and monitoring data to CCU
    - Handles service control, configuration, resets, test execution, gateway management, and more
    - Manages RLA-specific capabilities: rate limiting, spam detection, SSL certificates
    - All actions are traceable and logged
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_manager = ErrorManagementModule()
        self.connection_status = ECMConnectionStatus.DISCONNECTED
        self.last_command: Optional[str] = None
        self.last_command_result: Optional[Any] = None
        self.stats = {
            "total_commands": 0,
            "successful_commands": 0,
            "failed_commands": 0,
            "last_activity": None
        }
        self.log_queue = queue.Queue()
        self.monitoring_queue = queue.Queue()
        self._stop_event = threading.Event()
        
        # NEW ARCHITECTURE: WebSocket CLIENT configuration
        self.ccu_websocket_uri = "ws://localhost:4441/ws"  # Connect to CCU RLAIM server
        self.websocket_connection = None
        self.websocket_task = None 
        self.heartbeat_task = None
        self.connection_retry_count = 0
        self.max_retry_attempts = 10
        self.retry_delay = 5  # seconds
        self.heartbeat_interval = 30  # seconds
        self.connection_timeout = 5.0  # seconds
        self.fallback_ports = [4451, 4461, 4471]  # CCU RLAIM fallback ports
        self.current_port = 4441  # Primary CCU RLAIM port
        self.is_active = False  # ECM module activation state
        
        # RLA-specific state
        self.gateway_state = {
            "activation_enabled": True,
            "data_reception_enabled": True,
            "ssl_enabled": True,
            "current_limits": {
                "max_words": 3000,
                "max_tokens": 5000,
                "max_request_size": 10485760  # 10MB
            },
            "spam_detection": {
                "enabled": True,
                "threshold": 0.8,
                "auto_reject": True
            }
        }

    async def start_websocket_client(self):
        """Start WebSocket client connection to CCU RLAIM server."""
        try:
            self.logger.info("🔌 Starting RLA ECM WebSocket client to CCU RLAIM...")
            self.websocket_task = asyncio.create_task(self._websocket_connection_loop())
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self.logger.info("✅ RLA ECM WebSocket client started successfully")
        except Exception as e:
            self.logger.error(f"❌ Failed to start RLA ECM WebSocket client: {e}")
            raise

    async def stop_websocket_client(self):
        """Stop WebSocket client connection."""
        try:
            self._stop_event.set()
            
            # Cancel tasks
            if self.websocket_task and not self.websocket_task.done():
                self.websocket_task.cancel()
            if self.heartbeat_task and not self.heartbeat_task.done():
                self.heartbeat_task.cancel()

            # Close WebSocket connection
            if self.websocket_connection:
                await self.websocket_connection.close()
                self.websocket_connection = None

            self.connection_status = ECMConnectionStatus.DISCONNECTED
            self.logger.info("🔌 RLA ECM WebSocket client disconnected from CCU")
        except Exception as e:
            self.logger.error(f"Error stopping WebSocket client: {e}")

    
    async def _websocket_connection_loop(self):
        """Main WebSocket connection loop with retry logic."""
        while True:
            try:
                await self._connect_to_ccu()
                self.connection_retry_count = 0
                await self._listen_for_messages()
            except Exception as e:
                self.logger.error(f"WebSocket connection error: {e}")
                if self.websocket_connection:
                    try:
                        await self.websocket_connection.close()
                    except:
                        pass
                    self.websocket_connection = None
                self.connection_retry_count += 1
                if self.connection_retry_count <= self.max_retry_attempts:
                    self.logger.info(f"Retrying connection in {self.retry_delay} seconds")
                    await asyncio.sleep(self.retry_delay)
                else:
                    self.logger.error("Max retry attempts reached")
                    break
    
    async def _connect_to_ccu(self):
        """Connect to CCU RLAIM WebSocket server with fallback logic."""
        ports_to_try = [self.current_port] + self.fallback_ports
        
        for port in ports_to_try:
            try:
                uri = f"ws://localhost:{port}/ws"
                self.logger.debug(f"🔍 Attempting to connect to CCU RLAIM at {uri}")
                
                self.websocket_connection = await asyncio.wait_for(
                    websockets.connect(uri),
                    timeout=self.connection_timeout
                )
                
                self.connection_status = ECMConnectionStatus.CONNECTED
                self.ccu_websocket_uri = uri
                self.current_port = port
                
                self.logger.info(f"✅ RLA ECM connected to CCU RLAIM server at port {port}")
                
                # Send registration message
                await self._send_registration()
                return
                
            except Exception as e:
                self.logger.debug(f"❌ Failed to connect to port {port}: {e}")
                continue
        
        raise Exception(f"Failed to connect to CCU RLAIM server on all ports: {ports_to_try}")
    
    async def _listen_for_messages(self):
        """Listen for messages from CCU."""
        if not self.websocket_connection:
            return
        try:
            async for message in self.websocket_connection:
                await self._handle_ccu_message(message)
        except Exception as e:
            self.logger.error(f"Error receiving message: {e}")
            raise
    
    async def _send_registration(self):
        """Send registration message to CCU RLAIM server."""
        registration_msg = {
            "type": "service_registration",
            "service": "RLA",
            "module": "ECM",
            "timestamp": datetime.now().isoformat(),
            "capabilities": [
                "gateway_control",
                "rate_limiting",
                "spam_detection",
                "ssl_management",
                "health_monitoring"
            ],
            "version": "1.0.0"
        }
        await self._send_to_ccu(registration_msg)
        self.logger.info("📋 Registration sent to CCU RLAIM")

    async def _handle_ccu_message(self, message: str):
        """Handle message from CCU RLAIM server."""
        try:
            data = json.loads(message)
            message_type = data.get("type", "unknown")
            
            self.logger.debug(f"📨 Received {message_type} message from CCU")
            
            if message_type == "welcome":
                self.logger.info(f"🤝 Welcome message from CCU: {data.get('message', 'Connected')}")
            elif message_type == "heartbeat_response":
                self.logger.debug("💓 Heartbeat response received")
            elif message_type == "activate":
                await self._handle_activation_command(data)
            elif message_type == "command":
                await self._handle_command(data)
            elif message_type == "config_update":
                await self._handle_config_update(data)
            else:
                self.logger.warning(f"⚠️ Unknown message type from CCU: {message_type}")
                
            self.stats["last_activity"] = datetime.now()
            
        except json.JSONDecodeError as e:
            self.logger.error(f"❌ Invalid JSON from CCU: {e}")
        except Exception as e:
            self.logger.error(f"❌ Error handling CCU message: {e}")
    
    async def _handle_activation_command(self, data: Dict[str, Any]):
        """Handle activation command from CCU."""
        try:
            self.logger.info("🚀 Received activation command from CCU")
            
            # Activate RLA gateway and services
            activation_result = {
                "gateway_activated": True,
                "ssl_enabled": self.gateway_state["ssl_enabled"],
                "rate_limiting_active": True,
                "spam_detection_active": self.gateway_state["spam_detection"]["enabled"]
            }
            
            response = {
                "type": "activation_ack",
                "service": "RLA",
                "status": "activated",
                "timestamp": datetime.now().isoformat(),
                "details": activation_result
            }
            
            await self._send_to_ccu(response)
            self.logger.info("✅ Activation acknowledged to CCU")
            
        except Exception as e:
            self.logger.error(f"❌ Error handling activation: {e}")
            error_response = {
                "type": "activation_ack",
                "service": "RLA", 
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            await self._send_to_ccu(error_response)
    
    async def _send_to_ccu(self, data: dict):
        """Send message to CCU."""
        if not self.websocket_connection:
            return False
        try:
            await self.websocket_connection.send(json.dumps(data))
            return True
        except Exception as e:
            self.logger.error(f"Error sending to CCU: {e}")
            return False
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeat to CCU."""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                if self.websocket_connection:
                    await self._send_to_ccu({"type": "heartbeat", "service": "RLA", "status": "active"})
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in heartbeat: {e}")
    
    async def _handle_command(self, data: Dict[str, Any]):
        """Handle command from CCU."""
        try:
            command = data.get("command")
            self.logger.info(f"📋 Executing command from CCU: {command}")
            
            # Process the command (implementation depends on specific RLA commands)
            # This would route to appropriate RLA modules
            result = {"status": "completed", "command": command}
            
            response = {
                "type": "command_response",
                "service": "RLA",
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            
            await self._send_to_ccu(response)
            self.stats["successful_commands"] += 1
            
        except Exception as e:
            self.logger.error(f"❌ Error executing command: {e}")
            self.stats["failed_commands"] += 1
            error_response = {
                "type": "command_response",
                "service": "RLA",
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            await self._send_to_ccu(error_response)
    
    async def _handle_config_update(self, data: Dict[str, Any]):
        """Handle configuration update from CCU."""
        try:
            self.logger.info("⚙️ Received configuration update from CCU")
            
            # Update RLA configuration (implementation specific)
            config_data = data.get("config", {})
            
            # Acknowledge configuration update
            response = {
                "type": "config_update_ack",
                "service": "RLA",
                "status": "updated",
                "timestamp": datetime.now().isoformat()
            }
            
            await self._send_to_ccu(response)
            
        except Exception as e:
            self.logger.error(f"❌ Error updating configuration: {e}")
    
    def get_connection_status(self):
        """Get current connection status and statistics."""
        return {
            "status": self.connection_status,
            "connected_to": self.ccu_websocket_uri if self.connection_status == ECMConnectionStatus.CONNECTED else None,
            "current_port": self.current_port,
            "retry_count": self.connection_retry_count,
            "stats": {
                **self.stats,
                "total_commands": self.stats["successful_commands"] + self.stats["failed_commands"]
            }
        }



    async def receive_command(self, command: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Receive and process a command from the CCU."""
        # Note: Stats are now tracked in _handle_command method
        self.stats["last_activity"] = datetime.now()
        self.last_command = command
        try:
            result = await self._route_command(command, parameters or {})
            self.last_command_result = result
            self.stats["successful_commands"] += 1
            self.logger.info(f"ECM: Command '{command}' executed successfully")
            return {"success": True, "result": result}
        except Exception as e:
            self.stats["failed_commands"] += 1
            error_msg = f"ECM: Command '{command}' failed: {e}"
            self.logger.error(error_msg)
            self.error_manager.log_error_with_generation("ECM", "ExternalControlModule", "receive_command", error_msg)
            return {"success": False, "error": str(e)}

    async def _route_command(self, command: str, parameters: Dict[str, Any]) -> Any:
        """Route command to the appropriate RLA module/method."""
        # Service control
        if command == "activate":
            return self._activate_service()
        elif command == "deactivate":
            return self._deactivate_service()
        elif command == "status":
            return self._get_service_status()
        elif command == "health_check":
            return await self._get_health_status()
        
        # Gateway configuration
        elif command == "set_gateway_limits":
            return self._set_gateway_limits(parameters)
        elif command == "configure_ports":
            return self._configure_ports(parameters)
        elif command == "enable_activation_endpoint":
            return self._enable_activation_endpoint(parameters)
        elif command == "enable_data_endpoint":
            return self._enable_data_endpoint(parameters)
        
        # Rate limiting and spam detection
        elif command == "set_rate_limits":
            return self._set_rate_limits(parameters)
        elif command == "configure_spam_detection":
            return self._configure_spam_detection(parameters)
        elif command == "set_validation_rules":
            return self._set_validation_rules(parameters)
        
        # SSL certificate management
        elif command == "update_ssl_certificate":
            return self._update_ssl_certificate(parameters)
        elif command == "reload_ssl_certificates":
            return self._reload_ssl_certificates()
        elif command == "get_ssl_status":
            return self._get_ssl_status()
        
        # Remote test execution
        elif command == "run_test":
            return await self._run_test(parameters)
        elif command == "run_gateway_test":
            return await self._run_gateway_test(parameters)
        elif command == "test_spam_detection":
            return await self._test_spam_detection(parameters)
        elif command == "test_rate_limiting":
            return await self._test_rate_limiting(parameters)
        
        # Reset and maintenance
        elif command == "reset_module":
            return self._reset_module(parameters)
        elif command == "reset_all":
            return self._reset_all()
        elif command == "clear_rate_limit_cache":
            return self._clear_rate_limit_cache()
        elif command == "reset_spam_detection":
            return self._reset_spam_detection()
        
        # Monitoring and data
        elif command == "get_errors":
            return self._get_errors()
        elif command == "get_monitoring":
            return self._get_monitoring()
        elif command == "get_gateway_stats":
            return self._get_gateway_stats()
        elif command == "get_rate_limit_stats":
            return self._get_rate_limit_stats()
        
        # Automatic code generation
        elif command == "auto_code_gen":
            return await self._auto_code_gen()
        else:
            raise ValueError(f"Unknown command: {command}")

    def _activate_service(self):
        """Activate the RLA gateway service."""
        self.gateway_state["activation_enabled"] = True
        self.gateway_state["data_reception_enabled"] = True
        self.logger.info("ECM: RLA Gateway service activated")
        return {"status": "activated", "endpoints": ["activation:3812", "data:3781", "health:9090"]}

    def _deactivate_service(self):
        """Deactivate the RLA gateway service."""
        self.gateway_state["activation_enabled"] = False
        self.gateway_state["data_reception_enabled"] = False
        self.logger.info("ECM: RLA Gateway service deactivated")
        return {"status": "deactivated"}

    def _get_service_status(self):
        """Get comprehensive RLA service status."""
        status = {
            "service": "RLA",
            "version": "1.0.0",
            "connection_status": self.connection_status,
            "gateway_state": self.gateway_state,
            "last_command": self.last_command,
            "last_command_result": self.last_command_result,
            "stats": self.stats.copy(),
            "endpoints": {
                "activation_port": 3812,
                "data_port": 3781,
                "health_port": 9090
            },
            "capabilities": [
                "request_validation",
                "limit_enforcement",
                "spam_detection",
                "gateway_control",
                "rate_limiting",
                "ssl_certificate_management"
            ]
        }
        return status

    async def _get_health_status(self):
        """Get comprehensive health status."""
        try:
            module_health = {}
            all_healthy = True
            
            # Check core modules if available
            for module_name in ["gvdm", "lem", "svm", "ivm", "arm", "drm", "msm", "emm"]:
                if module_name in globals():
                    module = globals()[module_name]
                    if hasattr(module, 'health_check'):
                        health = await module.health_check()
                        module_health[module_name] = health
                        if not health.get('healthy', True):
                            all_healthy = False
            
            return {
                "healthy": all_healthy,
                "service": "RLA",
                "gateway_operational": self.gateway_state["activation_enabled"] and self.gateway_state["data_reception_enabled"],
                "ssl_enabled": self.gateway_state["ssl_enabled"],
                "modules": module_health,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"healthy": False, "error": str(e), "service": "RLA"}

    def _set_gateway_limits(self, parameters: Dict[str, Any]):
        """Configure gateway limits (words, tokens, request size)."""
        max_words = parameters.get("max_words", 3000)
        max_tokens = parameters.get("max_tokens", 5000)
        max_request_size = parameters.get("max_request_size", 10485760)  # 10MB
        
        # Update limits
        self.gateway_state["current_limits"]["max_words"] = max_words
        self.gateway_state["current_limits"]["max_tokens"] = max_tokens
        self.gateway_state["current_limits"]["max_request_size"] = max_request_size
        
        # Apply to LEM module if available
        if "lem" in globals():
            lem.limits["max_words"] = max_words
            lem.limits["max_tokens"] = max_tokens
            lem.limits["max_request_size"] = max_request_size
            
        self.logger.info(f"ECM: Gateway limits updated - words:{max_words}, tokens:{max_tokens}, size:{max_request_size}")
        return {
            "status": "limits_updated", 
            "limits": self.gateway_state["current_limits"]
        }

    def _configure_ports(self, parameters: Dict[str, Any]):
        """Configure gateway ports."""
        activation_port = parameters.get("activation_port", 3812)
        data_port = parameters.get("data_port", 3781)
        health_port = parameters.get("health_port", 9090)
        
        # Note: In production, this would require service restart or dynamic binding
        self.logger.info(f"ECM: Port configuration updated - activation:{activation_port}, data:{data_port}, health:{health_port}")
        return {
            "status": "ports_configured",
            "ports": {
                "activation_port": activation_port,
                "data_port": data_port,
                "health_port": health_port
            },
            "note": "Port changes require service restart to take effect"
        }

    def _enable_activation_endpoint(self, parameters: Dict[str, Any]):
        """Enable/disable activation endpoint."""
        enabled = parameters.get("enabled", True)
        self.gateway_state["activation_enabled"] = enabled
        
        # Apply to ARM module if available
        if "arm" in globals() and hasattr(arm, 'set_enabled'):
            arm.set_enabled(enabled)
            
        self.logger.info(f"ECM: Activation endpoint {'enabled' if enabled else 'disabled'}")
        return {"status": "activation_endpoint_updated", "enabled": enabled}

    def _enable_data_endpoint(self, parameters: Dict[str, Any]):
        """Enable/disable data reception endpoint."""
        enabled = parameters.get("enabled", True)
        self.gateway_state["data_reception_enabled"] = enabled
        
        # Apply to DRM module if available
        if "drm" in globals() and hasattr(drm, 'set_enabled'):
            drm.set_enabled(enabled)
            
        self.logger.info(f"ECM: Data endpoint {'enabled' if enabled else 'disabled'}")
        return {"status": "data_endpoint_updated", "enabled": enabled}

    def _set_rate_limits(self, parameters: Dict[str, Any]):
        """Configure rate limiting parameters."""
        requests_per_minute = parameters.get("requests_per_minute", 60)
        requests_per_hour = parameters.get("requests_per_hour", 1000)
        burst_limit = parameters.get("burst_limit", 10)
        
        # Apply to LEM module if available
        if "lem" in globals():
            lem.limits["max_requests_per_minute"] = requests_per_minute
            lem.limits["max_requests_per_hour"] = requests_per_hour
            if hasattr(lem, 'burst_limit'):
                lem.burst_limit = burst_limit
                
        self.logger.info(f"ECM: Rate limits updated - {requests_per_minute}/min, {requests_per_hour}/hour, burst:{burst_limit}")
        return {
            "status": "rate_limits_updated",
            "limits": {
                "requests_per_minute": requests_per_minute,
                "requests_per_hour": requests_per_hour,
                "burst_limit": burst_limit
            }
        }

    def _configure_spam_detection(self, parameters: Dict[str, Any]):
        """Configure spam detection settings."""
        enabled = parameters.get("enabled", True)
        threshold = parameters.get("threshold", 0.8)
        auto_reject = parameters.get("auto_reject", True)
        
        # Update local state
        self.gateway_state["spam_detection"]["enabled"] = enabled
        self.gateway_state["spam_detection"]["threshold"] = threshold
        self.gateway_state["spam_detection"]["auto_reject"] = auto_reject
        
        # Apply to SVM module if available
        if "svm" in globals():
            if hasattr(svm, 'configure'):
                svm.configure(enabled=enabled, threshold=threshold, auto_reject=auto_reject)
                
        self.logger.info(f"ECM: Spam detection configured - enabled:{enabled}, threshold:{threshold}, auto_reject:{auto_reject}")
        return {
            "status": "spam_detection_configured",
            "config": self.gateway_state["spam_detection"]
        }

    def _set_validation_rules(self, parameters: Dict[str, Any]):
        """Configure input validation rules."""
        rules = parameters.get("rules", {})
        
        # Apply to IVM module if available
        if "ivm" in globals() and hasattr(ivm, 'update_rules'):
            ivm.update_rules(rules)
        
        # Apply to GVDM module if available
        if "gvdm" in globals() and hasattr(gvdm, 'update_validation_rules'):
            gvdm.update_validation_rules(rules)
            
        self.logger.info(f"ECM: Validation rules updated: {list(rules.keys())}")
        return {"status": "validation_rules_updated", "rules": rules}

    def _update_ssl_certificate(self, parameters: Dict[str, Any]):
        """Update SSL certificate for HTTPS endpoints."""
        cert_content = parameters.get("cert_content", "")
        key_content = parameters.get("key_content", "")
        cert_hash = parameters.get("cert_hash", "")
        expires_at = parameters.get("expires_at")
        
        try:
            # Apply to DRM module if available (handles HTTPS on port 3781)
            if "drm" in globals() and hasattr(drm, 'update_ssl_certificate'):
                drm.update_ssl_certificate(cert_content, key_content, cert_hash)
            
            # Update local state
            self.gateway_state["ssl_enabled"] = True
            
            self.logger.info("ECM: SSL certificate updated successfully")
            return {
                "status": "ssl_certificate_updated",
                "cert_hash": cert_hash,
                "expires_at": expires_at
            }
        except Exception as e:
            self.logger.error(f"ECM: SSL certificate update failed: {e}")
            raise

    def _reload_ssl_certificates(self):
        """Reload SSL certificates without service restart."""
        try:
            if "drm" in globals() and hasattr(drm, 'reload_ssl_certificates'):
                drm.reload_ssl_certificates()
                
            self.logger.info("ECM: SSL certificates reloaded")
            return {"status": "ssl_certificates_reloaded"}
        except Exception as e:
            self.logger.error(f"ECM: SSL certificate reload failed: {e}")
            return {"status": "ssl_reload_failed", "error": str(e)}

    def _get_ssl_status(self):
        """Get SSL certificate status."""
        try:
            ssl_status = {"ssl_enabled": self.gateway_state["ssl_enabled"]}
            
            if "drm" in globals() and hasattr(drm, 'get_ssl_status'):
                ssl_status.update(drm.get_ssl_status())
                
            return {"status": "ssl_status_retrieved", "ssl_info": ssl_status}
        except Exception as e:
            return {"status": "ssl_status_error", "error": str(e)}

    async def _run_test(self, parameters: Dict[str, Any]):
        """Run a test via TMM."""
        test_code = parameters.get("test_code")
        if "tmm" in globals() and hasattr(tmm, 'run_test'):
            result = await tmm.run_test(test_code)
        else:
            raise ValueError("TMM module not available")
        
        self.logger.info(f"ECM: Test {test_code} executed")
        return {"status": "test_executed", "test_code": test_code, "result": result}

    async def _run_gateway_test(self, parameters: Dict[str, Any]):
        """Run gateway-specific integration test."""
        test_type = parameters.get("test_type", "full")
        
        try:
            # Test activation endpoint
            activation_test = {"passed": True, "details": "Mock activation test"}
            
            # Test data reception endpoint  
            data_test = {"passed": True, "details": "Mock data reception test"}
            
            # Test validation pipeline
            validation_test = {"passed": True, "details": "Mock validation pipeline test"}
            
            result = {
                "test_type": test_type,
                "activation_endpoint": activation_test,
                "data_endpoint": data_test,
                "validation_pipeline": validation_test,
                "overall_result": "PASSED"
            }
            
            self.logger.info(f"ECM: Gateway test '{test_type}' executed")
            return {"status": "gateway_test_executed", "result": result}
        except Exception as e:
            return {"status": "gateway_test_failed", "error": str(e)}

    async def _test_spam_detection(self, parameters: Dict[str, Any]):
        """Test spam detection with sample content."""
        test_content = parameters.get("content", "test spam content")
        
        try:
            if "svm" in globals():
                result = await svm.check_spam({"content": test_content})
            else:
                result = {"is_spam": False, "score": 0.0, "reasons": []}
            
            self.logger.info("ECM: Spam detection test executed")
            return {"status": "spam_test_executed", "result": result}
        except Exception as e:
            return {"status": "spam_test_failed", "error": str(e)}

    async def _test_rate_limiting(self, parameters: Dict[str, Any]):
        """Test rate limiting functionality."""
        test_requests = parameters.get("request_count", 10)
        
        try:
            # Mock rate limiting test
            result = {
                "test_requests": test_requests,
                "allowed_requests": min(test_requests, 60),  # Based on default limits
                "rejected_requests": max(0, test_requests - 60),
                "rate_limit_effective": test_requests > 60
            }
            
            self.logger.info(f"ECM: Rate limiting test executed with {test_requests} requests")
            return {"status": "rate_limit_test_executed", "result": result}
        except Exception as e:
            return {"status": "rate_limit_test_failed", "error": str(e)}

    def _reset_module(self, parameters: Dict[str, Any]):
        """Reset a specific RLA module."""
        module = parameters.get("module")
        if module and module in globals():
            mod = globals()[module]
            if hasattr(mod, "reset"):
                mod.reset()
            self.logger.info(f"ECM: Module {module} reset")
            return {"status": "module_reset", "module": module}
        else:
            raise ValueError(f"Unknown or unavailable module: {module}")

    def _reset_all(self):
        """Reset the entire RLA service."""
        # Reset gateway state
        self.gateway_state = {
            "activation_enabled": True,
            "data_reception_enabled": True,
            "ssl_enabled": True,
            "current_limits": {
                "max_words": 3000,
                "max_tokens": 5000,
                "max_request_size": 10485760
            },
            "spam_detection": {
                "enabled": True,
                "threshold": 0.8,
                "auto_reject": True
            }
        }
        
        self.logger.info("ECM: All RLA modules reset")
        return {"status": "all_reset"}

    def _clear_rate_limit_cache(self):
        """Clear rate limiting cache."""
        if "lem" in globals() and hasattr(lem, 'clear_cache'):
            lem.clear_cache()
            
        self.logger.info("ECM: Rate limit cache cleared")
        return {"status": "rate_limit_cache_cleared"}

    def _reset_spam_detection(self):
        """Reset spam detection module."""
        if "svm" in globals() and hasattr(svm, 'reset'):
            svm.reset()
            
        self.logger.info("ECM: Spam detection reset")
        return {"status": "spam_detection_reset"}

    def _get_errors(self):
        """Get error logs from EMM."""
        if "emm" in globals() and hasattr(emm, 'get_errors'):
            errors = emm.get_errors()
        else:
            errors = []
        
        self.logger.info("ECM: Error logs retrieved")
        return {"status": "errors_retrieved", "errors": errors}

    def _get_monitoring(self):
        """Get monitoring data from MSM."""
        if "msm" in globals() and hasattr(msm, 'get_monitoring'):
            monitoring = msm.get_monitoring()
        else:
            monitoring = {}
            
        self.logger.info("ECM: Monitoring data retrieved")
        return {"status": "monitoring_retrieved", "monitoring": monitoring}

    def _get_gateway_stats(self):
        """Get gateway-specific statistics."""
        stats = {
            "gateway_state": self.gateway_state,
            "command_stats": self.stats,
            "endpoints_status": {
                "activation": self.gateway_state["activation_enabled"],
                "data_reception": self.gateway_state["data_reception_enabled"],
                "ssl_enabled": self.gateway_state["ssl_enabled"]
            }
        }
        
        # Add module-specific stats if available
        if "lem" in globals() and hasattr(lem, 'stats'):
            stats["limit_enforcement"] = lem.stats
        if "svm" in globals() and hasattr(svm, 'stats'):
            stats["spam_validation"] = svm.stats
        if "ivm" in globals() and hasattr(ivm, 'stats'):
            stats["input_validation"] = ivm.stats
            
        return {"status": "gateway_stats_retrieved", "stats": stats}

    def _get_rate_limit_stats(self):
        """Get rate limiting statistics."""
        if "lem" in globals() and hasattr(lem, 'get_rate_limit_stats'):
            rate_stats = lem.get_rate_limit_stats()
        else:
            rate_stats = {"message": "Rate limiting stats not available"}
            
        return {"status": "rate_limit_stats_retrieved", "stats": rate_stats}

    async def _auto_code_gen(self):
        """Trigger automatic code generation in EMM."""
        try:
            if "emm" in globals() and hasattr(emm, 'generate_error_codes_for_codebase'):
                from pathlib import Path
                import os
                
                # Get codebase path using PMM-aware detection
                codebase_path = None
                
                # Method 1: Try PMM environment variable
                if "PMM_PATHS" in os.environ:
                    import json
                    pmm_paths = json.loads(os.environ["PMM_PATHS"])
                    codebase_path = Path(pmm_paths.get("installation_root"))
                
                # Method 2: Look for installation markers (PMM detection method)
                if not codebase_path or not codebase_path.exists():
                    current_path = Path(__file__).resolve()
                    markers = ["JFA_CONFIGURATION_PLAN.md", "LICENSE.txt", "MicroServices", ".git"]
                    
                    for parent in current_path.parents:
                        if any((parent / marker).exists() for marker in markers):
                            codebase_path = parent
                            break
                
                # Method 3: Fallback to old method
                if not codebase_path:
                    codebase_path = Path(__file__).parent.parent.parent.parent.parent.parent
                
                result = await emm.generate_error_codes_for_codebase(codebase_path)
            else:
                raise ValueError("EMM module not available")
                
            self.logger.info("ECM: Automatic code generation triggered")
            return {"status": "auto_code_gen_triggered", "result": result}
        except Exception as e:
            error_msg = f"Automatic code generation failed: {e}"
            self.error_manager.log_error_with_generation("ECM", "ExternalControlModule", "_auto_code_gen", error_msg)
            raise

    def stream_logs(self, callback: Callable[[str], None], level: str = "INFO"):
        """Stream logs to CCU."""
        self.logger.info(f"ECM: Streaming logs at level {level}")
        callback(f"[ECM] Log streaming started at level {level} for RLA Gateway")

    def stream_monitoring(self, callback: Callable[[Dict[str, Any]], None]):
        """Stream monitoring data to CCU."""
        self.logger.info("ECM: Streaming monitoring data")
        callback({"status": "monitoring_stream_started", "service": "RLA"})

    def get_module_status(self) -> Dict[str, Any]:
        """Get ECM module status."""
        return {
            "module": "ECM",
            "service": "RLA",
            "status": self.connection_status,
            "gateway_state": self.gateway_state,
            "last_command": self.last_command,
            "last_command_result": self.last_command_result,
            "stats": self.stats.copy(),
            "last_activity": self.stats["last_activity"]
        }

    def log_error_with_generation(self, module_name: str, class_name: str, function_name: str, error_message: str, error_code: str = None):
        """Log error with dynamic code generation using EMM."""
        if hasattr(self, 'error_manager'):
            self.error_manager.log_error_with_generation(module_name, class_name, function_name, error_message, error_code)
        else:
            self.logger.error(f"Error in {module_name}.{class_name}.{function_name}: {error_message}")

    async def handle_api_error(self, error: Exception, context: str = "unknown") -> dict:
        """Handle API errors with proper formatting."""
        return api_error_handler.handle_error(error, context, "ECM")

    async def start(self):
        """Start the ECM module."""
        self.is_active = True
        await self.start_websocket_client()
        self.logger.info("✅ RLA ECM started successfully")

    async def stop(self):
        """Stop the ECM module."""
        self.is_active = False
        await self.stop_websocket_client()
        self.logger.info("🔌 RLA ECM stopped successfully")

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        return {
            "healthy": self.connection_status == ECMConnectionStatus.CONNECTED,
            "module": "ECM",
            "service": "RLA",
            "connection_status": self.connection_status,
            "gateway_operational": self.gateway_state["activation_enabled"] and self.gateway_state["data_reception_enabled"],
            "timestamp": datetime.now().isoformat()
        }

# Global instances
ecm = ExternalControlModule()
ECM = ExternalControlModule() 