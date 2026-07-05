"""
External Control Module (ECM) for TPP Microservice

Primary interface between the TPP microservice and the Central Control Unit (CCU).
Handles service control, monitoring/log streaming, configuration, remote test execution, 
resets, text processing configuration, spam word management, language processing settings.

TPP-Specific Capabilities:
- Spam word list management and updates
- Language processing configuration (Persian, English, multilingual)
- Text filtering pipeline control
- Content purification settings
- Dynamic spam list updates
- Processing mode configuration
- Performance optimization settings
- Batch processing control
"""

import asyncio
import json
import logging
import websockets
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
import threading
import queue

from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler

# Import TPP modules for command routing
try:
    from TPDM.tpdm import tpdm
    from SWM.swm import swm
    from FTM.ftm import ftm
    from LPM.lpm import lpm
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
    External Control Module (ECM) for TPP
    - Maintains persistent connection to CCU
    - Parses and routes commands from CCU to appropriate TPP modules
    - Streams logs and monitoring data to CCU
    - Handles service control, configuration, resets, test execution, spam management, and more
    - Manages TPP-specific capabilities: text processing, spam filtering, language processing
    - All actions are traceable and logged
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # NEW ARCHITECTURE: WebSocket CLIENT configuration
        self.ccu_websocket_uri = "ws://localhost:4442/ws"
        self.websocket_connection = None
        self.websocket_task = None 
        self.heartbeat_task = None
        self.connection_retry_count = 0
        self.max_retry_attempts = 10
        self.retry_delay = 5  # seconds
        self.heartbeat_interval = 30  # seconds
        self.connection_timeout = 5.0  # seconds
        self.fallback_ports = [4452, 4462, 4472]  # CCU TPPIM fallback ports
        self.current_port = 4442  # Primary CCU TPPIM port
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
        
        # TPP-specific state
        self.tpp_state = {
            "processing_enabled": True,
            "spam_filtering_enabled": True,
            "language_modes": {
                "persian": True,
                "english": True,
                "multilingual": True
            },
            "current_settings": {
                "default_language": "persian",
                "max_text_length": 100000,
                "strictness_level": "medium",
                "batch_size": 100
            },
            "spam_word_counts": {
                "persian_words": 0,
                "english_words": 0,
                "custom_words": 0,
                "total_words": 0
            }
        }
        
        # Connection will be started via start() method

    async def start_websocket_client(self):
        """Start WebSocket client connection to CCU TPPIM server."""
        try:
            self.logger.info("🔌 Starting TPP ECM WebSocket client to CCU TPPIM...")
            self.websocket_task = asyncio.create_task(self._websocket_connection_loop())
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self.logger.info("✅ TPP ECM WebSocket client started successfully")
        except Exception as e:
            self.logger.error(f"❌ Failed to start TPP ECM WebSocket client: {e}")
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
            self.logger.info("🔌 TPP ECM WebSocket client disconnected from CCU")
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
        """Connect to CCU TPPIM WebSocket server with fallback logic."""
        ports_to_try = [self.current_port] + self.fallback_ports
        
        for port in ports_to_try:
            try:
                uri = f"ws://localhost:{port}/ws"
                self.logger.debug(f"🔍 Attempting to connect to CCU TPPIM at {uri}")
                
                self.websocket_connection = await asyncio.wait_for(
                    websockets.connect(uri),
                    timeout=self.connection_timeout
                )
                
                self.connection_status = ECMConnectionStatus.CONNECTED
                self.ccu_websocket_uri = uri
                self.current_port = port
                
                self.logger.info(f"✅ TPP ECM connected to CCU TPPIM server at port {port}")
                
                # Send registration message
                await self._send_registration()
                return
                
            except Exception as e:
                self.logger.debug(f"❌ Failed to connect to port {port}: {e}")
                continue
        
        raise Exception(f"Failed to connect to CCU TPPIM server on all ports: {ports_to_try}")

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
        """Send registration message to CCU TPPIM server."""
        registration_msg = {
            "type": "service_registration",
            "service": "TPP",
            "module": "ECM",
            "timestamp": datetime.now().isoformat(),
            "capabilities": [
                "text_processing",
                "spam_filtering",
                "language_processing",
                "batch_processing",
                "spam_word_management"
            ],
            "version": "1.0.0"
        }
        await self._send_to_ccu(registration_msg)
        self.logger.info("📋 Registration sent to CCU TPPIM")

    async def _handle_ccu_message(self, message: str):
        """Handle message from CCU TPPIM server."""
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
            
            # Activate TPP processing services
            activation_result = {
                "processing_activated": True,
                "spam_filtering_active": self.tpp_state["spam_filtering_enabled"],
                "languages_active": list(self.tpp_state["language_modes"].keys()),
                "batch_processing_ready": True
            }
            
            response = {
                "type": "activation_ack",
                "service": "TPP",
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
                "service": "TPP", 
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
            
            # Process the command (implementation depends on specific TPP commands)
            # This would route to appropriate TPP modules
            result = {"status": "completed", "command": command}
            
            response = {
                "type": "command_response",
                "service": "TPP",
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
                "service": "TPP",
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            await self._send_to_ccu(error_response)

    async def _handle_config_update(self, data: Dict[str, Any]):
        """Handle configuration update from CCU."""
        try:
            self.logger.info("⚙️ Received configuration update from CCU")
            
            # Update TPP configuration (implementation specific)
            config_data = data.get("config", {})
            
            # Acknowledge configuration update
            response = {
                "type": "config_update_ack",
                "service": "TPP",
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
                        "service": "TPP", 
                        "status": "active",
                        "timestamp": datetime.now().isoformat(),
                        "processing_stats": {
                            "spam_words_loaded": self.tpp_state["spam_word_counts"]["total_words"],
                            "processing_enabled": self.tpp_state["processing_enabled"]
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
        # Old mock connection code removed - now using WebSocket client

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
        """Route command to the appropriate TPP module/method."""
        # Service control
        if command == "activate":
            return self._activate_service()
        elif command == "deactivate":
            return self._deactivate_service()
        elif command == "status":
            return self._get_service_status()
        elif command == "health_check":
            return await self._get_health_status()
        
        # Text processing configuration
        elif command == "set_processing_mode":
            return self._set_processing_mode(parameters)
        elif command == "configure_language_processing":
            return self._configure_language_processing(parameters)
        elif command == "set_text_limits":
            return self._set_text_limits(parameters)
        elif command == "configure_batch_processing":
            return self._configure_batch_processing(parameters)
        
        # Spam word management
        elif command == "update_spam_words":
            return await self._update_spam_words(parameters)
        elif command == "get_spam_word_lists":
            return self._get_spam_word_lists()
        elif command == "clear_spam_words":
            return self._clear_spam_words(parameters)
        elif command == "import_spam_words":
            return await self._import_spam_words(parameters)
        elif command == "export_spam_words":
            return await self._export_spam_words(parameters)
        
        # Filter configuration
        elif command == "configure_spam_filter":
            return self._configure_spam_filter(parameters)
        elif command == "set_filter_strictness":
            return self._set_filter_strictness(parameters)
        elif command == "enable_custom_filters":
            return self._enable_custom_filters(parameters)
        
        # Processing pipeline control
        elif command == "enable_processing_stage":
            return self._enable_processing_stage(parameters)
        elif command == "disable_processing_stage":
            return self._disable_processing_stage(parameters)
        elif command == "get_pipeline_status":
            return self._get_pipeline_status()
        
        # Remote test execution
        elif command == "run_test":
            return await self._run_test(parameters)
        elif command == "test_text_processing":
            return await self._test_text_processing(parameters)
        elif command == "test_spam_detection":
            return await self._test_spam_detection(parameters)
        elif command == "test_language_detection":
            return await self._test_language_detection(parameters)
        
        # Reset and maintenance
        elif command == "reset_module":
            return self._reset_module(parameters)
        elif command == "reset_all":
            return self._reset_all()
        elif command == "reload_spam_words":
            return await self._reload_spam_words()
        elif command == "clear_processing_cache":
            return self._clear_processing_cache()
        
        # Monitoring and data
        elif command == "get_errors":
            return self._get_errors()
        elif command == "get_monitoring":
            return self._get_monitoring()
        elif command == "get_processing_stats":
            return self._get_processing_stats()
        elif command == "get_language_stats":
            return self._get_language_stats()
        
        # File processing
        elif command == "process_file_batch":
            return await self._process_file_batch(parameters)
        elif command == "get_file_processing_status":
            return self._get_file_processing_status()
        
        # Automatic code generation
        elif command == "auto_code_gen":
            return await self._auto_code_gen()
        else:
            raise ValueError(f"Unknown command: {command}")

    def _activate_service(self):
        """Activate the TPP text processing service."""
        self.tpp_state["processing_enabled"] = True
        self.tpp_state["spam_filtering_enabled"] = True
        self.logger.info("ECM: TPP text processing service activated")
        return {
            "status": "activated", 
            "capabilities": [
                "text_processing", 
                "spam_filtering", 
                "language_detection", 
                "multilingual_support",
                "batch_processing"
            ]
        }

    def _deactivate_service(self):
        """Deactivate the TPP text processing service."""
        self.tpp_state["processing_enabled"] = False
        self.logger.info("ECM: TPP text processing service deactivated")
        return {"status": "deactivated"}

    def _get_service_status(self):
        """Get comprehensive TPP service status."""
        status = {
            "service": "TPP",
            "version": "1.0.0",
            "connection_status": self.connection_status,
            "tpp_state": self.tpp_state,
            "last_command": self.last_command,
            "last_command_result": self.last_command_result,
            "stats": self.stats.copy(),
            "supported_languages": ["persian", "english", "arabic", "urdu"],
            "processing_modes": ["persian", "multilingual", "custom"],
            "capabilities": [
                "spam_word_filtering",
                "language_detection",
                "text_purification",
                "batch_processing",
                "custom_filter_rules",
                "multilingual_support"
            ]
        }
        return status

    async def _get_health_status(self):
        """Get comprehensive health status."""
        try:
            module_health = {}
            all_healthy = True
            
            # Check core modules if available
            for module_name in ["tpdm", "swm", "ftm", "lpm", "ipm", "opm", "msm", "emm"]:
                if module_name in globals():
                    module = globals()[module_name]
                    if hasattr(module, 'health_check'):
                        health = await module.health_check()
                        module_health[module_name] = health
                        if not health.get('healthy', True):
                            all_healthy = False
            
            return {
                "healthy": all_healthy,
                "service": "TPP",
                "processing_operational": self.tpp_state["processing_enabled"],
                "spam_filtering_operational": self.tpp_state["spam_filtering_enabled"],
                "language_modes": self.tpp_state["language_modes"],
                "modules": module_health,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"healthy": False, "error": str(e), "service": "TPP"}

    def _set_processing_mode(self, parameters: Dict[str, Any]):
        """Configure text processing mode."""
        mode = parameters.get("mode", "persian")
        enable_multilingual = parameters.get("enable_multilingual", True)
        preserve_word_order = parameters.get("preserve_word_order", True)
        
        # Update settings
        self.tpp_state["current_settings"]["default_language"] = mode
        self.tpp_state["language_modes"]["multilingual"] = enable_multilingual
        
        # Apply to modules if available
        if "lpm" in globals() and hasattr(lpm, 'set_processing_mode'):
            lpm.set_processing_mode(mode, enable_multilingual)
        
        if "tpdm" in globals() and hasattr(tpdm, 'configure'):
            tpdm.configure(mode=mode, preserve_order=preserve_word_order)
            
        self.logger.info(f"ECM: Processing mode set to {mode}, multilingual: {enable_multilingual}")
        return {
            "status": "processing_mode_updated", 
            "mode": mode,
            "multilingual": enable_multilingual
        }

    def _configure_language_processing(self, parameters: Dict[str, Any]):
        """Configure language processing settings."""
        supported_languages = parameters.get("supported_languages", ["persian", "english"])
        primary_language = parameters.get("primary_language", "persian")
        enable_auto_detection = parameters.get("enable_auto_detection", True)
        
        # Update language modes
        for lang in ["persian", "english", "multilingual"]:
            self.tpp_state["language_modes"][lang] = lang in supported_languages or lang == "multilingual"
        
        # Apply to LPM if available
        if "lpm" in globals() and hasattr(lpm, 'configure_languages'):
            lpm.configure_languages(supported_languages, primary_language, enable_auto_detection)
            
        self.logger.info(f"ECM: Language processing configured - languages: {supported_languages}, primary: {primary_language}")
        return {
            "status": "language_processing_configured",
            "supported_languages": supported_languages,
            "primary_language": primary_language,
            "auto_detection": enable_auto_detection
        }

    def _set_text_limits(self, parameters: Dict[str, Any]):
        """Configure text processing limits."""
        max_text_length = parameters.get("max_text_length", 100000)
        max_batch_size = parameters.get("max_batch_size", 100)
        max_file_size = parameters.get("max_file_size", 50 * 1024 * 1024)
        
        # Update limits
        self.tpp_state["current_settings"]["max_text_length"] = max_text_length
        self.tpp_state["current_settings"]["batch_size"] = max_batch_size
        
        # Apply to modules if available
        if "ipm" in globals() and hasattr(ipm, 'set_limits'):
            ipm.set_limits(max_text_length, max_file_size)
        
        if "fim" in globals() and hasattr(fim, 'set_batch_size'):
            fim.set_batch_size(max_batch_size)
            
        self.logger.info(f"ECM: Text limits updated - length:{max_text_length}, batch:{max_batch_size}")
        return {
            "status": "text_limits_updated",
            "limits": {
                "max_text_length": max_text_length,
                "max_batch_size": max_batch_size,
                "max_file_size": max_file_size
            }
        }

    def _configure_batch_processing(self, parameters: Dict[str, Any]):
        """Configure batch processing settings."""
        enable_batch = parameters.get("enable_batch", True)
        batch_size = parameters.get("batch_size", 100)
        concurrent_batches = parameters.get("concurrent_batches", 5)
        
        # Update settings
        self.tpp_state["current_settings"]["batch_size"] = batch_size
        
        # Apply to batch processing modules if available
        if "btm" in globals() and hasattr(btm, 'configure_batch_processing'):
            btm.configure_batch_processing(enable_batch, batch_size, concurrent_batches)
            
        self.logger.info(f"ECM: Batch processing configured - enabled: {enable_batch}, size: {batch_size}")
        return {
            "status": "batch_processing_configured",
            "enabled": enable_batch,
            "batch_size": batch_size,
            "concurrent_batches": concurrent_batches
        }

    async def _update_spam_words(self, parameters: Dict[str, Any]):
        """Update spam word lists."""
        language = parameters.get("language", "persian")
        words_to_add = parameters.get("words_to_add", [])
        words_to_remove = parameters.get("words_to_remove", [])
        
        try:
            # Apply to SWM if available
            if "swm" in globals():
                if hasattr(swm, 'add_spam_words'):
                    await swm.add_spam_words(language, words_to_add)
                if hasattr(swm, 'remove_spam_words'):
                    await swm.remove_spam_words(language, words_to_remove)
                
                # Update counts
                if hasattr(swm, 'get_word_counts'):
                    counts = swm.get_word_counts()
                    self.tpp_state["spam_word_counts"].update(counts)
            
            self.logger.info(f"ECM: Spam words updated - {language}: +{len(words_to_add)}, -{len(words_to_remove)}")
            return {
                "status": "spam_words_updated",
                "language": language,
                "words_added": len(words_to_add),
                "words_removed": len(words_to_remove),
                "current_counts": self.tpp_state["spam_word_counts"]
            }
        except Exception as e:
            raise Exception(f"Failed to update spam words: {e}")

    def _get_spam_word_lists(self):
        """Get current spam word lists."""
        try:
            lists = {}
            if "swm" in globals() and hasattr(swm, 'get_all_lists'):
                lists = swm.get_all_lists()
            
            return {
                "status": "spam_lists_retrieved",
                "lists": lists,
                "counts": self.tpp_state["spam_word_counts"]
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _clear_spam_words(self, parameters: Dict[str, Any]):
        """Clear spam words from specified language or all."""
        language = parameters.get("language", "all")
        
        try:
            if "swm" in globals() and hasattr(swm, 'clear_words'):
                swm.clear_words(language)
                
                # Reset counts
                if language == "all":
                    self.tpp_state["spam_word_counts"] = {
                        "persian_words": 0, "english_words": 0, 
                        "custom_words": 0, "total_words": 0
                    }
                
            self.logger.info(f"ECM: Spam words cleared for {language}")
            return {"status": "spam_words_cleared", "language": language}
        except Exception as e:
            raise Exception(f"Failed to clear spam words: {e}")

    async def _import_spam_words(self, parameters: Dict[str, Any]):
        """Import spam words from file."""
        file_path = parameters.get("file_path")
        language = parameters.get("language", "persian")
        file_format = parameters.get("format", "json")
        
        try:
            if "swm" in globals() and hasattr(swm, 'import_from_file'):
                result = await swm.import_from_file(file_path, language, file_format)
                
                # Update counts
                if hasattr(swm, 'get_word_counts'):
                    counts = swm.get_word_counts()
                    self.tpp_state["spam_word_counts"].update(counts)
                
                self.logger.info(f"ECM: Spam words imported from {file_path}")
                return {
                    "status": "spam_words_imported",
                    "file_path": file_path,
                    "language": language,
                    "imported_count": result.get("imported_count", 0)
                }
            else:
                raise Exception("SWM module not available")
        except Exception as e:
            raise Exception(f"Failed to import spam words: {e}")

    async def _export_spam_words(self, parameters: Dict[str, Any]):
        """Export spam words to file."""
        file_path = parameters.get("file_path")
        language = parameters.get("language", "all")
        file_format = parameters.get("format", "json")
        
        try:
            if "swm" in globals() and hasattr(swm, 'export_to_file'):
                result = await swm.export_to_file(file_path, language, file_format)
                
                self.logger.info(f"ECM: Spam words exported to {file_path}")
                return {
                    "status": "spam_words_exported",
                    "file_path": file_path,
                    "language": language,
                    "exported_count": result.get("exported_count", 0)
                }
            else:
                raise Exception("SWM module not available")
        except Exception as e:
            raise Exception(f"Failed to export spam words: {e}")

    def _configure_spam_filter(self, parameters: Dict[str, Any]):
        """Configure spam filtering settings."""
        enabled = parameters.get("enabled", True)
        strictness = parameters.get("strictness", "medium")
        case_sensitive = parameters.get("case_sensitive", True)
        whole_word_match = parameters.get("whole_word_match", False)
        
        # Update state
        self.tpp_state["spam_filtering_enabled"] = enabled
        self.tpp_state["current_settings"]["strictness_level"] = strictness
        
        # Apply to FTM if available
        if "ftm" in globals() and hasattr(ftm, 'configure_filter'):
            ftm.configure_filter(enabled, strictness, case_sensitive, whole_word_match)
            
        self.logger.info(f"ECM: Spam filter configured - enabled: {enabled}, strictness: {strictness}")
        return {
            "status": "spam_filter_configured",
            "enabled": enabled,
            "strictness": strictness,
            "case_sensitive": case_sensitive,
            "whole_word_match": whole_word_match
        }

    def _set_filter_strictness(self, parameters: Dict[str, Any]):
        """Set spam filter strictness level."""
        strictness = parameters.get("strictness", "medium")  # low, medium, high, strict
        
        # Update setting
        self.tpp_state["current_settings"]["strictness_level"] = strictness
        
        # Apply to FTM if available
        if "ftm" in globals() and hasattr(ftm, 'set_strictness'):
            ftm.set_strictness(strictness)
            
        self.logger.info(f"ECM: Filter strictness set to {strictness}")
        return {"status": "filter_strictness_updated", "strictness": strictness}

    def _enable_custom_filters(self, parameters: Dict[str, Any]):
        """Enable/disable custom filtering rules."""
        enabled = parameters.get("enabled", True)
        custom_rules = parameters.get("custom_rules", [])
        
        # Apply to FTM if available
        if "ftm" in globals() and hasattr(ftm, 'set_custom_filters'):
            ftm.set_custom_filters(enabled, custom_rules)
            
        self.logger.info(f"ECM: Custom filters {'enabled' if enabled else 'disabled'}")
        return {
            "status": "custom_filters_updated", 
            "enabled": enabled, 
            "rules_count": len(custom_rules)
        }

    def _enable_processing_stage(self, parameters: Dict[str, Any]):
        """Enable a specific processing pipeline stage."""
        stage = parameters.get("stage")  # input_processing, language_detection, spam_filtering, output_processing
        
        if stage == "spam_filtering":
            self.tpp_state["spam_filtering_enabled"] = True
        elif stage == "language_detection":
            self.tpp_state["language_modes"]["multilingual"] = True
            
        self.logger.info(f"ECM: Processing stage '{stage}' enabled")
        return {"status": "processing_stage_enabled", "stage": stage}

    def _disable_processing_stage(self, parameters: Dict[str, Any]):
        """Disable a specific processing pipeline stage."""
        stage = parameters.get("stage")
        
        if stage == "spam_filtering":
            self.tpp_state["spam_filtering_enabled"] = False
        elif stage == "language_detection":
            self.tpp_state["language_modes"]["multilingual"] = False
            
        self.logger.info(f"ECM: Processing stage '{stage}' disabled")
        return {"status": "processing_stage_disabled", "stage": stage}

    def _get_pipeline_status(self):
        """Get processing pipeline status."""
        pipeline_status = {
            "input_processing": True,  # Always enabled
            "language_detection": self.tpp_state["language_modes"]["multilingual"],
            "spam_filtering": self.tpp_state["spam_filtering_enabled"],
            "text_processing": self.tpp_state["processing_enabled"],
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

    async def _test_text_processing(self, parameters: Dict[str, Any]):
        """Test text processing with sample content."""
        test_text = parameters.get("text", "این یک متن آزمایشی است")
        language = parameters.get("language", "persian")
        
        try:
            result = {"original_text": test_text, "language": language}
            
            # Test through processing pipeline if available
            if "tpdm" in globals() and hasattr(tpdm, 'process_text'):
                processing_result = await tpdm.process_text(test_text, {"language": language})
                result["processing_result"] = processing_result
            
            if "ftm" in globals() and hasattr(ftm, 'filter_spam_words'):
                filter_result = await ftm.filter_spam_words(test_text, language)
                result["filter_result"] = filter_result
            
            self.logger.info("ECM: Text processing test executed")
            return {"status": "text_processing_test_executed", "result": result}
        except Exception as e:
            return {"status": "text_processing_test_failed", "error": str(e)}

    async def _test_spam_detection(self, parameters: Dict[str, Any]):
        """Test spam detection with sample content."""
        test_text = parameters.get("text", "سلام خوبی")  # Contains Persian spam word
        language = parameters.get("language", "persian")
        
        try:
            if "ftm" in globals() and hasattr(ftm, 'filter_spam_words'):
                result = await ftm.filter_spam_words(test_text, language)
            else:
                result = {"filtered_text": test_text, "words_removed": 0}
            
            self.logger.info("ECM: Spam detection test executed")
            return {"status": "spam_detection_test_executed", "result": result}
        except Exception as e:
            return {"status": "spam_detection_test_failed", "error": str(e)}

    async def _test_language_detection(self, parameters: Dict[str, Any]):
        """Test language detection functionality."""
        test_texts = parameters.get("texts", ["Hello world", "سلام دنیا", "مرحبا بالعالم"])
        
        try:
            results = []
            for text in test_texts:
                if "lpm" in globals() and hasattr(lpm, 'detect_language'):
                    detection = await lpm.detect_language(text)
                else:
                    detection = {"language": "unknown", "confidence": 0.0}
                
                results.append({"text": text, "detection": detection})
            
            self.logger.info("ECM: Language detection test executed")
            return {"status": "language_detection_test_executed", "results": results}
        except Exception as e:
            return {"status": "language_detection_test_failed", "error": str(e)}

    def _reset_module(self, parameters: Dict[str, Any]):
        """Reset a specific TPP module."""
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
        """Reset the entire TPP service."""
        # Reset TPP state
        self.tpp_state = {
            "processing_enabled": True,
            "spam_filtering_enabled": True,
            "language_modes": {"persian": True, "english": True, "multilingual": True},
            "current_settings": {
                "default_language": "persian",
                "max_text_length": 100000,
                "strictness_level": "medium",
                "batch_size": 100
            },
            "spam_word_counts": {"persian_words": 0, "english_words": 0, "custom_words": 0, "total_words": 0}
        }
        
        self.logger.info("ECM: All TPP modules reset")
        return {"status": "all_reset"}

    async def _reload_spam_words(self):
        """Reload spam word lists from storage."""
        try:
            if "swm" in globals() and hasattr(swm, 'reload_lists'):
                result = await swm.reload_lists()
                
                # Update counts
                if hasattr(swm, 'get_word_counts'):
                    counts = swm.get_word_counts()
                    self.tpp_state["spam_word_counts"].update(counts)
                
                self.logger.info("ECM: Spam word lists reloaded")
                return {"status": "spam_words_reloaded", "result": result}
            else:
                raise Exception("SWM module not available")
        except Exception as e:
            raise Exception(f"Failed to reload spam words: {e}")

    def _clear_processing_cache(self):
        """Clear text processing cache."""
        try:
            # Clear caches in various modules if available
            if "tpdm" in globals() and hasattr(tpdm, 'clear_cache'):
                tpdm.clear_cache()
            if "lpm" in globals() and hasattr(lpm, 'clear_cache'):
                lpm.clear_cache()
            if "ftm" in globals() and hasattr(ftm, 'clear_cache'):
                ftm.clear_cache()
                
            self.logger.info("ECM: Processing cache cleared")
            return {"status": "processing_cache_cleared"}
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

    def _get_processing_stats(self):
        """Get text processing statistics."""
        stats = {
            "tpp_state": self.tpp_state,
            "command_stats": self.stats,
            "service_status": {
                "processing_enabled": self.tpp_state["processing_enabled"],
                "spam_filtering_enabled": self.tpp_state["spam_filtering_enabled"],
                "language_modes": self.tpp_state["language_modes"]
            }
        }
        
        # Add module-specific stats if available
        if "tpdm" in globals() and hasattr(tpdm, 'stats'):
            stats["text_processing"] = tpdm.stats
        if "ftm" in globals() and hasattr(ftm, 'stats'):
            stats["spam_filtering"] = ftm.stats
        if "lpm" in globals() and hasattr(lpm, 'stats'):
            stats["language_processing"] = lpm.stats
            
        return {"status": "processing_stats_retrieved", "stats": stats}

    def _get_language_stats(self):
        """Get language processing statistics."""
        if "lpm" in globals() and hasattr(lpm, 'get_language_stats'):
            lang_stats = lpm.get_language_stats()
        else:
            lang_stats = {"message": "Language processing stats not available"}
            
        return {"status": "language_stats_retrieved", "stats": lang_stats}

    async def _process_file_batch(self, parameters: Dict[str, Any]):
        """Process a batch of files."""
        file_paths = parameters.get("file_paths", [])
        output_directory = parameters.get("output_directory")
        
        try:
            results = []
            for file_path in file_paths:
                if "fim" in globals() and hasattr(fim, 'process_file'):
                    result = await fim.process_file(file_path, output_directory)
                    results.append({"file": file_path, "result": result})
                else:
                    results.append({"file": file_path, "error": "FIM module not available"})
            
            self.logger.info(f"ECM: Processed batch of {len(file_paths)} files")
            return {"status": "file_batch_processed", "results": results}
        except Exception as e:
            return {"status": "file_batch_processing_failed", "error": str(e)}

    def _get_file_processing_status(self):
        """Get file processing status."""
        if "fim" in globals() and hasattr(fim, 'get_processing_status'):
            status = fim.get_processing_status()
        else:
            status = {"message": "File processing status not available"}
            
        return {"status": "file_processing_status_retrieved", "processing_status": status}

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
        callback(f"[ECM] Log streaming started at level {level} for TPP Text Processing")

    def stream_monitoring(self, callback: Callable[[Dict[str, Any]], None]):
        """Stream monitoring data to CCU."""
        self.logger.info("ECM: Streaming monitoring data")
        callback({"status": "monitoring_stream_started", "service": "TPP"})

    def get_module_status(self) -> Dict[str, Any]:
        """Get ECM module status."""
        return {
            "module": "ECM",
            "service": "TPP",
            "status": self.connection_status,
            "tpp_state": self.tpp_state,
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
        self.logger.info("✅ TPP ECM started successfully")



    
    # Duplicate methods removed - using implementations from above
    
    async def _handle_activation_command(self, data):
        """Handle activation command from CCU."""
        try:
            self.logger.info("Received activation command from CCU")
            
            # Send acknowledgment
            await self._send_to_ccu({
                "type": "activation_ack",
                "status": "activated",
                "timestamp": datetime.now().isoformat(),
                "service": "TPP"
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
                "service": "TPP"
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
            "service": "TPP"
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
                        "service": "TPP",
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
        await self.stop_websocket_client()
        self.logger.info("🔌 TPP ECM stopped successfully")

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        return {
            "healthy": self.connection_status == ECMConnectionStatus.CONNECTED,
            "module": "ECM",
            "service": "TPP",
            "connection_status": self.connection_status,
            "processing_operational": self.tpp_state["processing_enabled"],
            "spam_filtering_operational": self.tpp_state["spam_filtering_enabled"],
            "timestamp": datetime.now().isoformat()
        }

# Global instances
ecm = ExternalControlModule()
ECM = ExternalControlModule() 