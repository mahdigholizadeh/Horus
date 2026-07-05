"""
External Control Module (ECM) for TD Microservice

Primary interface between the TD microservice and the Central Control Unit (CCU).
Handles service control, monitoring/log streaming, configuration, remote test execution, 
resets, orchestration configuration, calculation block management, and binary file processing.

TD-Specific Capabilities:
- Binary file processing coordination
- Multi-calculation orchestration management
- Calculation block configuration
- Result aggregation settings
- OCM interface configuration
- Priority-based processing control
- Concurrent calculation management
- Performance optimization settings
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

# Import TD modules for command routing
try:
    from BFPM.bfpm import bfpm
    from AFM.afm import afm
    from ROM.rom import rom
    from CAM.cam import cam
    from CIM.cim import cim
    from RMM.rmm import rmm
    from FIM.fim import fim
    from ARM.arm import arm
    from OCMIM.ocmim import ocmim
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
    External Control Module (ECM) for TD
    - Maintains persistent connection to CCU
    - Parses and routes commands from CCU to appropriate TD modules
    - Streams logs and monitoring data to CCU
    - Handles service control, configuration, resets, test execution, orchestration management, and more
    - Manages TD-specific capabilities: binary processing, calculation coordination, orchestration
    - All actions are traceable and logged
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # NEW ARCHITECTURE: WebSocket CLIENT configuration
        self.ccu_websocket_uri = "ws://localhost:4445/ws"  # Connect to CCU TDIM server
        self.websocket_connection = None
        self.websocket_task = None 
        self.heartbeat_task = None
        self.connection_retry_count = 0
        self.max_retry_attempts = 10
        self.retry_delay = 5  # seconds
        self.heartbeat_interval = 30  # seconds
        self.connection_timeout = 5.0  # seconds
        self.fallback_ports = [4455, 4465, 4475]  # CCU TDIM fallback ports
        self.current_port = 4445  # Primary CCU TDIM port
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
        self._connection_thread = None
        
        # TD-specific state
        self.td_state = {
            "orchestration_enabled": True,
            "binary_processing_enabled": True,
            "calculation_coordination_enabled": True,
            "processing_modes": {
                "single_calculation": True,
                "multi_calculation": True,
                "orchestrated": True
            },
            "current_settings": {
                "default_mode": "orchestrated",
                "max_concurrent_calculations": 12,
                "max_concurrent_orchestrations": 5,
                "binary_file_formats": ["jfa_v1", "jfa_v2", "legacy"]
            },
            "route_handlers": {
                "forward": {"available": True, "active": 0, "total_processed": 0},
                "parallel": {"available": True, "active": 0, "total_processed": 0},
                "sequential": {"available": True, "active": 0, "total_processed": 0}
            },
            "orchestration_stats": {
                "total_orchestrations": 0,
                "successful_orchestrations": 0,
                "failed_orchestrations": 0,
                "average_orchestration_time": 0.0
            }
        }
        
        self._start_connection()

    def _start_connection(self):
        """Start (mock) persistent connection to CCU."""
        def connection_loop():
            self.connection_status = ECMConnectionStatus.CONNECTED
            self.logger.info("ECM: Connected to CCU (mock)")
            while not self._stop_event.is_set():
                # Simulate receiving commands from CCU
                # In real implementation, this would be WebSocket or message bus
                try:
                    # Poll for new commands (mocked)
                    import time
                    time.sleep(0.1)
                except Exception as e:
                    self.connection_status = ECMConnectionStatus.ERROR
                    self.logger.error(f"ECM connection error: {e}")
                    self.error_manager.log_error_with_generation("ECM", "ExternalControlModule", "_start_connection", f"Connection error: {e}")
                    break
        self._connection_thread = threading.Thread(target=connection_loop, daemon=True)
        self._connection_thread.start()

    def stop_connection(self):
        """Stop the persistent connection."""
        self._stop_event.set()
        if self._connection_thread:
            self._connection_thread.join()
        self.connection_status = ECMConnectionStatus.DISCONNECTED
        self.logger.info("ECM: Disconnected from CCU")
    async def start_websocket_client(self):
        """Start WebSocket client connection to CCU."""
        try:
            self.logger.info("Starting WebSocket client connection to CCU...")
            self.websocket_task = asyncio.create_task(self._websocket_connection_loop())
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self.logger.info("✅ WebSocket client started successfully")
        except Exception as e:
            self.logger.error(f"❌ Failed to start WebSocket client: {e}")
            raise
    
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
        """Connect to CCU WebSocket server."""
        try:
            self.websocket_connection = await asyncio.wait_for(
                websockets.connect(self.ccu_websocket_uri),
                timeout=self.connection_timeout
            )
            self.logger.info("✅ Connected to CCU WebSocket server")
        except Exception as e:
            for fallback_port in self.fallback_ports:
                try:
                    fallback_uri = f"ws://localhost:{fallback_port}/ws"
                    self.websocket_connection = await asyncio.wait_for(
                        websockets.connect(fallback_uri),
                        timeout=self.connection_timeout
                    )
                    self.logger.info(f"✅ Connected to CCU on fallback port {fallback_port}")
                    self.ccu_websocket_uri = fallback_uri
                    return
                except:
                    continue
            raise Exception("Failed to connect to CCU on all ports")
    
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
    
    async def _handle_ccu_message(self, message: str):
        """Handle message from CCU."""
        try:
            data = json.loads(message)
            message_type = data.get("type", "unknown")
            if message_type == "welcome":
                self.logger.info("Received welcome from CCU")
            elif message_type == "activate":
                await self._send_to_ccu({"type": "activation_ack", "status": "activated", "service": "TD"})
        except Exception as e:
            self.logger.error(f"Error handling CCU message: {e}")
    
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
                    await self._send_to_ccu({"type": "heartbeat", "service": "TD", "status": "active"})
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in heartbeat: {e}")
    
    async def stop_websocket_client(self):
        """Stop WebSocket client."""
        try:
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
            if self.websocket_task:
                self.websocket_task.cancel()
            if self.websocket_connection:
                await self.websocket_connection.close()
                self.websocket_connection = None
            self.logger.info("✅ WebSocket client stopped")
        except Exception as e:
            self.logger.error(f"Error stopping WebSocket client: {e}")



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
        """Route command to the appropriate TD module/method."""
        # Service control
        if command == "activate":
            return self._activate_service()
        elif command == "deactivate":
            return self._deactivate_service()
        elif command == "status":
            return self._get_service_status()
        elif command == "health_check":
            return await self._get_health_status()
        
        # Orchestration configuration
        elif command == "set_orchestration_mode":
            return self._set_orchestration_mode(parameters)
        elif command == "configure_calculation_blocks":
            return self._configure_calculation_blocks(parameters)
        elif command == "set_concurrent_limits":
            return self._set_concurrent_limits(parameters)
        elif command == "configure_binary_processing":
            return self._configure_binary_processing(parameters)
        
        # Calculation block management
        elif command == "enable_calculation_block":
            return self._enable_calculation_block(parameters)
        elif command == "disable_calculation_block":
            return self._disable_calculation_block(parameters)
        elif command == "get_calculation_blocks_status":
            return self._get_calculation_blocks_status()
        elif command == "reset_calculation_block":
            return self._reset_calculation_block(parameters)
        
        # Orchestration control
        elif command == "start_orchestration":
            return await self._start_orchestration(parameters)
        elif command == "stop_orchestration":
            return await self._stop_orchestration(parameters)
        elif command == "get_active_orchestrations":
            return self._get_active_orchestrations()
        elif command == "cancel_orchestration":
            return await self._cancel_orchestration(parameters)
        
        # Binary file processing
        elif command == "process_binary_file":
            return await self._process_binary_file(parameters)
        elif command == "set_binary_format":
            return self._set_binary_format(parameters)
        elif command == "get_binary_processing_status":
            return self._get_binary_processing_status()
        
        # Result aggregation and OCM
        elif command == "configure_result_aggregation":
            return self._configure_result_aggregation(parameters)
        elif command == "set_ocm_formatting":
            return self._set_ocm_formatting(parameters)
        elif command == "get_aggregation_results":
            return self._get_aggregation_results(parameters)
        
        # Remote test execution
        elif command == "run_test":
            return await self._run_test(parameters)
        elif command == "test_orchestration":
            return await self._test_orchestration(parameters)
        elif command == "test_calculation_block":
            return await self._test_calculation_block(parameters)
        elif command == "test_binary_processing":
            return await self._test_binary_processing(parameters)
        
        # Reset and maintenance
        elif command == "reset_module":
            return self._reset_module(parameters)
        elif command == "reset_all":
            return self._reset_all()
        elif command == "clear_orchestration_cache":
            return self._clear_orchestration_cache()
        elif command == "restart_calculation_engine":
            return await self._restart_calculation_engine()
        
        # Monitoring and data
        elif command == "get_errors":
            return self._get_errors()
        elif command == "get_monitoring":
            return self._get_monitoring()
        elif command == "get_orchestration_stats":
            return self._get_orchestration_stats()
        elif command == "get_calculation_performance":
            return self._get_calculation_performance()
        
        # Performance optimization
        elif command == "optimize_orchestration":
            return self._optimize_orchestration(parameters)
        elif command == "set_performance_mode":
            return self._set_performance_mode(parameters)
        
        # Automatic code generation
        elif command == "auto_code_gen":
            return await self._auto_code_gen()
        else:
            raise ValueError(f"Unknown command: {command}")

    def _activate_service(self):
        """Activate the TD orchestration service."""
        self.td_state["orchestration_enabled"] = True
        self.td_state["binary_processing_enabled"] = True
        self.td_state["calculation_coordination_enabled"] = True
        self.logger.info("ECM: TD orchestration service activated")
        return {
            "status": "activated", 
            "capabilities": [
                "binary_file_processing", 
                "multi_calculation_orchestration", 
                "result_aggregation", 
                "ocm_integration",
                "calculation_coordination"
            ]
        }

    def _deactivate_service(self):
        """Deactivate the TD orchestration service."""
        self.td_state["orchestration_enabled"] = False
        self.logger.info("ECM: TD orchestration service deactivated")
        return {"status": "deactivated"}

    def _get_service_status(self):
        """Get comprehensive TD service status."""
        status = {
            "service": "TD",
            "version": "1.0.0",
            "connection_status": self.connection_status,
            "td_state": self.td_state,
            "last_command": self.last_command,
            "last_command_result": self.last_command_result,
            "stats": self.stats.copy(),
            "supported_routes": list(self.td_state["route_handlers"].keys()),
            "processing_modes": list(self.td_state["processing_modes"].keys()),
            "capabilities": [
                "binary_file_processing",
                "multi_calculation_orchestration",
                "result_aggregation",
                "ocm_integration",
                "calculation_coordination",
                "priority_based_processing",
                "concurrent_execution"
            ]
        }
        return status

    async def _get_health_status(self):
        """Get comprehensive health status."""
        try:
            module_health = {}
            all_healthy = True
            
            # Check core modules if available
            for module_name in ["bfpm", "afm", "rom", "cam", "cim", "rmm", "msm", "emm"]:
                if module_name in globals():
                    module = globals()[module_name]
                    if hasattr(module, 'health_check'):
                        health = await module.health_check()
                        module_health[module_name] = health
                        if not health.get('healthy', True):
                            all_healthy = False
            
            # Check calculation block availability
            available_routes = sum(1 for route in self.td_state["route_handlers"].values() if route["available"])
            total_routes = len(self.td_state["route_handlers"])
            
            return {
                "healthy": all_healthy,
                "service": "TD",
                "orchestration_operational": self.td_state["orchestration_enabled"],
                "binary_processing_operational": self.td_state["binary_processing_enabled"],
                "calculation_coordination_operational": self.td_state["calculation_coordination_enabled"],
                "available_routes": f"{available_routes}/{total_routes}",
                "processing_modes": self.td_state["processing_modes"],
                "modules": module_health,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"healthy": False, "error": str(e), "service": "TD"}

    def _set_orchestration_mode(self, parameters: Dict[str, Any]):
        """Configure orchestration mode."""
        mode = parameters.get("mode", "orchestrated")  # single_calculation, multi_calculation, orchestrated
        enable_parallel = parameters.get("enable_parallel", True)
        optimization_level = parameters.get("optimization_level", "balanced")  # speed, balanced, accuracy
        
        # Update settings
        self.td_state["current_settings"]["default_mode"] = mode
        self.td_state["processing_modes"][mode] = True
        
        # Apply to ROM if available
        if "rom" in globals() and hasattr(rom, 'set_orchestration_mode'):
            rom.set_orchestration_mode(mode, enable_parallel, optimization_level)
            
        self.logger.info(f"ECM: Orchestration mode set to {mode}, parallel: {enable_parallel}")
        return {
            "status": "orchestration_mode_updated", 
            "mode": mode,
            "parallel": enable_parallel,
            "optimization": optimization_level
        }

    def _configure_calculation_blocks(self, parameters: Dict[str, Any]):
        """Configure calculation block settings."""
        block_priorities = parameters.get("block_priorities", {})
        timeout_per_block = parameters.get("timeout_per_block", 60)
        retry_attempts = parameters.get("retry_attempts", 3)
        enable_all_blocks = parameters.get("enable_all_blocks", True)
        
        # Update block settings
        for route_name, route_info in self.td_state["route_handlers"].items():
            if route_name in block_priorities:
                route_info["priority"] = block_priorities[route_name]
            route_info["available"] = enable_all_blocks
        
        # Apply to CIM if available
        if "cim" in globals() and hasattr(cim, 'configure_blocks'):
            cim.configure_blocks(block_priorities, timeout_per_block, retry_attempts)
            
        self.logger.info(f"ECM: Calculation blocks configured - timeout: {timeout_per_block}s, retries: {retry_attempts}")
        return {
            "status": "calculation_blocks_configured",
            "timeout": timeout_per_block,
            "retries": retry_attempts,
            "priorities": block_priorities
        }

    def _set_concurrent_limits(self, parameters: Dict[str, Any]):
        """Configure concurrent processing limits."""
        max_concurrent_calculations = parameters.get("max_concurrent_calculations", 12)
        max_concurrent_orchestrations = parameters.get("max_concurrent_orchestrations", 5)
        calculation_timeout = parameters.get("calculation_timeout", 300)
        
        # Update limits
        self.td_state["current_settings"]["max_concurrent_calculations"] = max_concurrent_calculations
        self.td_state["current_settings"]["max_concurrent_orchestrations"] = max_concurrent_orchestrations
        
        # Apply to ROM if available
        if "rom" in globals() and hasattr(rom, 'set_concurrent_limits'):
            rom.set_concurrent_limits(max_concurrent_calculations, max_concurrent_orchestrations, calculation_timeout)
            
        self.logger.info(f"ECM: Concurrent limits updated - calculations: {max_concurrent_calculations}, orchestrations: {max_concurrent_orchestrations}")
        return {
            "status": "concurrent_limits_updated",
            "limits": {
                "max_concurrent_calculations": max_concurrent_calculations,
                "max_concurrent_orchestrations": max_concurrent_orchestrations,
                "calculation_timeout": calculation_timeout
            }
        }

    def _configure_binary_processing(self, parameters: Dict[str, Any]):
        """Configure binary file processing settings."""
        supported_formats = parameters.get("supported_formats", ["jfa_v1", "jfa_v2", "legacy"])
        default_template = parameters.get("default_template", "default")
        enable_validation = parameters.get("enable_validation", True)
        max_file_size = parameters.get("max_file_size", 50 * 1024 * 1024)  # 50MB
        
        # Update settings
        self.td_state["current_settings"]["binary_file_formats"] = supported_formats
        self.td_state["binary_processing_enabled"] = enable_validation
        
        # Apply to BFPM if available
        if "bfpm" in globals() and hasattr(bfpm, 'configure_processing'):
            bfpm.configure_processing(supported_formats, default_template, enable_validation, max_file_size)
            
        self.logger.info(f"ECM: Binary processing configured - formats: {supported_formats}, validation: {enable_validation}")
        return {
            "status": "binary_processing_configured",
            "supported_formats": supported_formats,
            "default_template": default_template,
            "validation": enable_validation,
            "max_file_size": max_file_size
        }

    def _enable_calculation_block(self, parameters: Dict[str, Any]):
        """Enable a specific calculation block."""
        block_name = parameters.get("block_name")
        priority = parameters.get("priority", 1)
        
        if block_name in self.td_state["route_handlers"]:
            self.td_state["route_handlers"][block_name]["available"] = True
            self.td_state["route_handlers"][block_name]["priority"] = priority
            
            # Apply to CIM if available
            if "cim" in globals() and hasattr(cim, 'enable_calculation'):
                cim.enable_calculation(block_name, priority)
            
            self.logger.info(f"ECM: Calculation block '{block_name}' enabled")
            return {"status": "calculation_block_enabled", "block": block_name, "priority": priority}
        else:
            raise ValueError(f"Unknown calculation block: {block_name}")

    def _disable_calculation_block(self, parameters: Dict[str, Any]):
        """Disable a specific calculation block."""
        block_name = parameters.get("block_name")
        
        if block_name in self.td_state["route_handlers"]:
            self.td_state["route_handlers"][block_name]["available"] = False
            
            # Apply to CIM if available
            if "cim" in globals() and hasattr(cim, 'disable_calculation'):
                cim.disable_calculation(block_name)
            
            self.logger.info(f"ECM: Calculation block '{block_name}' disabled")
            return {"status": "calculation_block_disabled", "block": block_name}
        else:
            raise ValueError(f"Unknown calculation block: {block_name}")

    def _get_calculation_blocks_status(self):
        """Get status of all calculation blocks."""
        return {
            "status": "calculation_blocks_status_retrieved", 
            "blocks": self.td_state["route_handlers"]
        }

    def _reset_calculation_block(self, parameters: Dict[str, Any]):
        """Reset a specific calculation block."""
        block_name = parameters.get("block_name")
        
        if block_name in self.td_state["route_handlers"]:
            # Reset statistics
            self.td_state["route_handlers"][block_name]["active"] = 0
            self.td_state["route_handlers"][block_name]["total_processed"] = 0
            
            # Apply to CIM if available
            if "cim" in globals() and hasattr(cim, 'reset_calculation'):
                cim.reset_calculation(block_name)
            
            self.logger.info(f"ECM: Calculation block '{block_name}' reset")
            return {"status": "calculation_block_reset", "block": block_name}
        else:
            raise ValueError(f"Unknown calculation block: {block_name}")

    async def _start_orchestration(self, parameters: Dict[str, Any]):
        """Start a new orchestration."""
        binary_file_path = parameters.get("binary_file_path")
        request_id = parameters.get("request_id")
        priority = parameters.get("priority", "normal")
        
        try:
            if "rom" in globals() and hasattr(rom, 'start_orchestration'):
                result = await rom.start_orchestration(binary_file_path, request_id, priority)
                
                # Update stats
                self.td_state["orchestration_stats"]["total_orchestrations"] += 1
                
                self.logger.info(f"ECM: Orchestration started for request {request_id}")
                return {
                    "status": "orchestration_started",
                    "request_id": request_id,
                    "binary_file": binary_file_path,
                    "result": result
                }
            else:
                raise Exception("ROM module not available")
        except Exception as e:
            self.td_state["orchestration_stats"]["failed_orchestrations"] += 1
            raise Exception(f"Failed to start orchestration: {e}")

    async def _stop_orchestration(self, parameters: Dict[str, Any]):
        """Stop an active orchestration."""
        request_id = parameters.get("request_id")
        
        try:
            if "rom" in globals() and hasattr(rom, 'stop_orchestration'):
                result = await rom.stop_orchestration(request_id)
                
                self.logger.info(f"ECM: Orchestration stopped for request {request_id}")
                return {"status": "orchestration_stopped", "request_id": request_id, "result": result}
            else:
                raise Exception("ROM module not available")
        except Exception as e:
            raise Exception(f"Failed to stop orchestration: {e}")

    def _get_active_orchestrations(self):
        """Get list of active orchestrations."""
        try:
            orchestrations = []
            if "rom" in globals() and hasattr(rom, 'get_active_orchestrations'):
                orchestrations = rom.get_active_orchestrations()
                
            return {"status": "active_orchestrations_retrieved", "orchestrations": orchestrations}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _cancel_orchestration(self, parameters: Dict[str, Any]):
        """Cancel an orchestration."""
        request_id = parameters.get("request_id")
        reason = parameters.get("reason", "user_request")
        
        try:
            if "rom" in globals() and hasattr(rom, 'cancel_orchestration'):
                result = await rom.cancel_orchestration(request_id, reason)
                
                self.logger.info(f"ECM: Orchestration cancelled for request {request_id}")
                return {"status": "orchestration_cancelled", "request_id": request_id, "reason": reason}
            else:
                raise Exception("ROM module not available")
        except Exception as e:
            raise Exception(f"Failed to cancel orchestration: {e}")

    async def _process_binary_file(self, parameters: Dict[str, Any]):
        """Process a binary file directly."""
        binary_file_path = parameters.get("binary_file_path")
        request_id = parameters.get("request_id")
        template_format = parameters.get("template_format", "auto_detect")
        
        try:
            if "bfpm" in globals() and hasattr(bfpm, 'process_binary_file'):
                result = await bfpm.process_binary_file(binary_file_path, template_format)
                
                self.logger.info(f"ECM: Binary file processed: {binary_file_path}")
                return {
                    "status": "binary_file_processed",
                    "file_path": binary_file_path,
                    "request_id": request_id,
                    "result": result
                }
            else:
                raise Exception("BFPM module not available")
        except Exception as e:
            raise Exception(f"Failed to process binary file: {e}")

    def _set_binary_format(self, parameters: Dict[str, Any]):
        """Set binary file format preference."""
        format_preference = parameters.get("format", "jfa_v1")  # jfa_v1, jfa_v2, legacy
        auto_detect = parameters.get("auto_detect", True)
        
        # Update settings
        if format_preference not in self.td_state["current_settings"]["binary_file_formats"]:
            self.td_state["current_settings"]["binary_file_formats"].append(format_preference)
        
        # Apply to BFPM if available
        if "bfpm" in globals() and hasattr(bfpm, 'set_format_preference'):
            bfpm.set_format_preference(format_preference, auto_detect)
            
        self.logger.info(f"ECM: Binary format preference set to {format_preference}")
        return {"status": "binary_format_updated", "format": format_preference, "auto_detect": auto_detect}

    def _get_binary_processing_status(self):
        """Get binary processing status."""
        try:
            status = {"enabled": self.td_state["binary_processing_enabled"]}
            
            if "bfpm" in globals() and hasattr(bfpm, 'get_processing_status'):
                status.update(bfpm.get_processing_status())
                
            return {"status": "binary_processing_status_retrieved", "processing_status": status}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _configure_result_aggregation(self, parameters: Dict[str, Any]):
        """Configure result aggregation settings."""
        aggregation_mode = parameters.get("mode", "comprehensive")  # simple, comprehensive, custom
        include_metadata = parameters.get("include_metadata", True)
        include_performance = parameters.get("include_performance", True)
        
        # Apply to CAM if available
        if "cam" in globals() and hasattr(cam, 'configure_aggregation'):
            cam.configure_aggregation(aggregation_mode, include_metadata, include_performance)
            
        self.logger.info(f"ECM: Result aggregation configured - mode: {aggregation_mode}")
        return {
            "status": "result_aggregation_configured",
            "mode": aggregation_mode,
            "include_metadata": include_metadata,
            "include_performance": include_performance
        }

    def _set_ocm_formatting(self, parameters: Dict[str, Any]):
        """Configure OCM output formatting."""
        format_type = parameters.get("format", "aggregated_json")
        enable_section_separation = parameters.get("enable_section_separation", True)
        include_calculation_details = parameters.get("include_calculation_details", True)
        
        # Apply to OCMIM if available
        if "ocmim" in globals() and hasattr(ocmim, 'configure_formatting'):
            ocmim.configure_formatting(format_type, enable_section_separation, include_calculation_details)
            
        self.logger.info(f"ECM: OCM formatting configured - format: {format_type}")
        return {
            "status": "ocm_formatting_configured",
            "format": format_type,
            "section_separation": enable_section_separation,
            "calculation_details": include_calculation_details
        }

    def _get_aggregation_results(self, parameters: Dict[str, Any]):
        """Get aggregated calculation results."""
        request_id = parameters.get("request_id")
        
        try:
            results = {}
            if "cam" in globals() and hasattr(cam, 'get_aggregation_results'):
                results = cam.get_aggregation_results(request_id)
            
            return {"status": "aggregation_results_retrieved", "request_id": request_id, "results": results}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _run_test(self, parameters: Dict[str, Any]):
        """Run a test via TMM."""
        test_code = parameters.get("test_code")
        if "tmm" in globals() and hasattr(tmm, 'run_test'):
            result = await tmm.run_test(test_code)
        else:
            raise ValueError("TMM module not available")
        
        self.logger.info(f"ECM: Test {test_code} executed")
        return {"status": "test_executed", "test_code": test_code, "result": result}

    async def _test_orchestration(self, parameters: Dict[str, Any]):
        """Test orchestration functionality."""
        test_binary_path = parameters.get("test_binary_path", "test/mock_binary.bin")
        test_calculations = parameters.get("calculations", ["forward", "parallel"])
        
        try:
            if "rom" in globals() and hasattr(rom, 'test_orchestration'):
                result = await rom.test_orchestration(test_binary_path, test_calculations)
            else:
                result = {"mock_test": True, "calculations": test_calculations}
            
            self.logger.info("ECM: Orchestration test executed")
            return {"status": "orchestration_test_executed", "result": result}
        except Exception as e:
            return {"status": "orchestration_test_failed", "error": str(e)}

    async def _test_calculation_block(self, parameters: Dict[str, Any]):
        """Test specific calculation block."""
        block_name = parameters.get("block_name", "forward")
        test_data = parameters.get("test_data", {})
        
        try:
            if "cim" in globals() and hasattr(cim, 'test_calculation_block'):
                result = await cim.test_calculation_block(block_name, test_data)
            else:
                result = {"block": block_name, "test": "mock_passed"}
            
            self.logger.info(f"ECM: Calculation block test executed for {block_name}")
            return {"status": "calculation_block_test_executed", "block": block_name, "result": result}
        except Exception as e:
            return {"status": "calculation_block_test_failed", "error": str(e)}

    async def _test_binary_processing(self, parameters: Dict[str, Any]):
        """Test binary file processing."""
        test_file_path = parameters.get("test_file_path", "test/mock_binary.bin")
        format_type = parameters.get("format", "jfa_v1")
        
        try:
            if "bfpm" in globals() and hasattr(bfpm, 'test_processing'):
                result = await bfpm.test_processing(test_file_path, format_type)
            else:
                result = {"file": test_file_path, "format": format_type, "test": "mock_passed"}
            
            self.logger.info("ECM: Binary processing test executed")
            return {"status": "binary_processing_test_executed", "result": result}
        except Exception as e:
            return {"status": "binary_processing_test_failed", "error": str(e)}

    def _reset_module(self, parameters: Dict[str, Any]):
        """Reset a specific TD module."""
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
        """Reset the entire TD service."""
        # Reset TD state
        self.td_state = {
            "orchestration_enabled": True,
            "binary_processing_enabled": True,
            "calculation_coordination_enabled": True,
            "processing_modes": {"single_calculation": True, "multi_calculation": True, "orchestrated": True},
            "current_settings": {
                "default_mode": "orchestrated",
                "max_concurrent_calculations": 12,
                "max_concurrent_orchestrations": 5,
                "binary_file_formats": ["jfa_v1", "jfa_v2", "legacy"]
            },
            "route_handlers": {route: {"available": True, "active": 0, "total_processed": 0}
                                 for route in ["forward", "parallel", "sequential"]},
            "orchestration_stats": {
                "total_orchestrations": 0, "successful_orchestrations": 0,
                "failed_orchestrations": 0, "average_orchestration_time": 0.0
            }
        }
        
        self.logger.info("ECM: All TD modules reset")
        return {"status": "all_reset"}

    def _clear_orchestration_cache(self):
        """Clear orchestration cache."""
        try:
            # Clear caches in various modules if available
            if "rom" in globals() and hasattr(rom, 'clear_cache'):
                rom.clear_cache()
            if "cam" in globals() and hasattr(cam, 'clear_cache'):
                cam.clear_cache()
                
            self.logger.info("ECM: Orchestration cache cleared")
            return {"status": "orchestration_cache_cleared"}
        except Exception as e:
            return {"status": "cache_clear_error", "error": str(e)}

    async def _restart_calculation_engine(self):
        """Restart the calculation engine."""
        try:
            if "cim" in globals() and hasattr(cim, 'restart_engine'):
                result = await cim.restart_engine()
                
                self.logger.info("ECM: Calculation engine restarted")
                return {"status": "calculation_engine_restarted", "result": result}
            else:
                return {"status": "calculation_engine_restart_not_available"}
        except Exception as e:
            return {"status": "calculation_engine_restart_failed", "error": str(e)}

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

    def _get_orchestration_stats(self):
        """Get orchestration statistics."""
        stats = {
            "td_state": self.td_state,
            "command_stats": self.stats,
            "service_status": {
                "orchestration_enabled": self.td_state["orchestration_enabled"],
                "binary_processing_enabled": self.td_state["binary_processing_enabled"],
                "calculation_coordination_enabled": self.td_state["calculation_coordination_enabled"],
                "processing_modes": self.td_state["processing_modes"]
            }
        }
        
        # Add module-specific stats if available
        if "rom" in globals() and hasattr(rom, 'stats'):
            stats["orchestration_module"] = rom.stats
        if "cam" in globals() and hasattr(cam, 'stats'):
            stats["aggregation_module"] = cam.stats
        if "bfpm" in globals() and hasattr(bfpm, 'stats'):
            stats["binary_processing"] = bfpm.stats
            
        return {"status": "orchestration_stats_retrieved", "stats": stats}

    def _get_calculation_performance(self):
        """Get calculation performance metrics."""
        if "cim" in globals() and hasattr(cim, 'get_performance_metrics'):
            performance = cim.get_performance_metrics()
        else:
            performance = {"route_handlers": self.td_state["route_handlers"]}
            
        return {"status": "calculation_performance_retrieved", "performance": performance}

    def _optimize_orchestration(self, parameters: Dict[str, Any]):
        """Optimize orchestration performance."""
        optimization_target = parameters.get("target", "speed")  # speed, accuracy, resource_usage
        enable_caching = parameters.get("enable_caching", True)
        
        # Apply to ROM if available
        if "rom" in globals() and hasattr(rom, 'optimize'):
            rom.optimize(optimization_target, enable_caching)
            
        self.logger.info(f"ECM: Orchestration optimized for {optimization_target}")
        return {
            "status": "orchestration_optimized",
            "target": optimization_target,
            "caching": enable_caching
        }

    def _set_performance_mode(self, parameters: Dict[str, Any]):
        """Set performance mode."""
        mode = parameters.get("mode", "balanced")  # speed, balanced, accuracy, resource_saving
        
        # Update settings and apply to modules
        if "rom" in globals() and hasattr(rom, 'set_performance_mode'):
            rom.set_performance_mode(mode)
        if "cim" in globals() and hasattr(cim, 'set_performance_mode'):
            cim.set_performance_mode(mode)
            
        self.logger.info(f"ECM: Performance mode set to {mode}")
        return {"status": "performance_mode_updated", "mode": mode}

    async def _auto_code_gen(self):
        """Trigger automatic code generation in EMM."""
        try:
            if "emm" in globals() and hasattr(emm, 'generate_error_codes_for_codebase'):
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
        """Stream logs to CCU."""
        self.logger.info(f"ECM: Streaming logs at level {level}")
        callback(f"[ECM] Log streaming started at level {level} for TD Orchestration")

    def stream_monitoring(self, callback: Callable[[Dict[str, Any]], None]):
        """Stream monitoring data to CCU."""
        self.logger.info("ECM: Streaming monitoring data")
        callback({"status": "monitoring_stream_started", "service": "TD"})

    def get_module_status(self) -> Dict[str, Any]:
        """Get ECM module status."""
        return {
            "module": "ECM",
            "service": "TD",
            "status": self.connection_status,
            "td_state": self.td_state,
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

    async def start_td_microservice(self):
        """
        Start the complete TD microservice.
        
        This method integrates the functionality from start_td.py, allowing CCU 
        to start and manage the TD microservice through ECM.
        """
        try:
            # Configure logging for TD service
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.StreamHandler(),
                    logging.FileHandler('td_service.log')
                ]
            )
            
            self.logger.info("ECM: Starting TD Microservice...")
            
            # Import and create TD microservice instance
            from TD_main import TDMicroservice
            self.td_microservice = TDMicroservice()
            
            # Start the TD service
            await self.td_microservice.start()
            
            # Activate TD service through ECM
            self._activate_service()
            
            # Update service state
            self.td_state["microservice_instance"] = self.td_microservice
            self.td_state["service_running"] = True
            self.td_state["start_time"] = datetime.now()
            
            self.logger.info("ECM: TD Microservice started successfully")
            self.logger.info("ECM: TD Service endpoints:")
            self.logger.info("  - API Server: http://localhost:8003")
            self.logger.info("  - Health Check: http://localhost:8003/health")
            self.logger.info("  - WebSocket: ws://localhost:11492")
            
            return {
                "status": "started",
                "service": "TD",
                "endpoints": {
                    "api_server": "http://localhost:8003",
                    "health_check": "http://localhost:8003/health",
                    "websocket": "ws://localhost:11492"
                },
                "start_time": self.td_state["start_time"].isoformat(),
                "message": "TD Microservice started successfully via ECM"
            }
            
        except Exception as e:
            self.logger.error(f"ECM: Failed to start TD microservice: {e}")
            self.td_state["service_running"] = False
            self.td_state["last_error"] = str(e)
            
            return {
                "status": "failed",
                "service": "TD", 
                "error": str(e),
                "message": "Failed to start TD Microservice"
            }
    
    async def stop_td_microservice(self):
        """
        Stop the TD microservice.
        
        This method stops the TD microservice and cleans up all resources.
        """
        try:
            self.logger.info("ECM: Stopping TD Microservice...")
            
            # Stop the TD microservice if it exists
            if hasattr(self, 'td_microservice') and self.td_microservice:
                await self.td_microservice.stop()
                self.td_microservice = None
            
            # Deactivate TD service
            self._deactivate_service()
            
            # Update service state
            self.td_state["microservice_instance"] = None
            self.td_state["service_running"] = False
            self.td_state["stop_time"] = datetime.now()
            
            self.logger.info("ECM: TD Microservice stopped successfully")
            
            return {
                "status": "stopped",
                "service": "TD",
                "stop_time": self.td_state["stop_time"].isoformat(),
                "message": "TD Microservice stopped successfully via ECM"
            }
            
        except Exception as e:
            self.logger.error(f"ECM: Failed to stop TD microservice: {e}")
            self.td_state["last_error"] = str(e)
            
            return {
                "status": "error",
                "service": "TD",
                "error": str(e),
                "message": "Failed to stop TD Microservice"
            }
    
    async def restart_td_microservice(self):
        """
        Restart the TD microservice.
        
        This method stops and then starts the TD microservice.
        """
        try:
            self.logger.info("ECM: Restarting TD Microservice...")
            
            # Stop the current instance
            stop_result = await self.stop_td_microservice()
            if stop_result["status"] != "stopped":
                return stop_result
            
            # Wait a moment for cleanup
            await asyncio.sleep(2)
            
            # Start new instance
            start_result = await self.start_td_microservice()
            
            return {
                "status": "restarted" if start_result["status"] == "started" else "failed",
                "service": "TD",
                "restart_time": datetime.now().isoformat(),
                "start_result": start_result,
                "message": "TD Microservice restarted via ECM"
            }
            
        except Exception as e:
            self.logger.error(f"ECM: Failed to restart TD microservice: {e}")
            return {
                "status": "error",
                "service": "TD",
                "error": str(e),
                "message": "Failed to restart TD Microservice"
            }
    
    async def get_td_service_status(self):
        """
        Get comprehensive TD microservice status.
        
        Returns detailed status information about the TD microservice.
        """
        try:
            base_status = self._get_service_status()
            
            # Add microservice-specific status
            if hasattr(self, 'td_microservice') and self.td_microservice:
                microservice_status = self.td_microservice.get_status()
                base_status.update({
                    "microservice_status": microservice_status,
                    "route_handlers": await self.td_microservice.get_calculation_status()
                })
            
            base_status.update({
                "service_running": self.td_state.get("service_running", False),
                "start_time": self.td_state.get("start_time", {}).isoformat() if self.td_state.get("start_time") else None,
                "uptime_seconds": (datetime.now() - self.td_state["start_time"]).total_seconds() if self.td_state.get("start_time") else 0
            })
            
            return base_status
            
        except Exception as e:
            self.logger.error(f"ECM: Error getting TD service status: {e}")
            return {
                "status": "error",
                "service": "TD",
                "error": str(e),
                "service_running": False
            }

    async def start(self):
        """Start the ECM module."""
        self.is_active = True
        await self.start_websocket_client()
        self.logger.info("✅ TD ECM started successfully")

    async def stop(self):
        """Stop the ECM module."""
        # Stop TD microservice if running
        if self.td_state.get("service_running", False):
            await self.stop_td_microservice()
            
        self.is_active = False
        await self.stop_websocket_client()
        self.logger.info("🔌 TD ECM stopped successfully")

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        return {
            "healthy": self.connection_status == ECMConnectionStatus.CONNECTED,
            "module": "ECM",
            "service": "TD",
            "connection_status": self.connection_status,
            "orchestration_operational": self.td_state["orchestration_enabled"],
            "binary_processing_operational": self.td_state["binary_processing_enabled"],
            "calculation_coordination_operational": self.td_state["calculation_coordination_enabled"],
            "timestamp": datetime.now().isoformat()
        }

# Global instances
ecm = ExternalControlModule()
ECM = ExternalControlModule() 