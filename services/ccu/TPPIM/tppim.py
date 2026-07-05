"""
TPP Interaction Module (TPPIM) for CCU

This module handles all communication and coordination with the TPP (Text Processing and Purification) microservice.
The TPP service has been refactored to a modular architecture with advanced text processing capabilities.

Key Features:
- Advanced text processing and spam filtering
- Persian/Farsi language processing with alphabet organization
- Multi-language support (Persian, English, Arabic, Urdu)
- Dynamic spam word management
- Real-time health monitoring
- Batch processing capabilities
"""

import logging
import asyncio
import json
import websockets
import aiohttp
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
import sys
from pathlib import Path

# Add utils path for WebSocketPortManager
sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
from websocket_port_manager import WebSocketPortManager


class TPPInteractionModule:
    """
    TPP Interaction Module for CCU
    
    Manages all interactions with the TPP (Text Processing and Purification) microservice.
    Handles request routing, health monitoring, and service coordination.
    """
    
    def __init__(self, ccu_config: Dict[str, Any] = None):
        """Initialize the TPPIM module."""
        self.logger = logging.getLogger(__name__)
        self.module_name = "TPPIM"
        self.is_active = False
        
        # Use WebSocket port manager from CCU config (shared instance)
        self.port_manager = ccu_config.get('websocket_port_manager') if ccu_config else None
        if not self.port_manager:
            # Fallback to creating new instance if not provided
            self.port_manager = WebSocketPortManager()
            self.logger.warning("No WebSocket port manager provided, creating new instance")
        
        # NEW ARCHITECTURE: WebSocket SERVER configuration
        self.websocket_server = None
        self.websocket_server_port = None
        self.connected_clients = {}  # Track TPP ECM connections
        self.max_clients = 1  # Only one TPP ECM should connect
        
        # Load TPP configuration from CCU (includes PMM paths and network config)
        tpp_setting = ccu_config.get('tpp_setting', {}) if ccu_config else {}
        
        # TPP service configuration (with PMM-provided defaults)
        self.tpp_config = {
            "service_name": tpp_setting.get("service_name", "TPP"),
            "host": tpp_setting.get("host", "localhost"),
            "api_port": tpp_setting.get("ports", {}).get("api", 8080),
            "health_port": tpp_setting.get("ports", {}).get("health", 9091),
            "websocket_port": tpp_setting.get("ports", {}).get("websocket", 11490),
            "timeout": tpp_setting.get("timeout", 30),
            "max_retries": tpp_setting.get("max_retries", 3),
            "retry_delay": tpp_setting.get("retry_delay", 5)
        }
        
        # Connection management
        self.connections = {
            "http_session": None,
            "websocket": None,
            "health_check_interval": 30
        }
        
        # Service status tracking
        self.service_status = {
            "is_healthy": False,
            "last_health_check": None,
            "last_successful_request": None,
            "consecutive_failures": 0,
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0
        }
        
        # Processing capabilities
        self.processing_capabilities = {
            "supported_languages": ["fa", "en", "ar", "ur"],
            "max_text_length": 100000,
            "max_file_size": 50 * 1024 * 1024,  # 50MB
            "processing_modes": ["persian", "multilingual", "custom"],
            "batch_processing": True,
            "real_time_processing": True
        }
        
        # Request tracking
        self.active_requests = {}
        
        self.logger.info(f"{self.module_name} initialized for enhanced TPP integration")
    
    async def start(self):
        """Start the TPPIM module."""
        try:
            self.is_active = True
            
            
            # Start WebSocket server for ECM connections
            await self.start_websocket_server()
            # Initialize HTTP session
            self.connections["http_session"] = aiohttp.ClientSession()
            
            # Start health monitoring
            asyncio.create_task(self._health_monitoring_loop())
            
            # Start WebSocket connection
            asyncio.create_task(self._maintain_websocket_connection())
            
            # Perform initial health check
            await self._perform_health_check()
            
            self.logger.info(f"{self.module_name} started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start {self.module_name}: {e}")
            raise
    async def start_websocket_server(self):
        """Start WebSocket server for TPP ECM connections."""
        try:
            self.logger.info("Starting TPPIM WebSocket server...")
            
            # Start WebSocket server using port manager
            self.websocket_server = await self.port_manager.start_ccu_websocket_server(
                "TPPIM", 
                self.handle_tpp_connection
            )
            
            if not self.websocket_server:
                raise Exception("Failed to start WebSocket server - no available ports")
            
            # Get the allocated port
            self.websocket_server_port = self.port_manager.allocated_ports.get("TPPIM")
            
            self.logger.info(f"✅ TPPIM WebSocket server started on port {self.websocket_server_port}")
            self.logger.info(f"🔗 TPP ECM should connect to: ws://localhost:{self.websocket_server_port}/ws")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start TPPIM WebSocket server: {e}")
            raise
    
    async def handle_tpp_connection(self, websocket, path):
        """Handle incoming TPP ECM WebSocket connection."""
        client_id = None
        try:
            client_id = f"TPP_ECM_{id(websocket)}"
            client_address = websocket.remote_address
            self.logger.info(f"🔗 TPP ECM connected from {client_address} (ID: {client_id})")
            
            # Check if we already have max connections
            if len(self.connected_clients) >= self.max_clients:
                self.logger.warning(f"⚠️ Maximum TPP connections ({self.max_clients}) reached, rejecting new connection")
                await websocket.close(code=1008, reason="Maximum connections reached")
                return
            
            # Add client to connected clients
            self.connected_clients[client_id] = {
                "websocket": websocket,
                "connected_at": datetime.now(),
                "last_heartbeat": datetime.now(),
                "client_address": client_address
            }
            
            self.logger.info(f"✅ TPP ECM client registered (Total clients: {len(self.connected_clients)})")
            
            # Send welcome message
            welcome_msg = {
                "type": "welcome",
                "client_id": client_id,
                "server": "TPPIM",
                "timestamp": datetime.now().isoformat(),
                "message": "Connected to CCU TPPIM WebSocket server"
            }
            await websocket.send(json.dumps(welcome_msg))
            
            # Listen for messages from this TPP ECM client
            await self.handle_client_messages(websocket, client_id)
            
        except Exception as e:
            self.logger.error(f"❌ Error handling TPP connection: {e}")
        finally:
            # Clean up client connection
            if client_id and client_id in self.connected_clients:
                del self.connected_clients[client_id]
                self.logger.info(f"🔌 TPP ECM client {client_id} disconnected")
    
    async def handle_client_messages(self, websocket, client_id: str):
        """Listen for messages from a specific TPP ECM client."""
        try:
            async for message in websocket:
                self.logger.debug(f"Received message from TPP ECM {client_id}: {message}")
                
                # Update heartbeat
                if client_id in self.connected_clients:
                    self.connected_clients[client_id]["last_heartbeat"] = datetime.now()
                
                try:
                    data = json.loads(message)
                    # Process message
                    await self.handle_tpp_message(data, client_id)
                except json.JSONDecodeError as e:
                    self.logger.error(f"Invalid JSON message from TPP client {client_id}: {e}")
                    error_response = {
                        "type": "error",
                        "error": "invalid_json",
                        "message": str(e),
                        "timestamp": datetime.now().isoformat()
                    }
                    await websocket.send(json.dumps(error_response))
                
        except Exception as e:
            self.logger.error(f"Error handling messages from TPP ECM {client_id}: {e}")
    
    async def handle_tpp_message(self, data: Dict[str, Any], client_id: str):
        """Handle a message from TPP ECM."""
        try:
            message_type = data.get("type", "unknown")
            
            self.logger.debug(f"Processing {message_type} message from TPP ECM {client_id}")
            
            # Handle different message types
            if message_type == "heartbeat":
                await self._handle_tpp_heartbeat(data, client_id)
            elif message_type == "status_update":
                await self._handle_tpp_status_update(data)
            elif message_type == "processing_result":
                await self._handle_processing_result(data)
            elif message_type == "spam_list_update":
                await self._handle_spam_list_update(data)
            elif message_type == "health_report":
                await self._handle_tpp_health_report(data)
            elif message_type == "error_report":
                await self._handle_tpp_error_report(data)
            else:
                self.logger.warning(f"Unknown message type '{message_type}' from TPP ECM {client_id}")
                
        except Exception as e:
            self.logger.error(f"Error processing message from TPP ECM {client_id}: {e}")
    
    async def _handle_tpp_heartbeat(self, data: Dict[str, Any], client_id: str):
        """Handle heartbeat from TPP ECM."""
        response = {
            "type": "heartbeat_response",
            "timestamp": datetime.now().isoformat(),
            "server": "TPPIM",
            "client_id": client_id
        }
        
        if client_id in self.connected_clients:
            try:
                await self.connected_clients[client_id]["websocket"].send(json.dumps(response))
            except Exception as e:
                self.logger.error(f"Failed to send heartbeat response to {client_id}: {e}")
    
    async def _handle_tpp_status_update(self, data: Dict[str, Any]):
        """Handle status update from TPP service."""
        try:
            status = data.get("status", {})
            self.service_status["is_healthy"] = status.get("is_active", False)
            self.service_status["last_health_check"] = datetime.now()
            self.logger.debug(f"Received TPP status update: {status}")
        except Exception as e:
            self.logger.error(f"Error handling TPP status update: {e}")
    
    async def _handle_processing_result(self, data: Dict[str, Any]):
        """Handle processing result from TPP service."""
        try:
            request_id = data.get("request_id")
            if request_id in self.active_requests:
                self.active_requests[request_id]["status"] = "completed"
                self.active_requests[request_id]["result"] = data.get("result")
                self.logger.debug(f"TPP processing result received for {request_id}")
        except Exception as e:
            self.logger.error(f"Error handling processing result: {e}")
    
    async def _handle_spam_list_update(self, data: Dict[str, Any]):
        """Handle spam list update notification from TPP."""
        try:
            update_info = data.get("update", {})
            self.logger.info(f"TPP spam list updated: {update_info}")
        except Exception as e:
            self.logger.error(f"Error handling spam list update: {e}")
    
    async def _handle_tpp_health_report(self, data: Dict[str, Any]):
        """Handle health report from TPP service."""
        try:
            health_info = data.get("health", {})
            self.service_status["is_healthy"] = health_info.get("healthy", False)
            self.service_status["last_health_check"] = datetime.now()
            self.logger.debug(f"TPP health report: {health_info}")
        except Exception as e:
            self.logger.error(f"Error handling TPP health report: {e}")
    
    async def _handle_tpp_error_report(self, data: Dict[str, Any]):
        """Handle error report from TPP service."""
        try:
            error_info = data.get("error", {})
            self.service_status["consecutive_failures"] += 1
            self.logger.error(f"TPP error report: {error_info}")
        except Exception as e:
            self.logger.error(f"Error handling TPP error report: {e}")
    
    async def send_command_to_tpp(self, command: Dict[str, Any]) -> bool:
        """Send command to connected TPP ECM client."""
        if not self.connected_clients:
            self.logger.warning("No TPP ECM clients connected - cannot send command")
            return False
        
        try:
            # Send to all connected clients (should be just one)
            for client_id, client_info in self.connected_clients.items():
                websocket = client_info["websocket"]
                await websocket.send(json.dumps(command))
                self.logger.debug(f"Sent command to TPP ECM {client_id}: {command.get('type', 'unknown')}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending command to TPP ECM: {e}")
            return False


    
    async def stop(self):
        """Stop the TPPIM module."""
        try:
            self.is_active = False
            
            
            # Close all client connections
            for client_id, client_info in list(self.connected_clients.items()):
                try:
                    await client_info["websocket"].close()
                except:
                    pass
            self.connected_clients.clear()
            
            # Stop WebSocket server
            if self.websocket_server:
                self.websocket_server.close()
                await self.websocket_server.wait_closed()
                self.websocket_server = None
            # Close connections
            if self.connections["http_session"]:
                await self.connections["http_session"].close()
            
            if self.connections["websocket"]:
                await self.connections["websocket"].close()
            
            self.logger.info(f"{self.module_name} stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to stop {self.module_name}: {e}")
            raise
    
    async def process_text(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process text through TPP service.
        
        Args:
            request_data: Request data containing text and parameters
            
        Returns:
            Processing result from TPP service
        """
        try:
            request_id = request_data.get("request_id", f"tpp_req_{uuid.uuid4().hex[:12]}")
            
            self.logger.info(f"Processing text request {request_id} via TPP")
            
            # Track request
            self.active_requests[request_id] = {
                "start_time": datetime.now(),
                "status": "processing",
                "request_data": request_data
            }
            
            # Prepare TPP request
            tpp_request = {
                "request_id": request_id,
                "message_text": request_data.get("message_text", ""),
                "language": request_data.get("language", "auto"),
                "processing_mode": request_data.get("processing_mode", "persian"),
                "source_block": "CCU",
                "timestamp": datetime.now().isoformat(),
                "metadata": request_data.get("metadata", {})
            }
            
            # Send request to TPP
            result = await self._send_http_request("POST", "/process", tpp_request)
            
            # Update tracking
            if result.get("success", False):
                self.service_status["successful_requests"] += 1
                self.service_status["last_successful_request"] = datetime.now()
                self.service_status["consecutive_failures"] = 0
                
                self.active_requests[request_id]["status"] = "completed"
                
                self.logger.info(f"TPP processed request {request_id} successfully")
                
                return {
                    "success": True,
                    "request_id": request_id,
                    "processed_data": result.get("processed_data", {}),
                    "processing_time": result.get("processing_time", 0),
                    "service": "TPP",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                self.service_status["failed_requests"] += 1
                self.service_status["consecutive_failures"] += 1
                
                self.active_requests[request_id]["status"] = "failed"
                
                self.logger.error(f"TPP failed to process request {request_id}: {result}")
                
                return {
                    "success": False,
                    "request_id": request_id,
                    "error": result.get("error", "Unknown error"),
                    "service": "TPP",
                    "timestamp": datetime.now().isoformat()
                }
            
        except Exception as e:
            self.logger.error(f"Error processing text via TPP: {e}")
            
            self.service_status["failed_requests"] += 1
            self.service_status["consecutive_failures"] += 1
            
            return {
                "success": False,
                "request_id": request_data.get("request_id", "unknown"),
                "error": str(e),
                "service": "TPP",
                "timestamp": datetime.now().isoformat()
            }
    
    async def process_file(self, file_path: str, output_path: str = None) -> Dict[str, Any]:
        """
        Process file through TPP service.
        
        Args:
            file_path: Path to input file
            output_path: Path for output file (optional)
            
        Returns:
            Processing result from TPP service
        """
        try:
            request_data = {
                "request_id": f"tpp_file_{uuid.uuid4().hex[:12]}",
                "file_path": file_path,
                "output_path": output_path,
                "source_block": "CCU",
                "timestamp": datetime.now().isoformat()
            }
            
            result = await self._send_http_request("POST", "/process/file", request_data)
            
            if result.get("success", False):
                self.logger.info(f"TPP processed file {file_path} successfully")
                return result
            else:
                self.logger.error(f"TPP failed to process file {file_path}: {result}")
                return result
                
        except Exception as e:
            self.logger.error(f"Error processing file via TPP: {e}")
            return {
                "success": False,
                "error": str(e),
                "service": "TPP",
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_spam_lists(self) -> Dict[str, Any]:
        """Get spam word lists from TPP service."""
        try:
            result = await self._send_http_request("GET", "/spam-lists")
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting spam lists from TPP: {e}")
            return {"success": False, "error": str(e)}
    
    async def add_spam_words(self, words: List[str], language: str = "fa") -> Dict[str, Any]:
        """Add spam words to TPP service."""
        try:
            request_data = {
                "words": words,
                "language": language,
                "source": "CCU",
                "timestamp": datetime.now().isoformat()
            }
            
            result = await self._send_http_request("POST", "/spam-lists/add", request_data)
            return result
            
        except Exception as e:
            self.logger.error(f"Error adding spam words to TPP: {e}")
            return {"success": False, "error": str(e)}
    
    async def remove_spam_words(self, words: List[str], language: str = "fa") -> Dict[str, Any]:
        """Remove spam words from TPP service."""
        try:
            request_data = {
                "words": words,
                "language": language,
                "source": "CCU",
                "timestamp": datetime.now().isoformat()
            }
            
            result = await self._send_http_request("DELETE", "/spam-lists/remove", request_data)
            return result
            
        except Exception as e:
            self.logger.error(f"Error removing spam words from TPP: {e}")
            return {"success": False, "error": str(e)}
    
    async def _send_http_request(self, method: str, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send HTTP request to TPP service."""
        try:
            url = f"http://{self.tpp_config['host']}:{self.tpp_config['api_port']}{endpoint}"
            
            timeout = aiohttp.ClientTimeout(total=self.tpp_config['timeout'])
            
            async with self.connections["http_session"].request(
                method, url, json=data, timeout=timeout
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}: {error_text}"
                    }
                    
        except Exception as e:
            self.logger.error(f"HTTP request failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _perform_health_check(self) -> bool:
        """Perform health check on TPP service."""
        try:
            result = await self._send_http_request("GET", "/health")
            
            if result.get("healthy", False):
                self.service_status["is_healthy"] = True
                self.service_status["last_health_check"] = datetime.now()
                self.service_status["consecutive_failures"] = 0
                
                self.logger.debug("TPP service health check passed")
                return True
            else:
                self.service_status["is_healthy"] = False
                self.service_status["consecutive_failures"] += 1
                
                self.logger.warning(f"TPP service health check failed: {result}")
                return False
                
        except Exception as e:
            self.service_status["is_healthy"] = False
            self.service_status["consecutive_failures"] += 1
            
            self.logger.error(f"TPP service health check error: {e}")
            return False
    
    async def _health_monitoring_loop(self):
        """Continuous health monitoring loop."""
        while self.is_active:
            try:
                await self._perform_health_check()
                await asyncio.sleep(self.connections["health_check_interval"])
                
            except Exception as e:
                self.logger.error(f"Health monitoring loop error: {e}")
                await asyncio.sleep(self.connections["health_check_interval"])
    
    async def _maintain_websocket_connection(self):
        """Maintain WebSocket connection to TPP service."""
        while self.is_active:
            try:
                uri = f"ws://{self.tpp_config['host']}:{self.tpp_config['websocket_port']}/ws"
                
                async with websockets.connect(uri) as websocket:
                    self.connections["websocket"] = websocket
                    self.logger.info("WebSocket connection to TPP established")
                    
                    # Listen for messages
                    async for message in websocket:
                        await self._handle_websocket_message(message)
                        
            except Exception as e:
                self.logger.error(f"WebSocket connection error: {e}")
                await asyncio.sleep(10)  # Retry after 10 seconds
    
    async def _handle_websocket_message(self, message: str):
        """Handle incoming WebSocket messages from TPP."""
        try:
            data = json.loads(message)
            message_type = data.get("type", "unknown")
            
            if message_type == "status_update":
                await self._handle_status_update(data)
            elif message_type == "request_update":
                await self._handle_request_update(data)
            else:
                self.logger.debug(f"Received unknown message type: {message_type}")
                
        except Exception as e:
            self.logger.error(f"Error handling WebSocket message: {e}")
    
    async def _handle_status_update(self, data: Dict[str, Any]):
        """Handle status update from TPP service."""
        try:
            tpp_status = data.get("status", {})
            
            # Update service status
            self.service_status["is_healthy"] = tpp_status.get("is_active", False)
            self.service_status["last_health_check"] = datetime.now()
            
            self.logger.debug(f"Received TPP status update: {tpp_status}")
            
        except Exception as e:
            self.logger.error(f"Error handling status update: {e}")
    
    async def _handle_request_update(self, data: Dict[str, Any]):
        """Handle request update from TPP service."""
        try:
            request_id = data.get("request_id")
            status = data.get("status")
            
            if request_id in self.active_requests:
                self.active_requests[request_id]["status"] = status
                self.logger.debug(f"Request {request_id} status updated to {status}")
            
        except Exception as e:
            self.logger.error(f"Error handling request update: {e}")
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get comprehensive service status."""
        return {
            "module": self.module_name,
            "is_active": self.is_active,
            "service_status": self.service_status,
            "processing_capabilities": self.processing_capabilities,
            "active_requests": len(self.active_requests),
            "configuration": self.tpp_config,
            "timestamp": datetime.now().isoformat()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            # Check module health
            module_healthy = self.is_active
            
            # Check TPP service health
            tpp_healthy = await self._perform_health_check()
            
            return {
                "healthy": module_healthy and tpp_healthy,
                "module": self.module_name,
                "tpp_service_healthy": tpp_healthy,
                "last_successful_request": self.service_status["last_successful_request"],
                "consecutive_failures": self.service_status["consecutive_failures"],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "module": self.module_name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current module status."""
        return {
            "module": self.module_name,
            "is_active": self.is_active,
            "service_healthy": self.service_status["is_healthy"],
            "total_requests": self.service_status["total_requests"],
            "successful_requests": self.service_status["successful_requests"],
            "failed_requests": self.service_status["failed_requests"],
            "success_rate": (
                self.service_status["successful_requests"] / 
                max(self.service_status["total_requests"], 1)
            ) * 100,
            "active_requests": len(self.active_requests),
            "supported_languages": self.processing_capabilities["supported_languages"],
            "timestamp": datetime.now().isoformat()
        } 