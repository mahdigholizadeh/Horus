"""
External Control Module (ECM)

Primary interface between the RCM microservice and the Central Control Unit (CCU).
Handles service control, monitoring/log streaming, configuration, remote test execution, resets, database access, system message injection, model switching, error reporting, and monitoring data streaming.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
import threading
import queue
import websockets
import json
from config import CCU_WS_URI, CCU_SERVICE_ID, CCU_HEARTBEAT_INTERVAL

from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler

# Import other modules for command routing
try:
    from IFCM.ifcm import ifcm
    from MSM.msm import msm
    from EMM.emm import emm
    from DCMM.dcmm import dcmm  # Ensure dcmm is imported and available
    globals()['dcmm'] = dcmm  # Explicitly assign to globals
    from TMM.tmm import tmm
    from BAAIM.baaim import baaim
    from AAAIM.aaaim import aaaim
    from SAAIM.saaim import saaim
    from RLM.rlm import rlm
    from SMSM.smsm import smsm
    from SMCM.smcm import smcm
except ImportError:
    pass

class ECMConnectionStatus:
    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    ERROR = "error"

class ExternalControlModule:
    """
    External Control Module (ECM)
    - Maintains persistent connection to CCU (mocked for now)
    - Parses and routes commands from CCU to appropriate modules
    - Streams logs and monitoring data to CCU
    - Handles service control, configuration, resets, test execution, database access, and more
    - All actions are traceable and logged
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # NEW ARCHITECTURE: WebSocket CLIENT configuration
        self.ccu_websocket_uri = "ws://localhost:4443/ws"
        self.websocket_connection = None
        self.websocket_task = None 
        self.heartbeat_task = None
        self.connection_retry_count = 0
        self.max_retry_attempts = 10
        self.retry_delay = 5  # seconds
        self.heartbeat_interval = 30  # seconds
        self.connection_timeout = 5.0  # seconds
        self.fallback_ports = [4453, 4463, 4473]  # CCU RCMIM fallback ports
        self.current_port = 4443  # Primary CCU RCMIM port
        self.is_active = False  # ECM module activation state
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
        
        # RCM-specific state
        self.rcm_state = {
            "processing_enabled": True,
            "database_connected": True,
            "api_endpoints_active": True,
            "workflow_processing": True,
            "current_settings": {
                "max_concurrent_requests": 100,
                "timeout_seconds": 300,
                "retry_attempts": 3,
                "batch_size": 50
            }
        }
        
        # Connection will be started via start() method

    async def start_websocket_client(self):
        """Start WebSocket client connection to CCU RCMIM server."""
        try:
            self.logger.info("🔌 Starting RCM ECM WebSocket client to CCU RCMIM...")
            self.websocket_task = asyncio.create_task(self._websocket_connection_loop())
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self.logger.info("✅ RCM ECM WebSocket client started successfully")
        except Exception as e:
            self.logger.error(f"❌ Failed to start RCM ECM WebSocket client: {e}")
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
            self.logger.info("🔌 RCM ECM WebSocket client disconnected from CCU")
        except Exception as e:
            self.logger.error(f"Error stopping WebSocket client: {e}")

    async def _websocket_connection_loop(self):
        """Main WebSocket connection loop with retry logic."""
        while not self._stop_event.is_set():
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
        """Connect to CCU RCMIM WebSocket server with fallback logic."""
        ports_to_try = [self.current_port] + self.fallback_ports
        
        for port in ports_to_try:
            try:
                uri = f"ws://localhost:{port}/ws"
                self.logger.debug(f"🔍 Attempting to connect to CCU RCMIM at {uri}")
                
                self.websocket_connection = await asyncio.wait_for(
                    websockets.connect(uri),
                    timeout=self.connection_timeout
                )
                
                self.connection_status = ECMConnectionStatus.CONNECTED
                self.ccu_websocket_uri = uri
                self.current_port = port
                
                self.logger.info(f"✅ RCM ECM connected to CCU RCMIM server at port {port}")
                
                # Send registration message
                await self._send_registration()
                return
                
            except Exception as e:
                self.logger.debug(f"❌ Failed to connect to port {port}: {e}")
                continue
        
        raise Exception(f"Failed to connect to CCU RCMIM server on all ports: {ports_to_try}")

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
        """Send registration message to CCU RCMIM server."""
        registration_msg = {
            "type": "service_registration",
            "service": "RCM",
            "module": "ECM",
            "timestamp": datetime.now().isoformat(),
            "capabilities": [
                "request_processing",
                "api_communication",
                "workflow_management",
                "database_operations",
                "rate_limiting"
            ],
            "version": "1.0.0"
        }
        await self._send_to_ccu(registration_msg)
        self.logger.info("📋 Registration sent to CCU RCMIM")

    async def _handle_ccu_message(self, message: str):
        """Handle message from CCU RCMIM server."""
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
            
            # Activate RCM processing services
            activation_result = {
                "processing_activated": True,
                "database_connected": self.rcm_state["database_connected"],
                "api_endpoints_active": self.rcm_state["api_endpoints_active"],
                "workflow_processing_ready": True
            }
            
            response = {
                "type": "activation_ack",
                "service": "RCM",
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
                "service": "RCM", 
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            await self._send_to_ccu(error_response)

    async def _handle_command(self, data: Dict[str, Any]):
        """Handle command from CCU."""
        try:
            command = data.get("command")
            self.logger.info(f"📋 Executing command from CCU: {command}")
            
            # Process the command (implementation depends on specific RCM commands)
            # This would route to appropriate RCM modules
            result = {"status": "completed", "command": command}
            
            response = {
                "type": "command_response",
                "service": "RCM",
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
                "service": "RCM",
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            await self._send_to_ccu(error_response)

    async def _handle_config_update(self, data: Dict[str, Any]):
        """Handle configuration update from CCU."""
        try:
            self.logger.info("⚙️ Received configuration update from CCU")
            
            # Update RCM configuration (implementation specific)
            config_data = data.get("config", {})
            
            # Acknowledge configuration update
            response = {
                "type": "config_update_ack",
                "service": "RCM",
                "status": "updated",
                "timestamp": datetime.now().isoformat()
            }
            
            await self._send_to_ccu(response)
            
        except Exception as e:
            self.logger.error(f"❌ Error updating configuration: {e}")

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
        while not self._stop_event.is_set():
            try:
                await asyncio.sleep(self.heartbeat_interval)
                if self.websocket_connection:
                    heartbeat_msg = {
                        "type": "heartbeat", 
                        "service": "RCM", 
                        "status": "active",
                        "timestamp": datetime.now().isoformat(),
                        "processing_stats": {
                            "requests_processing": self.rcm_state["processing_enabled"],
                            "database_connected": self.rcm_state["database_connected"]
                        }
                    }
                    await self._send_to_ccu(heartbeat_msg)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in heartbeat: {e}")

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

    # Old WebSocket code removed - using new implementation above



    async def send_output_request_to_ccu(self, request_id: str, payload: dict, priority: str = "C", timeout_seconds: int = 300, source_module: str = "JFAIM"):
        """Send an output request to CCU for handoff (JFAIM/OCMIM)."""
        msg = {
            "type": "output_request",
            "request_id": request_id,
            "priority": priority,
            "data": payload,
            "timeout_seconds": timeout_seconds,
            "timestamp": datetime.now().isoformat(),
            "source_module": source_module
        }
        await self._send_to_ccu(msg)
        self.logger.info(f"ECM: Sent output_request to CCU (source_module={source_module}, request_id={request_id})")

    async def receive_command(self, command: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Receive and process a command from the CCU."""
        self.stats["total_commands"] += 1
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
        """Route command to the appropriate module/method."""
        # Service control
        if command == "activate":
            return self._activate_service()
        elif command == "deactivate":
            return self._deactivate_service()
        elif command == "status":
            return self._get_service_status()
        # Configuration
        elif command == "set_api_key":
            return self._set_api_key(parameters)
        elif command == "set_rate_limit":
            return self._set_rate_limit(parameters)
        elif command == "set_port":
            return self._set_port(parameters)
        # Remote test execution
        elif command == "run_test":
            return self._run_test(parameters)
        # Reset
        elif command == "reset_module":
            return self._reset_module(parameters)
        elif command == "reset_all":
            return self._reset_all()
        # Database access
        elif command == "db_query":
            return self._db_query(parameters)
        # System message injection
        elif command == "inject_system_message":
            return self._inject_system_message(parameters)
        # Model switching
        elif command == "switch_model":
            return self._switch_model(parameters)
        # Error reporting
        elif command == "get_errors":
            return self._get_errors()
        # Monitoring data
        elif command == "get_monitoring":
            return self._get_monitoring()
        # Automatic code generation
        elif command == "auto_code_gen":
            return await self._auto_code_gen()
        else:
            raise ValueError(f"Unknown command: {command}")

    def _activate_service(self):
        # Activate the RCM service (mocked)
        self.logger.info("ECM: Service activated")
        return {"status": "activated"}

    def _deactivate_service(self):
        # Deactivate the RCM service (mocked)
        self.logger.info("ECM: Service deactivated")
        return {"status": "deactivated"}

    def _get_service_status(self):
        # Get overall service status (mocked)
        status = {
            "connection_status": self.connection_status,
            "last_command": self.last_command,
            "last_command_result": self.last_command_result,
            "stats": self.stats.copy()
        }
        return status

    def _set_api_key(self, parameters: Dict[str, Any]):
        # Set API key for BAAIM, AAAIM, or SAAIM
        module = parameters.get("module", "BAAIM")
        api_key = parameters.get("api_key")
        if module == "BAAIM" and "baaim" in globals():
            baaim.set_api_key(api_key)
        elif module == "AAAIM" and "aaaim" in globals():
            aaaim.set_api_key(api_key)
        elif module == "SAAIM" and "saaim" in globals():
            saaim.set_api_key(api_key)
        else:
            raise ValueError(f"Unknown or unavailable module for API key: {module}")
        self.logger.info(f"ECM: API key set for {module}")
        return {"status": "api_key_set", "module": module}

    def _set_rate_limit(self, parameters: Dict[str, Any]):
        # Set rate limit in RLM
        rate = parameters.get("rate")
        if "rlm" in globals():
            rlm.set_rate_limit(rate)
        else:
            raise ValueError("RLM module not available")
        self.logger.info(f"ECM: Rate limit set to {rate}")
        return {"status": "rate_limit_set", "rate": rate}

    def _set_port(self, parameters: Dict[str, Any]):
        # Set port for API modules
        module = parameters.get("module", "BAAIM")
        port = parameters.get("port")
        if module == "BAAIM" and "baaim" in globals():
            baaim.set_port(port)
        elif module == "AAAIM" and "aaaim" in globals():
            aaaim.set_port(port)
        elif module == "SAAIM" and "saaim" in globals():
            saaim.set_port(port)
        else:
            raise ValueError(f"Unknown or unavailable module for port: {module}")
        self.logger.info(f"ECM: Port set for {module} to {port}")
        return {"status": "port_set", "module": module, "port": port}

    def _run_test(self, parameters: Dict[str, Any]):
        # Trigger a test in TMM
        test_code = parameters.get("test_code")
        if "tmm" in globals():
            result = tmm.run_test(test_code)
        else:
            raise ValueError("TMM module not available")
        self.logger.info(f"ECM: Test {test_code} executed")
        return {"status": "test_executed", "test_code": test_code, "result": result}

    def _reset_module(self, parameters: Dict[str, Any]):
        # Reset a specific module (mocked)
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
        # Reset the entire RCM service (mocked)
        self.logger.info("ECM: All modules reset")
        return {"status": "all_reset"}

    def _db_query(self, parameters: Dict[str, Any]):
        # Query the database via DCMM
        query = parameters.get("query")
        db_name = parameters.get("db_name", "conversations")  # Default to conversations database
        
        # Debug: Check what's in globals
        self.logger.info(f"ECM: Checking globals for dcmm, available keys: {list(globals().keys())}")
        self.logger.info(f"ECM: 'dcmm' in globals: {'dcmm' in globals()}")
        print(f"ECM DEBUG: globals keys: {list(globals().keys())}")
        print(f"ECM DEBUG: 'dcmm' in globals: {'dcmm' in globals()}")
        
        if "dcmm" in globals():
            result = dcmm.query(db_name, query)
        else:
            raise ValueError("DCMM module not available")
        self.logger.info(f"ECM: DB query executed: {query}")
        return {"status": "db_query_executed", "query": query, "result": result}

    def _inject_system_message(self, parameters: Dict[str, Any]):
        # Inject a system message via SMSM
        request_id = parameters.get("request_id")
        message = parameters.get("message")
        if "smsm" in globals():
            smsm.inject_message(request_id, message)
        else:
            raise ValueError("SMSM module not available")
        self.logger.info(f"ECM: System message injected for request {request_id}")
        return {"status": "system_message_injected", "request_id": request_id}

    def _switch_model(self, parameters: Dict[str, Any]):
        # Switch model via SMCM
        request_id = parameters.get("request_id")
        model_name = parameters.get("model_name")
        if "smcm" in globals():
            smcm.switch_model(request_id, model_name)
        else:
            raise ValueError("SMCM module not available")
        self.logger.info(f"ECM: Model switched for request {request_id} to {model_name}")
        return {"status": "model_switched", "request_id": request_id, "model_name": model_name}

    def _get_errors(self):
        # Get error logs from EMM
        if "emm" in globals():
            errors = emm.get_errors()
        else:
            errors = []
        self.logger.info("ECM: Error logs retrieved")
        return {"status": "errors_retrieved", "errors": errors}

    def _get_monitoring(self):
        # Get monitoring data from MSM
        if "msm" in globals():
            monitoring = msm.get_monitoring()
        else:
            monitoring = {}
        self.logger.info("ECM: Monitoring data retrieved")
        return {"status": "monitoring_retrieved", "monitoring": monitoring}

    async def _auto_code_gen(self):
        # Trigger automatic code generation in EMM
        try:
            if "emm" in globals():
                # Get the installation root using PMM-aware detection
                from pathlib import Path
                import os
                import json
                
                # Method 1: Try PMM environment variable
                codebase_path = None
                if "PMM_PATHS" in os.environ:
                    try:
                        pmm_paths = json.loads(os.environ["PMM_PATHS"])
                        codebase_path = Path(pmm_paths.get("installation_root", Path.cwd()))
                    except (json.JSONDecodeError, KeyError):
                        pass
                
                # Method 2: Look for installation markers if PMM env not available
                if not codebase_path:
                    current_path = Path(__file__).resolve()
                    markers = ["JFA_CONFIGURATION_PLAN.md", "LICENSE.txt", "MicroServices", ".git"]
                    
                    for parent in current_path.parents:
                        if any((parent / marker).exists() for marker in markers):
                            codebase_path = parent
                            break
                    else:
                        # Fallback to original complex path navigation
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
        """Stream logs to CCU (stub)."""
        # In real implementation, this would stream logs in real time
        self.logger.info(f"ECM: Streaming logs at level {level}")
        callback(f"[ECM] Log streaming started at level {level}")

    def stream_monitoring(self, callback: Callable[[Dict[str, Any]], None]):
        """Stream monitoring data to CCU (stub)."""
        self.logger.info("ECM: Streaming monitoring data")
        callback({"status": "monitoring_stream_started"})

    def get_module_status(self) -> Dict[str, Any]:
        """Get ECM module status."""
        return {
            "module": "ECM",
            "status": self.connection_status,
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
        return api_error_handler.handle_error(error, context, "ECM")

    async def insufficient_data_message_get(self) -> Dict[str, Any]:
        """
        Get insufficient data message from CCU.
        
        Returns:
            Insufficient data message from CCU
        """
        try:
            # This would typically receive data from CCU via WebSocket
            # For now, return a placeholder structure
            message_data = {
                "type": "insufficient_data_message",
                "timestamp": datetime.now().isoformat(),
                "source": "CCU"
            }
            
            self.logger.info("ECM: Received insufficient data message from CCU")
            return {"success": True, "message_data": message_data}
            
        except Exception as e:
            error_msg = f"Error getting insufficient data message: {e}"
            self.logger.error(error_msg)
            self.error_manager.log_error_with_generation("ECM", "ExternalControlModule", "insufficient_data_message_get", error_msg)
            return {"success": False, "error": error_msg}

    async def invalid_data_message_get(self) -> Dict[str, Any]:
        """
        Get invalid data message from CCU.
        
        Returns:
            Invalid data message from CCU
        """
        try:
            # This would typically receive data from CCU via WebSocket
            # For now, return a placeholder structure
            message_data = {
                "type": "invalid_data_message",
                "timestamp": datetime.now().isoformat(),
                "source": "CCU"
            }
            
            self.logger.info("ECM: Received invalid data message from CCU")
            return {"success": True, "message_data": message_data}
            
        except Exception as e:
            error_msg = f"Error getting invalid data message: {e}"
            self.logger.error(error_msg)
            self.error_manager.log_error_with_generation("ECM", "ExternalControlModule", "invalid_data_message_get", error_msg)
            return {"success": False, "error": error_msg}

    async def insufficient_data_message_smsm_pass(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pass insufficient data message to SMSM module for injection.
        
        Args:
            message_data: Message data from CCU
            
        Returns:
            Result of SMSM injection
        """
        try:
            request_id = message_data.get("request_id", "unknown")
            message_content = message_data.get("message", "Insufficient data detected")
            
            # Import SMSM module
            from SMSM.smsm import SystemMessageSubjoinModule
            smsm = SystemMessageSubjoinModule()
            
            # Inject the system message
            result = await smsm.inject_system_message(
                request_id=request_id,
                message=message_content,
                message_type="intervention",
                position="end"
            )
            
            self.logger.info(f"ECM: Passed insufficient data message to SMSM for request {request_id}")
            return {
                "success": result.get("success", False),
                "smsm_result": result,
                "request_id": request_id,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            error_msg = f"Error passing insufficient data message to SMSM: {e}"
            self.logger.error(error_msg)
            self.error_manager.log_error_with_generation("ECM", "ExternalControlModule", "insufficient_data_message_smsm_pass", error_msg)
            return {"success": False, "error": error_msg}

    async def invalid_data_smsm_pass(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pass invalid data message to SMSM module for injection.
        
        Args:
            message_data: Message data from CCU
            
        Returns:
            Result of SMSM injection
        """
        try:
            request_id = message_data.get("request_id", "unknown")
            message_content = message_data.get("message", "Invalid data detected")
            
            # Import SMSM module
            from SMSM.smsm import SystemMessageSubjoinModule
            smsm = SystemMessageSubjoinModule()
            
            # Inject the system message
            result = await smsm.inject_system_message(
                request_id=request_id,
                message=message_content,
                message_type="intervention",
                position="end"
            )
            
            self.logger.info(f"ECM: Passed invalid data message to SMSM for request {request_id}")
            return {
                "success": result.get("success", False),
                "smsm_result": result,
                "request_id": request_id,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            error_msg = f"Error passing invalid data message to SMSM: {e}"
            self.logger.error(error_msg)
            self.error_manager.log_error_with_generation("ECM", "ExternalControlModule", "invalid_data_smsm_pass", error_msg)
            return {"success": False, "error": error_msg}

    async def start(self):
        """Start the ECM module."""
        self.is_active = True
        await self.start_websocket_client()
        self.logger.info("✅ RCM ECM started successfully")

    async def stop(self):
        """Stop the ECM module."""
        self.is_active = False
        await self.stop_websocket_client()
        self.logger.info("🔌 RCM ECM stopped successfully")

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        return {
            "healthy": self.connection_status == ECMConnectionStatus.CONNECTED,
            "module": "ECM", 
            "service": "RCM",
            "connection_status": self.connection_status,
            "processing_operational": self.rcm_state["processing_enabled"],
            "database_connected": self.rcm_state["database_connected"],
            "timestamp": datetime.now().isoformat()
        }

# Global instances
ecm = ExternalControlModule()
ECM = ExternalControlModule() 