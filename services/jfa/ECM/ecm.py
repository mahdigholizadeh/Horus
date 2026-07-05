"""
External Control Module (ECM) for JFA Microservice

Primary interface between the JFA microservice and the Central Control Unit (CCU).
Handles service control, monitoring/log streaming, configuration, remote test execution, 
resets, JSON analysis configuration, template validation settings, binary data management.

JFA-Specific Capabilities:
- JSON template validation configuration
- Binary data generation settings
- Analysis parameter tuning
- Template structure management
- Data processing pipeline control
- Validation rule configuration
- Analysis mode configuration
- Binary file format management
"""

import asyncio
import logging
import json
import websockets
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
import threading
import queue

from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler

# Import JFA modules for command routing
try:
    from JDPM.jdpm import jdpm
    from TVM.tvm import tvm
    from BDM.bdm import bdm
    from DAM.dam import dam
    from IPM.ipm import ipm
    from OPM.opm import opm
    from FIM.fim import fim
    from ARM.arm import arm
    from CIM.cim import cim
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
    External Control Module (ECM) for JFA
    - Maintains persistent connection to CCU
    - Parses and routes commands from CCU to appropriate JFA modules
    - Streams logs and monitoring data to CCU
    - Handles service control, configuration, resets, test execution, JSON analysis, and more
    - Manages JFA-specific capabilities: template validation, binary generation, analysis
    - All actions are traceable and logged
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # NEW ARCHITECTURE: WebSocket CLIENT configuration
        self.ccu_websocket_uri = "ws://localhost:4444/ws"
        self.websocket_connection = None
        self.websocket_task = None 
        self.heartbeat_task = None
        self.connection_retry_count = 0
        self.max_retry_attempts = 10
        self.retry_delay = 5  # seconds
        self.heartbeat_interval = 30  # seconds
        self.connection_timeout = 5.0  # seconds
        self.fallback_ports = [4454, 4464, 4474]
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
        self.current_port = 4444  # Primary CCU JFAIM port
        self.is_active = False  # ECM module activation state
        
        # JFA-specific state
        self.jfa_state = {
            "analysis_enabled": True,
            "template_validation_enabled": True,
            "binary_generation_enabled": True,
            "processing_modes": {
                "template": True,
                "binary": True,
                "comprehensive": True
            },
            "current_settings": {
                "default_mode": "comprehensive",
                "max_template_size": 10485760,  # 10MB
                "validation_strictness": "high",
                "batch_size": 100
            },
            "analysis_stats": {
                "templates_validated": 0,
                "binary_files_generated": 0,
                "analyses_completed": 0,
                "validation_success_rate": 0.0
            }
        }

    async def _start_connection(self):
        """Start WebSocket connection to CCU."""
        try:
            self._websocket = await websockets.connect(self._ccu_url)
            self.connection_status = ECMConnectionStatus.CONNECTED
            self.logger.info(f"ECM: Connected to CCU at {self._ccu_url}")
            
            # Send service registration
            await self._send_registration()
            
            # Start message handling loop
            asyncio.create_task(self._message_loop())
            
        except Exception as e:
            self.connection_status = ECMConnectionStatus.ERROR
            self.logger.error(f"ECM connection error: {e}")
            self.error_manager.log_error_with_generation("ECM", "ExternalControlModule", "_start_connection", f"Connection error: {e}")
    
    async def _send_registration(self):
        """Send service registration message to CCU."""
        try:
            registration_msg = {
                "type": "service_registration",
                "service": "JFA",
                "capabilities": [
                    "template_validation",
                    "binary_generation", 
                    "data_analysis",
                    "json_processing",
                    "file_management",
                    "error_management",
                    "configuration_management",
                    "background_tasks",
                    "test_management",
                    "monitoring"
                ],
                "status": {
                    "active": True,
                    "version": "1.0.0",
                    "modules": ["JDPM", "TVM", "BDM", "DAM", "IPM", "OPM", "FIM", "ECM", "ARM", "CIM", "EMM", "BTM", "TMM", "MSM"]
                },
                "timestamp": datetime.now().isoformat()
            }
            
            await self._websocket.send(json.dumps(registration_msg))
            self._registration_sent = True
            self.logger.info("ECM: Service registration sent to CCU")
            
        except Exception as e:
            self.logger.error(f"ECM: Failed to send registration: {e}")
    
    async def _message_loop(self):
        """Handle incoming messages from CCU."""
        try:
            while not self._stop_event.is_set():
                if not self._websocket:
                    # Try to reconnect
                    await self._reconnect()
                    if not self._websocket:
                        await asyncio.sleep(self._reconnect_delay)
                        continue
                
                try:
                    message = await asyncio.wait_for(self._websocket.recv(), timeout=1.0)
                    await self._handle_message(json.loads(message))
                except asyncio.TimeoutError:
                    continue
                except websockets.exceptions.ConnectionClosed:
                    self.connection_status = ECMConnectionStatus.DISCONNECTED
                    self.logger.warning("ECM: Connection to CCU closed, attempting reconnect...")
                    self._websocket = None
                except Exception as e:
                    self.logger.error(f"ECM: Error handling message: {e}")
                    
        except Exception as e:
            self.logger.error(f"ECM: Message loop error: {e}")
        finally:
            if self._websocket:
                await self._websocket.close()
    
    async def _reconnect(self):
        """Attempt to reconnect to CCU."""
        try:
            self._websocket = await websockets.connect(self._ccu_url)
            self.connection_status = ECMConnectionStatus.CONNECTED
            self.logger.info(f"ECM: Reconnected to CCU at {self._ccu_url}")
            
            # Send service registration again
            await self._send_registration()
            
        except Exception as e:
            self.connection_status = ECMConnectionStatus.ERROR
            self.logger.error(f"ECM: Reconnection failed: {e}")
            self._websocket = None
    
    async def _handle_message(self, message: Dict[str, Any]):
        """Handle incoming message from CCU."""
        try:
            msg_type = message.get("type")
            
            if msg_type == "command":
                command = message.get("command")
                parameters = message.get("parameters", {})
                result = await self.receive_command(command, parameters)
                
                # Send response back to CCU
                response = {
                    "type": "status_response" if command == "get_status" else "command_response",
                    "command": command,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                }
                await self._websocket.send(json.dumps(response, default=str))
                
            elif msg_type == "ping":
                # Respond to ping
                pong = {
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                }
                await self._websocket.send(json.dumps(pong))
                
        except Exception as e:
            self.logger.error(f"ECM: Error handling message: {e}")

    def stop_connection(self):
        """Stop the persistent connection."""
        self._stop_event.set()
        if self._connection_thread:
            self._connection_thread.join()
        self.connection_status = ECMConnectionStatus.DISCONNECTED
        self.logger.info("ECM: Disconnected from CCU")

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
        """Route command to the appropriate JFA module/method."""
        # Service control
        if command == "activate":
            return self._activate_service()
        elif command == "deactivate":
            return self._deactivate_service()
        elif command == "status" or command == "get_status":
            return self._get_service_status()
        elif command == "health_check":
            return await self._get_health_status()
        
        # JSON analysis configuration
        elif command == "set_analysis_mode":
            return self._set_analysis_mode(parameters)
        elif command == "configure_template_validation":
            return self._configure_template_validation(parameters)
        elif command == "set_template_limits":
            return self._set_template_limits(parameters)
        elif command == "configure_batch_processing":
            return self._configure_batch_processing(parameters)
        
        # Template validation management
        elif command == "update_validation_rules":
            return await self._update_validation_rules(parameters)
        elif command == "get_validation_rules":
            return self._get_validation_rules()
        elif command == "set_validation_strictness":
            return self._set_validation_strictness(parameters)
        elif command == "enable_custom_validators":
            return self._enable_custom_validators(parameters)
        
        # Binary data configuration
        elif command == "configure_binary_generation":
            return self._configure_binary_generation(parameters)
        elif command == "set_binary_format":
            return self._set_binary_format(parameters)
        elif command == "enable_compression":
            return self._enable_compression(parameters)
        
        # Data analysis pipeline control
        elif command == "enable_analysis_stage":
            return self._enable_analysis_stage(parameters)
        elif command == "disable_analysis_stage":
            return self._disable_analysis_stage(parameters)
        elif command == "get_pipeline_status":
            return self._get_pipeline_status()
        
        # Remote test execution
        elif command == "run_test":
            return await self._run_test(parameters)
        elif command == "test_template_validation":
            return await self._test_template_validation(parameters)
        elif command == "test_binary_generation":
            return await self._test_binary_generation(parameters)
        elif command == "test_data_analysis":
            return await self._test_data_analysis(parameters)
        
        # Reset and maintenance
        elif command == "reset_module":
            return self._reset_module(parameters)
        elif command == "reset_all":
            return self._reset_all()
        elif command == "reload_validation_rules":
            return await self._reload_validation_rules()
        elif command == "clear_analysis_cache":
            return self._clear_analysis_cache()
        
        # Monitoring and data
        elif command == "get_errors":
            return self._get_errors()
        elif command == "get_monitoring":
            return self._get_monitoring()
        elif command == "get_analysis_stats":
            return self._get_analysis_stats()
        elif command == "get_template_stats":
            return self._get_template_stats()
        
        # File processing
        elif command == "process_template_batch":
            return await self._process_template_batch(parameters)
        elif command == "get_processing_status":
            return self._get_processing_status()
        
        # Automatic code generation
        elif command == "auto_code_gen":
            return await self._auto_code_gen()
        else:
            raise ValueError(f"Unknown command: {command}")

    def _activate_service(self):
        """Activate the JFA analysis service."""
        self.jfa_state["analysis_enabled"] = True
        self.jfa_state["template_validation_enabled"] = True
        self.jfa_state["binary_generation_enabled"] = True
        self.logger.info("ECM: JFA analysis service activated")
        return {
            "status": "activated", 
            "capabilities": [
                "template_analysis", 
                "template_validation", 
                "binary_generation", 
                "data_analysis",
                "batch_processing"
            ]
        }

    def _deactivate_service(self):
        """Deactivate the JFA analysis service."""
        self.jfa_state["analysis_enabled"] = False
        self.logger.info("ECM: JFA analysis service deactivated")
        return {"status": "deactivated"}

    def _get_service_status(self):
        """Get comprehensive JFA service status."""
        status = {
            "service": "JFA",
            "version": "1.0.0",
            "connection_status": self.connection_status,
            "jfa_state": self.jfa_state,
            "last_command": self.last_command,
            "last_command_result": self.last_command_result,
            "stats": self.stats.copy(),
            "supported_formats": ["json", "binary", "structured"],
            "analysis_modes": ["template", "binary", "comprehensive"],
            "capabilities": [
                "json_template_analysis",
                "template_validation",
                "binary_data_generation",
                "data_analysis",
                "batch_processing",
                "custom_validation_rules"
            ]
        }
        return status

    async def _get_health_status(self):
        """Get comprehensive health status."""
        try:
            module_health = {}
            all_healthy = True
            
            # Check core modules if available
            for module_name in ["jdpm", "tvm", "bdm", "dam", "ipm", "opm", "msm", "emm"]:
                if module_name in globals():
                    module = globals()[module_name]
                    if hasattr(module, 'health_check'):
                        health = await module.health_check()
                        module_health[module_name] = health
                        if not health.get('healthy', True):
                            all_healthy = False
            
            return {
                "healthy": all_healthy,
                "service": "JFA",
                "analysis_operational": self.jfa_state["analysis_enabled"],
                "template_validation_operational": self.jfa_state["template_validation_enabled"],
                "binary_generation_operational": self.jfa_state["binary_generation_enabled"],
                "processing_modes": self.jfa_state["processing_modes"],
                "modules": module_health,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"healthy": False, "error": str(e), "service": "JFA"}

    def _set_analysis_mode(self, parameters: Dict[str, Any]):
        """Configure JSON analysis mode."""
        mode = parameters.get("mode", "comprehensive")  # template, binary, comprehensive
        enable_deep_analysis = parameters.get("enable_deep_analysis", True)
        enable_pattern_detection = parameters.get("enable_pattern_detection", True)
        
        # Update settings
        self.jfa_state["current_settings"]["default_mode"] = mode
        self.jfa_state["processing_modes"][mode] = True
        
        # Apply to modules if available
        if "dam" in globals() and hasattr(dam, 'set_analysis_mode'):
            dam.set_analysis_mode(mode, enable_deep_analysis)
        
        if "jdpm" in globals() and hasattr(jdpm, 'configure'):
            jdpm.configure(mode=mode, pattern_detection=enable_pattern_detection)
            
        self.logger.info(f"ECM: Analysis mode set to {mode}, deep analysis: {enable_deep_analysis}")
        return {
            "status": "analysis_mode_updated", 
            "mode": mode,
            "deep_analysis": enable_deep_analysis,
            "pattern_detection": enable_pattern_detection
        }

    def _configure_template_validation(self, parameters: Dict[str, Any]):
        """Configure template validation settings."""
        validate_structure = parameters.get("validate_structure", True)
        validate_data_types = parameters.get("validate_data_types", True)
        validate_required_fields = parameters.get("validate_required_fields", True)
        validate_business_rules = parameters.get("validate_business_rules", True)
        
        # Update state
        self.jfa_state["template_validation_enabled"] = validate_structure
        
        # Apply to TVM if available
        if "tvm" in globals() and hasattr(tvm, 'configure_validation'):
            tvm.configure_validation(
                structure=validate_structure,
                data_types=validate_data_types,
                required_fields=validate_required_fields,
                business_rules=validate_business_rules
            )
            
        self.logger.info(f"ECM: Template validation configured - structure:{validate_structure}")
        return {
            "status": "template_validation_configured",
            "settings": {
                "validate_structure": validate_structure,
                "validate_data_types": validate_data_types,
                "validate_required_fields": validate_required_fields,
                "validate_business_rules": validate_business_rules
            }
        }

    def _set_template_limits(self, parameters: Dict[str, Any]):
        """Configure template processing limits."""
        max_template_size = parameters.get("max_template_size", 10485760)  # 10MB
        max_nesting_depth = parameters.get("max_nesting_depth", 20)
        max_array_length = parameters.get("max_array_length", 10000)
        
        # Update limits
        self.jfa_state["current_settings"]["max_template_size"] = max_template_size
        
        # Apply to modules if available
        if "ipm" in globals() and hasattr(ipm, 'set_limits'):
            ipm.set_limits(max_template_size, max_nesting_depth, max_array_length)
            
        self.logger.info(f"ECM: Template limits updated - size:{max_template_size}, depth:{max_nesting_depth}")
        return {
            "status": "template_limits_updated",
            "limits": {
                "max_template_size": max_template_size,
                "max_nesting_depth": max_nesting_depth,
                "max_array_length": max_array_length
            }
        }

    def _configure_batch_processing(self, parameters: Dict[str, Any]):
        """Configure batch processing settings."""
        enable_batch = parameters.get("enable_batch", True)
        batch_size = parameters.get("batch_size", 100)
        concurrent_analyses = parameters.get("concurrent_analyses", 10)
        
        # Update settings
        self.jfa_state["current_settings"]["batch_size"] = batch_size
        
        # Apply to batch processing modules if available
        if "btm" in globals() and hasattr(btm, 'configure_batch_processing'):
            btm.configure_batch_processing(enable_batch, batch_size, concurrent_analyses)
            
        self.logger.info(f"ECM: Batch processing configured - enabled: {enable_batch}, size: {batch_size}")
        return {
            "status": "batch_processing_configured",
            "enabled": enable_batch,
            "batch_size": batch_size,
            "concurrent_analyses": concurrent_analyses
        }

    async def _update_validation_rules(self, parameters: Dict[str, Any]):
        """Update template validation rules."""
        rule_category = parameters.get("category", "general")  # structure, data_type, business, custom
        rules_to_add = parameters.get("rules_to_add", [])
        rules_to_remove = parameters.get("rules_to_remove", [])
        
        try:
            # Apply to TVM if available
            if "tvm" in globals():
                if hasattr(tvm, 'add_validation_rules'):
                    await tvm.add_validation_rules(rule_category, rules_to_add)
                if hasattr(tvm, 'remove_validation_rules'):
                    await tvm.remove_validation_rules(rule_category, rules_to_remove)
            
            self.logger.info(f"ECM: Validation rules updated - {rule_category}: +{len(rules_to_add)}, -{len(rules_to_remove)}")
            return {
                "status": "validation_rules_updated",
                "category": rule_category,
                "rules_added": len(rules_to_add),
                "rules_removed": len(rules_to_remove)
            }
        except Exception as e:
            raise Exception(f"Failed to update validation rules: {e}")

    def _get_validation_rules(self):
        """Get current template validation rules."""
        try:
            rules = {}
            if "tvm" in globals() and hasattr(tvm, 'get_all_rules'):
                rules = tvm.get_all_rules()
            
            return {"status": "validation_rules_retrieved", "rules": rules}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _set_validation_strictness(self, parameters: Dict[str, Any]):
        """Set template validation strictness level."""
        strictness = parameters.get("strictness", "high")  # low, medium, high, strict
        
        # Update setting
        self.jfa_state["current_settings"]["validation_strictness"] = strictness
        
        # Apply to TVM if available
        if "tvm" in globals() and hasattr(tvm, 'set_strictness'):
            tvm.set_strictness(strictness)
            
        self.logger.info(f"ECM: Validation strictness set to {strictness}")
        return {"status": "validation_strictness_updated", "strictness": strictness}

    def _enable_custom_validators(self, parameters: Dict[str, Any]):
        """Enable/disable custom validation rules."""
        enabled = parameters.get("enabled", True)
        custom_validators = parameters.get("validators", [])
        
        # Apply to TVM if available
        if "tvm" in globals() and hasattr(tvm, 'set_custom_validators'):
            tvm.set_custom_validators(enabled, custom_validators)
            
        self.logger.info(f"ECM: Custom validators {'enabled' if enabled else 'disabled'}")
        return {
            "status": "custom_validators_updated", 
            "enabled": enabled, 
            "validators_count": len(custom_validators)
        }

    def _configure_binary_generation(self, parameters: Dict[str, Any]):
        """Configure binary data generation settings."""
        enabled = parameters.get("enabled", True)
        compression = parameters.get("compression", "gzip")
        encoding = parameters.get("encoding", "utf-8")
        checksum_validation = parameters.get("checksum_validation", True)
        
        # Update state
        self.jfa_state["binary_generation_enabled"] = enabled
        
        # Apply to BDM if available
        if "bdm" in globals() and hasattr(bdm, 'configure_generation'):
            bdm.configure_generation(enabled, compression, encoding, checksum_validation)
            
        self.logger.info(f"ECM: Binary generation configured - enabled: {enabled}, compression: {compression}")
        return {
            "status": "binary_generation_configured",
            "enabled": enabled,
            "compression": compression,
            "encoding": encoding,
            "checksum_validation": checksum_validation
        }

    def _set_binary_format(self, parameters: Dict[str, Any]):
        """Set binary file format."""
        format_type = parameters.get("format", "jfa_v1")  # jfa_v1, jfa_v2, custom
        version = parameters.get("version", "1.0")
        
        # Apply to BDM if available
        if "bdm" in globals() and hasattr(bdm, 'set_format'):
            bdm.set_format(format_type, version)
            
        self.logger.info(f"ECM: Binary format set to {format_type} v{version}")
        return {"status": "binary_format_updated", "format": format_type, "version": version}

    def _enable_compression(self, parameters: Dict[str, Any]):
        """Enable/disable binary data compression."""
        enabled = parameters.get("enabled", True)
        compression_level = parameters.get("level", 6)  # 1-9
        algorithm = parameters.get("algorithm", "gzip")
        
        # Apply to BDM if available
        if "bdm" in globals() and hasattr(bdm, 'set_compression'):
            bdm.set_compression(enabled, compression_level, algorithm)
            
        self.logger.info(f"ECM: Compression {'enabled' if enabled else 'disabled'}, level: {compression_level}")
        return {
            "status": "compression_updated", 
            "enabled": enabled, 
            "level": compression_level,
            "algorithm": algorithm
        }

    def _enable_analysis_stage(self, parameters: Dict[str, Any]):
        """Enable a specific analysis pipeline stage."""
        stage = parameters.get("stage")  # input_processing, template_validation, binary_generation, data_analysis
        
        if stage == "template_validation":
            self.jfa_state["template_validation_enabled"] = True
        elif stage == "binary_generation":
            self.jfa_state["binary_generation_enabled"] = True
        elif stage == "data_analysis":
            self.jfa_state["analysis_enabled"] = True
            
        self.logger.info(f"ECM: Analysis stage '{stage}' enabled")
        return {"status": "analysis_stage_enabled", "stage": stage}

    def _disable_analysis_stage(self, parameters: Dict[str, Any]):
        """Disable a specific analysis pipeline stage."""
        stage = parameters.get("stage")
        
        if stage == "template_validation":
            self.jfa_state["template_validation_enabled"] = False
        elif stage == "binary_generation":
            self.jfa_state["binary_generation_enabled"] = False
        elif stage == "data_analysis":
            self.jfa_state["analysis_enabled"] = False
            
        self.logger.info(f"ECM: Analysis stage '{stage}' disabled")
        return {"status": "analysis_stage_disabled", "stage": stage}

    def _get_pipeline_status(self):
        """Get analysis pipeline status."""
        pipeline_status = {
            "input_processing": True,  # Always enabled
            "template_validation": self.jfa_state["template_validation_enabled"],
            "binary_generation": self.jfa_state["binary_generation_enabled"],
            "data_analysis": self.jfa_state["analysis_enabled"],
            "output_processing": True  # Always enabled
        }
        
        return {"status": "pipeline_status_retrieved", "pipeline": pipeline_status}

    async def _run_test(self, parameters: Dict[str, Any]):
        """Run a test via TMM."""
        test_code = parameters.get("test_code")
        if "tmm" in globals() and hasattr(tmm, 'run_test'):
            result = await tmm.run_test(test_code)
        else:
            raise ValueError("TMM module not available")
        
        self.logger.info(f"ECM: Test {test_code} executed")
        return {"status": "test_executed", "test_code": test_code, "result": result}

    async def _test_template_validation(self, parameters: Dict[str, Any]):
        """Test template validation with sample template."""
        test_template = parameters.get("template", {"test": "data", "version": "1.0"})
        validation_rules = parameters.get("validation_rules", {})
        
        try:
            result = {"template": test_template, "rules": validation_rules}
            
            # Test through validation pipeline if available
            if "tvm" in globals() and hasattr(tvm, 'validate_template'):
                validation_result = await tvm.validate_template(test_template, validation_rules)
                result["validation_result"] = validation_result
            
            self.logger.info("ECM: Template validation test executed")
            return {"status": "template_validation_test_executed", "result": result}
        except Exception as e:
            return {"status": "template_validation_test_failed", "error": str(e)}

    async def _test_binary_generation(self, parameters: Dict[str, Any]):
        """Test binary generation functionality."""
        test_data = parameters.get("data", {"test": "binary", "format": "jfa_v1"})
        
        try:
            if "bdm" in globals() and hasattr(bdm, 'generate_binary_data'):
                result = await bdm.generate_binary_data(test_data)
            else:
                result = {"binary_size": len(str(test_data)), "format": "mock"}
            
            self.logger.info("ECM: Binary generation test executed")
            return {"status": "binary_generation_test_executed", "result": result}
        except Exception as e:
            return {"status": "binary_generation_test_failed", "error": str(e)}

    async def _test_data_analysis(self, parameters: Dict[str, Any]):
        """Test data analysis functionality."""
        test_data = parameters.get("data", {"analysis": "test", "complexity": "medium"})
        analysis_type = parameters.get("analysis_type", "comprehensive")
        
        try:
            results = []
            
            if "dam" in globals() and hasattr(dam, 'analyze_data'):
                analysis_result = await dam.analyze_data(test_data, analysis_type)
                results.append({"analysis": "data_analysis", "result": analysis_result})
            
            self.logger.info("ECM: Data analysis test executed")
            return {"status": "data_analysis_test_executed", "results": results}
        except Exception as e:
            return {"status": "data_analysis_test_failed", "error": str(e)}

    def _reset_module(self, parameters: Dict[str, Any]):
        """Reset a specific JFA module."""
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
        """Reset the entire JFA service."""
        # Reset JFA state
        self.jfa_state = {
            "analysis_enabled": True,
            "template_validation_enabled": True,
            "binary_generation_enabled": True,
            "processing_modes": {"template": True, "binary": True, "comprehensive": True},
            "current_settings": {
                "default_mode": "comprehensive",
                "max_template_size": 10485760,
                "validation_strictness": "high",
                "batch_size": 100
            },
            "analysis_stats": {
                "templates_validated": 0, "binary_files_generated": 0, 
                "analyses_completed": 0, "validation_success_rate": 0.0
            }
        }
        
        self.logger.info("ECM: All JFA modules reset")
        return {"status": "all_reset"}

    async def _reload_validation_rules(self):
        """Reload template validation rules from storage."""
        try:
            if "tvm" in globals() and hasattr(tvm, 'reload_rules'):
                result = await tvm.reload_rules()
                
                self.logger.info("ECM: Validation rules reloaded")
                return {"status": "validation_rules_reloaded", "result": result}
            else:
                raise Exception("TVM module not available")
        except Exception as e:
            raise Exception(f"Failed to reload validation rules: {e}")

    def _clear_analysis_cache(self):
        """Clear analysis and processing cache."""
        try:
            # Clear caches in various modules if available
            if "jdpm" in globals() and hasattr(jdpm, 'clear_cache'):
                jdpm.clear_cache()
            if "dam" in globals() and hasattr(dam, 'clear_cache'):
                dam.clear_cache()
            if "tvm" in globals() and hasattr(tvm, 'clear_cache'):
                tvm.clear_cache()
                
            self.logger.info("ECM: Analysis cache cleared")
            return {"status": "analysis_cache_cleared"}
        except Exception as e:
            return {"status": "cache_clear_error", "error": str(e)}

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

    def _get_analysis_stats(self):
        """Get JSON analysis statistics."""
        stats = {
            "jfa_state": self.jfa_state,
            "command_stats": self.stats,
            "service_status": {
                "analysis_enabled": self.jfa_state["analysis_enabled"],
                "template_validation_enabled": self.jfa_state["template_validation_enabled"],
                "binary_generation_enabled": self.jfa_state["binary_generation_enabled"],
                "processing_modes": self.jfa_state["processing_modes"]
            }
        }
        
        # Add module-specific stats if available
        if "jdpm" in globals() and hasattr(jdpm, 'stats'):
            stats["json_processing"] = jdpm.stats
        if "tvm" in globals() and hasattr(tvm, 'stats'):
            stats["template_validation"] = tvm.stats
        if "bdm" in globals() and hasattr(bdm, 'stats'):
            stats["binary_generation"] = bdm.stats
        if "dam" in globals() and hasattr(dam, 'stats'):
            stats["data_analysis"] = dam.stats
            
        return {"status": "analysis_stats_retrieved", "stats": stats}

    def _get_template_stats(self):
        """Get template processing statistics."""
        if "tvm" in globals() and hasattr(tvm, 'get_template_stats'):
            template_stats = tvm.get_template_stats()
        else:
            template_stats = {"message": "Template processing stats not available"}
            
        return {"status": "template_stats_retrieved", "stats": template_stats}

    async def _process_template_batch(self, parameters: Dict[str, Any]):
        """Process a batch of templates."""
        templates = parameters.get("templates", [])
        output_directory = parameters.get("output_directory")
        
        try:
            results = []
            for i, template in enumerate(templates):
                if "jdpm" in globals() and hasattr(jdpm, 'process_json_data'):
                    result = await jdpm.process_json_data(template)
                    results.append({"template_index": i, "result": result})
                else:
                    results.append({"template_index": i, "error": "JDPM module not available"})
            
            self.logger.info(f"ECM: Processed batch of {len(templates)} templates")
            return {"status": "template_batch_processed", "results": results}
        except Exception as e:
            return {"status": "template_batch_processing_failed", "error": str(e)}

    def _get_processing_status(self):
        """Get template processing status."""
        if "jdpm" in globals() and hasattr(jdpm, 'get_processing_status'):
            status = jdpm.get_processing_status()
        else:
            status = {"message": "Template processing status not available"}
            
        return {"status": "processing_status_retrieved", "processing_status": status}

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

    async def invalid_data_recognition(self, template_data: Dict[str, Any], validation_errors: List[str], request_id: str) -> Dict[str, Any]:
        """
        Analyze validation failures and identify which parts of the data template are invalid.
        
        Args:
            template_data: The template data that failed validation
            validation_errors: List of validation error messages
            request_id: Request identifier for tracking
            
        Returns:
            Dictionary containing invalid data analysis
        """
        try:
            invalid_parts = []
            error_categories = {
                "structure_errors": [],
                "type_errors": [],
                "format_errors": [],
                "business_rule_errors": [],
                "field_errors": []
            }
            
            # Analyze validation errors and categorize them
            for error in validation_errors:
                error_lower = error.lower()
                
                # Structure errors
                if any(keyword in error_lower for keyword in ["missing", "required", "structure", "field"]):
                    if "choices" in error_lower:
                        error_categories["structure_errors"].append("choices object structure")
                    elif "message" in error_lower:
                        error_categories["structure_errors"].append("message object structure")
                    elif "usage" in error_lower:
                        error_categories["structure_errors"].append("usage object structure")
                    else:
                        error_categories["structure_errors"].append("template structure")
                
                # Type errors
                elif any(keyword in error_lower for keyword in ["must be", "type", "string", "number", "object"]):
                    if "id" in error_lower:
                        error_categories["type_errors"].append("id field type")
                    elif "created" in error_lower:
                        error_categories["type_errors"].append("created field type")
                    elif "model" in error_lower:
                        error_categories["type_errors"].append("model field type")
                    else:
                        error_categories["type_errors"].append("field data type")
                
                # Format errors
                elif any(keyword in error_lower for keyword in ["format", "encoding", "character"]):
                    error_categories["format_errors"].append("data format")
                
                # Business rule errors
                elif any(keyword in error_lower for keyword in ["business", "rule", "validation", "jfa"]):
                    if "flag" in error_lower:
                        error_categories["business_rule_errors"].append("JFA flag validation")
                    elif "loca" in error_lower:
                        error_categories["business_rule_errors"].append("location data validation")
                    elif "cust" in error_lower:
                        error_categories["business_rule_errors"].append("customer data validation")
                    elif "sinf" in error_lower:
                        error_categories["business_rule_errors"].append("system information validation")
                    else:
                        error_categories["business_rule_errors"].append("business rule validation")
                
                # Field-specific errors
                else:
                    error_categories["field_errors"].append(error)
            
            # Build invalid parts list
            for category, errors in error_categories.items():
                if errors:
                    invalid_parts.extend(errors)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_invalid_parts = []
            for part in invalid_parts:
                if part not in seen:
                    seen.add(part)
                    unique_invalid_parts.append(part)
            
            result = {
                "request_id": request_id,
                "recognition_type": "invalid_data",
                "invalid_parts": unique_invalid_parts,
                "error_categories": error_categories,
                "total_invalid_parts": len(unique_invalid_parts),
                "template_analysis": {
                    "has_id": "id" in template_data,
                    "has_object": "object" in template_data,
                    "has_created": "created" in template_data,
                    "has_model": "model" in template_data,
                    "has_choices": "choices" in template_data,
                    "has_usage": "usage" in template_data,
                    "has_jfa_fields": any(field in template_data for field in ["flag", "loca", "cust", "sinf"])
                },
                "timestamp": datetime.now().isoformat(),
                "service": "JFA"
            }
            
            self.logger.info(f"ECM: Invalid data recognition completed for request {request_id}: {len(unique_invalid_parts)} invalid parts identified")
            return result
            
        except Exception as e:
            error_msg = f"Error in invalid data recognition for request {request_id}: {e}"
            self.logger.error(error_msg)
            self.error_manager.log_error_with_generation("ECM", "ExternalControlModule", "invalid_data_recognition", error_msg)
            return {
                "request_id": request_id,
                "recognition_type": "invalid_data",
                "error": str(e),
                "invalid_parts": [],
                "timestamp": datetime.now().isoformat(),
                "service": "JFA"
            }

    async def insufficient_data_recognition(self, template_data: Dict[str, Any], validation_errors: List[str], request_id: str) -> Dict[str, Any]:
        """
        Analyze validation failures and identify which data is missing or insufficient.
        
        Args:
            template_data: The template data that failed validation
            validation_errors: List of validation error messages
            request_id: Request identifier for tracking
            
        Returns:
            Dictionary containing missing/insufficient data analysis
        """
        try:
            missing_data = []
            insufficient_data = []
            
            # Define required data categories
            required_categories = {
                "basic_fields": ["id", "object", "created", "model", "choices", "usage"],
                "jfa_specific": ["flag", "loca", "cust", "sinf"],
                "choices_structure": ["message", "role", "content"],
                "usage_structure": ["prompt_tokens", "completion_tokens", "total_tokens"],
                "location_data": ["province", "city", "coordinates", "climate_zone"],
                "customer_data": ["customer_id", "customer_type", "energy_requirements"],
                "system_data": ["calculation_type", "system_size", "efficiency_parameters"]
            }
            
            # Check for missing basic fields
            for field in required_categories["basic_fields"]:
                if field not in template_data:
                    missing_data.append(f"Required field: {field}")
            
            # Check for missing JFA-specific fields
            jfa_fields_present = []
            for field in required_categories["jfa_specific"]:
                if field in template_data:
                    jfa_fields_present.append(field)
                else:
                    missing_data.append(f"JFA field: {field}")
            
            # Check choices structure
            if "choices" in template_data:
                choices = template_data["choices"]
                if not isinstance(choices, dict):
                    missing_data.append("choices object structure")
                else:
                    for field in required_categories["choices_structure"]:
                        if field not in choices:
                            missing_data.append(f"choices.{field}")
            else:
                missing_data.append("choices object")
            
            # Check usage structure
            if "usage" in template_data:
                usage = template_data["usage"]
                if not isinstance(usage, dict):
                    missing_data.append("usage object structure")
                else:
                    for field in required_categories["usage_structure"]:
                        if field not in usage:
                            insufficient_data.append(f"usage.{field}")
            else:
                missing_data.append("usage object")
            
            # Check for location data (if JFA processing requires it)
            if "loca" in template_data:
                location_data = template_data["loca"]
                if isinstance(location_data, dict):
                    for field in required_categories["location_data"]:
                        if field not in location_data:
                            insufficient_data.append(f"location.{field}")
                else:
                    insufficient_data.append("location data structure")
            else:
                missing_data.append("location data (loca)")
            
            # Check for customer data
            if "cust" in template_data:
                customer_data = template_data["cust"]
                if isinstance(customer_data, dict):
                    for field in required_categories["customer_data"]:
                        if field not in customer_data:
                            insufficient_data.append(f"customer.{field}")
                else:
                    insufficient_data.append("customer data structure")
            else:
                missing_data.append("customer data (cust)")
            
            # Check for system information
            if "sinf" in template_data:
                system_data = template_data["sinf"]
                if isinstance(system_data, dict):
                    for field in required_categories["system_data"]:
                        if field not in system_data:
                            insufficient_data.append(f"system.{field}")
                else:
                    insufficient_data.append("system information structure")
            else:
                missing_data.append("system information (sinf)")
            
            # Analyze validation errors for additional missing data
            for error in validation_errors:
                error_lower = error.lower()
                if "missing" in error_lower:
                    if "location" in error_lower:
                        missing_data.append("location information")
                    elif "customer" in error_lower:
                        missing_data.append("customer information")
                    elif "system" in error_lower:
                        missing_data.append("system configuration")
                    elif "energy" in error_lower:
                        missing_data.append("energy requirements")
                    elif "climate" in error_lower:
                        missing_data.append("climate data")
                    elif "coordinates" in error_lower:
                        missing_data.append("geographic coordinates")
                    else:
                        missing_data.append("required data field")
            
            # Remove duplicates while preserving order
            seen = set()
            unique_missing_data = []
            for item in missing_data:
                if item not in seen:
                    seen.add(item)
                    unique_missing_data.append(item)
            
            seen = set()
            unique_insufficient_data = []
            for item in insufficient_data:
                if item not in seen:
                    seen.add(item)
                    unique_insufficient_data.append(item)
            
            result = {
                "request_id": request_id,
                "recognition_type": "insufficient_data",
                "missing_data": unique_missing_data,
                "insufficient_data": unique_insufficient_data,
                "total_missing": len(unique_missing_data),
                "total_insufficient": len(unique_insufficient_data),
                "data_completeness": {
                    "basic_fields_complete": all(field in template_data for field in required_categories["basic_fields"]),
                    "jfa_fields_present": jfa_fields_present,
                    "has_location_data": "loca" in template_data,
                    "has_customer_data": "cust" in template_data,
                    "has_system_data": "sinf" in template_data,
                    "choices_structure_complete": "choices" in template_data and isinstance(template_data["choices"], dict),
                    "usage_structure_complete": "usage" in template_data and isinstance(template_data["usage"], dict)
                },
                "timestamp": datetime.now().isoformat(),
                "service": "JFA"
            }
            
            self.logger.info(f"ECM: Insufficient data recognition completed for request {request_id}: {len(unique_missing_data)} missing, {len(unique_insufficient_data)} insufficient")
            return result
            
        except Exception as e:
            error_msg = f"Error in insufficient data recognition for request {request_id}: {e}"
            self.logger.error(error_msg)
            self.error_manager.log_error_with_generation("ECM", "ExternalControlModule", "insufficient_data_recognition", error_msg)
            return {
                "request_id": request_id,
                "recognition_type": "insufficient_data",
                "error": str(e),
                "missing_data": [],
                "insufficient_data": [],
                "timestamp": datetime.now().isoformat(),
                "service": "JFA"
            }

    def stream_logs(self, callback: Callable[[str], None], level: str = "INFO"):
        """Stream logs to CCU."""
        self.logger.info(f"ECM: Streaming logs at level {level}")
        callback(f"[ECM] Log streaming started at level {level} for JFA JSON Analysis")

    def stream_monitoring(self, callback: Callable[[Dict[str, Any]], None]):
        """Stream monitoring data to CCU."""
        self.logger.info("ECM: Streaming monitoring data")
        callback({"status": "monitoring_stream_started", "service": "JFA"})

    def get_module_status(self) -> Dict[str, Any]:
        """Get ECM module status."""
        return {
            "module": "ECM",
            "service": "JFA",
            "status": self.connection_status,
            "jfa_state": self.jfa_state,
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
        await self._start_connection()
        
        # Start WebSocket client connection to CCU
        await self.start_websocket_client()
        
        self.logger.info("ECM started successfully")
    async def start_websocket_client(self):
        """Start WebSocket client connection to CCU."""
        try:
            self.logger.info("Starting WebSocket client connection to CCU...")
            
            # Start WebSocket connection task
            self.websocket_task = asyncio.create_task(self._websocket_connection_loop())
            
            # Start heartbeat task
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
                
                # If connection succeeded, reset retry count
                self.connection_retry_count = 0
                
                # Listen for messages
                await self._listen_for_messages()
                
            except Exception as e:
                self.logger.error(f"WebSocket connection error: {e}")
                
                # Clean up connection
                if self.websocket_connection:
                    try:
                        await self.websocket_connection.close()
                    except:
                        pass
                    self.websocket_connection = None
                
                # Retry logic
                self.connection_retry_count += 1
                if self.connection_retry_count <= self.max_retry_attempts:
                    self.logger.info(f"Retrying connection in {self.retry_delay} seconds (attempt {self.connection_retry_count}/{self.max_retry_attempts})")
                    await asyncio.sleep(self.retry_delay)
                else:
                    self.logger.error("Max retry attempts reached, stopping WebSocket client")
                    break
    
    async def _connect_to_ccu(self):
        """Connect to CCU WebSocket server with fallback ports."""
        # Try primary port first
        try:
            self.logger.info(f"Connecting to CCU at {self.ccu_websocket_uri}")
            self.websocket_connection = await asyncio.wait_for(
                websockets.connect(self.ccu_websocket_uri),
                timeout=self.connection_timeout
            )
            self.logger.info("✅ Connected to CCU WebSocket server")
            return
            
        except Exception as e:
            self.logger.warning(f"Failed to connect to primary port: {e}")
        
        # Try fallback ports
        for fallback_port in self.fallback_ports:
            try:
                fallback_uri = f"ws://localhost:{fallback_port}/ws"
                self.logger.info(f"Trying fallback port: {fallback_uri}")
                
                self.websocket_connection = await asyncio.wait_for(
                    websockets.connect(fallback_uri),
                    timeout=self.connection_timeout
                )
                
                self.logger.info(f"✅ Connected to CCU WebSocket server on fallback port {fallback_port}")
                self.ccu_websocket_uri = fallback_uri  # Update for future connections
                return
                
            except Exception as e:
                self.logger.warning(f"Failed to connect to fallback port {fallback_port}: {e}")
        
        # If all attempts failed
        raise Exception("Failed to connect to CCU on primary and all fallback ports")
    
    async def _listen_for_messages(self):
        """Listen for messages from CCU."""
        if not self.websocket_connection:
            return
        
        try:
            async for message in self.websocket_connection:
                await self._handle_ccu_message(message)
        except websockets.exceptions.ConnectionClosed:
            self.logger.warning("WebSocket connection closed by CCU")
        except Exception as e:
            self.logger.error(f"Error receiving message from CCU: {e}")
            raise
    
    async def _handle_ccu_message(self, message: str):
        """Handle message received from CCU."""
        try:
            data = json.loads(message)
            message_type = data.get("type", "unknown")
            
            self.logger.debug(f"Received message from CCU: {message_type}")
            
            if message_type == "welcome":
                self.logger.info(f"Received welcome from CCU: {data.get('message', 'Connected')}")
            elif message_type == "activate":
                await self._handle_activation_command(data)
            elif message_type == "command":
                await self._handle_ccu_command(data)
            elif message_type == "ping":
                await self._send_pong()
            else:
                self.logger.warning(f"Unknown message type from CCU: {message_type}")
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON from CCU: {e}")
        except Exception as e:
            self.logger.error(f"Error handling CCU message: {e}")
    
    async def _handle_activation_command(self, data):
        """Handle activation command from CCU."""
        try:
            self.logger.info("Received activation command from CCU")
            
            # Send acknowledgment
            await self._send_to_ccu({
                "type": "activation_ack",
                "status": "activated",
                "timestamp": datetime.now().isoformat(),
                "service": "JFA"
            })
            
        except Exception as e:
            self.logger.error(f"Error handling activation command: {e}")
    
    async def _handle_ccu_command(self, data):
        """Handle general command from CCU."""
        try:
            command = data.get("command", "unknown")
            self.logger.info(f"Received command from CCU: {command}")
            
            # Process command and send response
            response = {
                "type": "command_response",
                "command": command,
                "status": "processed", 
                "timestamp": datetime.now().isoformat(),
                "service": "JFA"
            }
            
            await self._send_to_ccu(response)
            
        except Exception as e:
            self.logger.error(f"Error handling CCU command: {e}")
    
    async def _send_to_ccu(self, data: dict):
        """Send message to CCU."""
        if not self.websocket_connection:
            self.logger.warning("No WebSocket connection to CCU - cannot send message")
            return False
        
        try:
            message = json.dumps(data)
            await self.websocket_connection.send(message)
            self.logger.debug(f"Sent message to CCU: {data.get('type', 'unknown')}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending message to CCU: {e}")
            return False
    
    async def _send_pong(self):
        """Send pong response to CCU ping."""
        await self._send_to_ccu({
            "type": "pong",
            "timestamp": datetime.now().isoformat(),
            "service": "JFA"
        })
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeat to CCU."""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                if self.websocket_connection:
                    await self._send_to_ccu({
                        "type": "heartbeat",
                        "timestamp": datetime.now().isoformat(),
                        "service": "JFA",
                        "status": "active"
                    })
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in heartbeat loop: {e}")
    
    async def stop_websocket_client(self):
        """Stop WebSocket client connection."""
        try:
            # Cancel tasks
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
                try:
                    await self.heartbeat_task
                except asyncio.CancelledError:
                    pass
            
            if self.websocket_task:
                self.websocket_task.cancel()
                try:
                    await self.websocket_task
                except asyncio.CancelledError:
                    pass
            
            # Close connection
            if self.websocket_connection:
                await self.websocket_connection.close()
                self.websocket_connection = None
            
            self.logger.info("✅ WebSocket client stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping WebSocket client: {e}")



    async def stop(self):
        """Stop the ECM module."""
        self.is_active = False
        self._stop_event.set()
        if self._websocket:
            await self._websocket.close()
                    # Stop WebSocket client connection
            await self.stop_websocket_client()
            
            self.logger.info("ECM stopped successfully")

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        return {
            "healthy": self.connection_status == ECMConnectionStatus.CONNECTED,
            "module": "ECM",
            "service": "JFA",
            "connection_status": self.connection_status,
            "analysis_operational": self.jfa_state["analysis_enabled"],
            "template_validation_operational": self.jfa_state["template_validation_enabled"],
            "binary_generation_operational": self.jfa_state["binary_generation_enabled"],
            "timestamp": datetime.now().isoformat()
        }

    async def start(self):
        """Start the ECM module."""
        self.is_active = True
        await self.start_websocket_client()
        self.logger.info("✅ JFA ECM started successfully")

    async def stop(self):
        """Stop the ECM module."""
        self.is_active = False
        await self.stop_websocket_client()
        self.logger.info("🔌 JFA ECM stopped successfully")

# Global instances
ecm = ExternalControlModule()
ECM = ExternalControlModule() 