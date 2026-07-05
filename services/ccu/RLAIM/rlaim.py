"""
RLA Interaction Module (RLAIM) for CCU

This module manages the interaction between CCU and the RLA (Request Limit Analyzer) microservice.
Based on the RLA_CONFIGURATION_PLAN.md, this module provides:

- WebSocket SERVER for RLA ECM connections (NEW ARCHITECTURE)
- Accept connections from RLA ECM module
- Request validation coordination
- Limit enforcement monitoring
- Gateway control and status tracking
- Real-time monitoring of RLA modules

Architecture: CCU runs WebSocket servers, microservices connect as clients
The RLA serves as the primary Gateway/Ingress Controller for the entire microservice ecosystem.
"""

import asyncio
import json
import logging
import websockets
from typing import Dict, Any, Optional, List
from datetime import datetime
import aiohttp
from dataclasses import dataclass
import sys
from pathlib import Path

# Add utils path for WebSocketPortManager  
utils_path = Path(__file__).parent.parent / "utils"
sys.path.insert(0, str(utils_path))

try:
    from websocket_port_manager import WebSocketPortManager
except ImportError as e:
    print(f"Failed to import WebSocketPortManager: {e}")
    print(f"Utils path: {utils_path}")
    print(f"Utils path exists: {utils_path.exists()}")
    raise


@dataclass
class RLAStatus:
    """RLA service status information."""
    service: str
    is_active: bool
    total_requests: int
    validated_requests: int
    rejected_requests: int
    average_processing_time: float
    modules: Dict[str, Any]
    last_update: datetime


class RLAInteractionModule:
    """
    RLA Interaction Module
    
    Manages communication with the RLA microservice, which serves as the
    primary gateway/ingress controller for the entire system.
    
    Key Features:
    - WebSocket communication with RLA
    - Real-time monitoring of 14 RLA modules
    - Request validation coordination
    - Limit enforcement tracking
    - Gateway control and activation management
    """
    
    def __init__(self, ccu_config: Dict[str, Any] = None):
        """Initialize the RLAIM module."""
        self.logger = logging.getLogger(__name__)
        self.module_name = "RLAIM"
        self.service_name = "RLA"
        self.is_active = False
        self.is_connected = False  # Add connection status tracking
        
        # Use WebSocket port manager from CCU config (shared instance)
        self.port_manager = ccu_config.get('websocket_port_manager') if ccu_config else None
        if not self.port_manager:
            # Fallback to creating new instance if not provided
            self.port_manager = WebSocketPortManager()
            self.logger.warning("No WebSocket port manager provided, creating new instance")
        
        # Load RLA configuration from CCU (includes PMM paths and network config)
        rla_setting = ccu_config.get('rla_setting', {}) if ccu_config else {}
        
        # Legacy HTTP API configuration (still needed for health checks)
        self.rla_host = rla_setting.get("host", "localhost") 
        self.rla_health_port = rla_setting.get("ports", {}).get("health", 9090)
        
        # Build health endpoints
        self.rla_endpoints = {
            "health": f"http://{self.rla_host}:{self.rla_health_port}/health",
            "status": f"http://{self.rla_host}:{self.rla_health_port}/status", 
            "metrics": f"http://{self.rla_host}:{self.rla_health_port}/metrics"
        }
        
        # NEW ARCHITECTURE: WebSocket SERVER configuration 
        self.websocket_server = None
        self.websocket_server_port = None
        self.connected_clients = {}  # Track RLA ECM connections
        self.max_clients = 1  # Only one RLA ECM should connect
        
        # RLA modules tracking (14 modules)
        self.rla_modules = {
            # Core Validation Modules
            "GVDM": {"name": "Gateway Validation Data Module", "status": "unknown", "last_check": None},
            "IVM": {"name": "Input Validation Module", "status": "unknown", "last_check": None},
            "LEM": {"name": "Limit Enforcement Module", "status": "unknown", "last_check": None},
            "SVM": {"name": "Spam Validation Module", "status": "unknown", "last_check": None},
            
            # Network & Protocol Modules
            "ARM": {"name": "Activation Receiver Module", "status": "unknown", "last_check": None},
            "DRM": {"name": "Data Receiver Module", "status": "unknown", "last_check": None},
            "OPM": {"name": "Output Processing Module", "status": "unknown", "last_check": None},
            
            # Integration & Control Modules
            "CCM": {"name": "CCU Communication Module", "status": "unknown", "last_check": None},
            "ECM": {"name": "External Control Module", "status": "unknown", "last_check": None},
            "FAIM": {"name": "FastAPI Integration Module", "status": "unknown", "last_check": None},
            
            # System Support Modules
            "EMM": {"name": "Error Management Module", "status": "unknown", "last_check": None},
            "MSM": {"name": "Monitoring System Module", "status": "unknown", "last_check": None},
            "BTM": {"name": "Background Tasks Module", "status": "unknown", "last_check": None},
            "TMM": {"name": "Test Management Module", "status": "unknown", "last_check": None}
        }
        
        # RLA status tracking
        self.rla_status = RLAStatus(
            service="RLA",
            is_active=False,
            total_requests=0,
            validated_requests=0,
            rejected_requests=0,
            average_processing_time=0.0,
            modules={},
            last_update=datetime.now()
        )
        
        # Gateway metrics
        self.gateway_metrics = {
            "activation_attempts": 0,
            "successful_activations": 0,
            "failed_activations": 0,
            "data_requests": 0,
            "validation_failures": 0,
            "limit_violations": 0,
            "spam_detections": 0,
            "security_threats": 0,
            "current_connections": 0,
            "throughput_rps": 0.0
        }
        
        # WebSocket connection
        self.websocket = None
        self.websocket_task = None
        self.heartbeat_task = None
        
        # Communication statistics
        self.stats = {
            "total_messages_sent": 0,
            "total_messages_received": 0,
            "connection_attempts": 0,
            "successful_connections": 0,
            "connection_failures": 0,
            "last_connection": None,
            "last_disconnection": None
        }
        
        self.logger.info(f"{self.module_name} initialized for {self.service_name}")
    
    async def start(self):
        """Start the RLAIM module with WebSocket server."""
        try:
            self.logger.info("Starting RLAIM module with WebSocket server...")
            self.is_active = True
            
            # Start WebSocket server for RLA ECM connections
            await self.start_websocket_server()
            
            # Start monitoring tasks  
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            self.logger.info(f"RLAIM module started successfully with WebSocket server on port {self.websocket_server_port}")
            
        except Exception as e:
            self.logger.error(f"Failed to start RLAIM module: {e}")
            raise
    
    async def stop(self):
        """Stop the RLAIM module."""
        try:
            self.is_active = False
            
            # Cancel tasks
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
                try:
                    await self.heartbeat_task
                except asyncio.CancelledError:
                    pass
            
            # Stop WebSocket connection
            await self.stop_websocket_connection()
            
            self.logger.info(f"{self.module_name} stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to stop {self.module_name}: {e}")
            raise
    
    async def start_websocket_server(self):
        """Start WebSocket server for RLA ECM connections."""
        try:
            self.logger.info("Starting RLAIM WebSocket server...")
            
            # Start WebSocket server using port manager
            self.websocket_server = await self.port_manager.start_ccu_websocket_server(
                "RLAIM", 
                self.handle_rla_connection
            )
            
            if not self.websocket_server:
                raise Exception("Failed to start WebSocket server - no available ports")
            
            # Get the allocated port
            self.websocket_server_port = self.port_manager.allocated_ports.get("RLAIM")
            
            self.logger.info(f"✅ RLAIM WebSocket server started on port {self.websocket_server_port}")
            self.logger.info(f"🔗 RLA ECM should connect to: ws://localhost:{self.websocket_server_port}/ws")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start RLAIM WebSocket server: {e}")
            raise
    
    async def handle_rla_connection(self, websocket, path):
        """Handle incoming RLA ECM WebSocket connection."""
        try:
            client_id = f"RLA_ECM_{id(websocket)}"
            client_address = websocket.remote_address
            self.logger.info(f"🔗 RLA ECM connected from {client_address} (ID: {client_id})")
            
            # Check if we already have max connections
            if len(self.connected_clients) >= self.max_clients:
                self.logger.warning(f"⚠️ Maximum RLA connections ({self.max_clients}) reached, rejecting new connection")
                await websocket.close(code=1008, reason="Maximum connections reached")
                return
            
            # Add client to connected clients
            self.connected_clients[client_id] = {
                "websocket": websocket,
                "connected_at": datetime.now(),
                "last_heartbeat": datetime.now(),
                "client_address": client_address
            }
            
            self.is_connected = len(self.connected_clients) > 0
            self.stats["last_connection"] = datetime.now()
            
            self.logger.info(f"✅ RLA ECM client registered (Total clients: {len(self.connected_clients)})")
            
            # Send welcome message
            welcome_msg = {
                "type": "welcome",
                "client_id": client_id,
                "server": "RLAIM",
                "timestamp": datetime.now().isoformat(),
                "message": "Connected to CCU RLAIM WebSocket server"
            }
            await websocket.send(json.dumps(welcome_msg))
            
            # Listen for messages from this RLA ECM client
            await self.handle_client_messages(websocket, client_id)
            
        except Exception as e:
            self.logger.error(f"❌ Error handling RLA connection: {e}")
        finally:
            # Clean up client connection
            if client_id in self.connected_clients:
                del self.connected_clients[client_id]
                self.is_connected = len(self.connected_clients) > 0
                self.stats["last_disconnection"] = datetime.now()
                self.logger.info(f"🔌 RLA ECM client {client_id} disconnected (Remaining: {len(self.connected_clients)})")

    async def handle_client_messages(self, websocket, client_id: str):
        """Handle messages from a specific RLA ECM client."""
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    
                    # Update last heartbeat
                    if client_id in self.connected_clients:
                        self.connected_clients[client_id]["last_heartbeat"] = datetime.now()
                    
                    # Handle the message
                    await self.handle_rla_message(data, client_id)
                    
                except json.JSONDecodeError as e:
                    self.logger.error(f"Invalid JSON message from RLA client {client_id}: {e}")
                    error_response = {
                        "type": "error",
                        "error": "invalid_json",
                        "message": str(e),
                        "timestamp": datetime.now().isoformat()
                    }
                    await websocket.send(json.dumps(error_response))
                    
                except Exception as e:
                    self.logger.error(f"Error handling message from RLA client {client_id}: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"RLA ECM client {client_id} disconnected")
        except Exception as e:
            self.logger.error(f"Error in client message handler for {client_id}: {e}")
    
    async def handle_rla_message(self, data: Dict[str, Any], client_id: str):
        """Handle a message from RLA ECM."""
        try:
            message_type = data.get("type", "unknown")
            
            self.logger.debug(f"Processing {message_type} message from RLA ECM {client_id}")
            
            # Handle different message types
            if message_type == "heartbeat":
                await self._handle_heartbeat(data, client_id)
            elif message_type == "status_update":
                await self._handle_status_update(data)
            elif message_type == "service_registration":
                await self._handle_service_registration(data)
            elif message_type == "health_report":
                await self._handle_health_report(data)
            elif message_type == "alert":
                await self._handle_alert(data)
            elif message_type == "error_report":
                await self._handle_error_report(data)
            elif message_type == "module_status":
                await self._handle_module_status(data)
            elif message_type == "gateway_metrics":
                await self._handle_gateway_metrics(data)
            else:
                self.logger.warning(f"Unknown message type '{message_type}' from RLA ECM {client_id}")
                
        except Exception as e:
            self.logger.error(f"Error processing message from RLA ECM {client_id}: {e}")
    
    async def _handle_heartbeat(self, data: Dict[str, Any], client_id: str):
        """Handle heartbeat from RLA ECM."""
        # Send heartbeat response
        response = {
            "type": "heartbeat_response",
            "timestamp": datetime.now().isoformat(),
            "server": "RLAIM",
            "client_id": client_id
        }
        
        if client_id in self.connected_clients:
            try:
                await self.connected_clients[client_id]["websocket"].send(json.dumps(response))
            except Exception as e:
                self.logger.error(f"Failed to send heartbeat response to {client_id}: {e}")
    
    async def stop_websocket_connection(self):
        """Stop WebSocket connection to RLA."""
        try:
            if self.websocket_task:
                self.websocket_task.cancel()
                try:
                    await self.websocket_task
                except asyncio.CancelledError:
                    pass
                self.websocket_task = None
            
            if self.websocket:
                await self.websocket.close()
                self.websocket = None
            
            self.is_connected = False
            self.logger.info("WebSocket connection to RLA stopped")
            
        except Exception as e:
            self.logger.error(f"Failed to stop WebSocket connection: {e}")
    
    async def _websocket_client(self):
        """WebSocket client for RLA communication."""
        reconnect_attempts = 0
        max_reconnect_attempts = 10
        
        while self.is_active:
            try:
                ws_url = f"ws://{self.rla_config['host']}:{self.rla_config['ports']['websocket']}{self.rla_config['websocket_path']}"
                
                self.logger.info(f"Connecting to RLA WebSocket at {ws_url}")
                self.stats["connection_attempts"] += 1
                
                async with websockets.connect(ws_url) as websocket:
                    self.websocket = websocket
                    self.is_connected = True
                    self.stats["successful_connections"] += 1
                    self.stats["last_connection"] = datetime.now()
                    
                    self.logger.info("Connected to RLA WebSocket")
                    
                    # Send initial handshake
                    await self._send_handshake()
                    
                    # Listen for messages
                    async for message in websocket:
                        await self._handle_message(message)
                        
            except websockets.exceptions.ConnectionClosed:
                self.logger.warning("RLA WebSocket connection closed")
            except Exception as e:
                self.logger.error(f"RLA WebSocket error: {e}")
                self.stats["connection_failures"] += 1
                
                # Reconnect logic
                reconnect_attempts += 1
                if reconnect_attempts <= max_reconnect_attempts:
                    wait_time = min(2 ** reconnect_attempts, 60)
                    self.logger.info(f"Reconnecting to RLA in {wait_time} seconds (attempt {reconnect_attempts})")
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error("Max reconnection attempts reached")
                    break
            finally:
                self.is_connected = False
                self.stats["last_disconnection"] = datetime.now()
                self.websocket = None
    
    async def _send_handshake(self):
        """Send initial handshake to RLA."""
        try:
            handshake = {
                "type": "ccu_handshake",
                "timestamp": datetime.now().isoformat(),
                "ccu_version": "1.0.0",
                "supported_protocols": ["websocket", "http"],
                "capabilities": [
                    "monitoring",
                    "configuration_management",
                    "command_execution",
                    "alert_handling"
                ]
            }
            
            await self._send_message(handshake)
            self.logger.info("Handshake sent to RLA")
            
        except Exception as e:
            self.logger.error(f"Failed to send handshake: {e}")
    
    async def _send_message(self, message: Dict[str, Any]):
        """Send a message to RLA."""
        try:
            if self.websocket and self.is_connected:
                message_json = json.dumps(message)
                await self.websocket.send(message_json)
                self.stats["total_messages_sent"] += 1
                
        except Exception as e:
            self.logger.error(f"Failed to send message to RLA: {e}")
            raise
    
    async def _handle_message(self, message: str):
        """Handle incoming message from RLA."""
        try:
            data = json.loads(message)
            self.stats["total_messages_received"] += 1
            
            message_type = data.get("type")
            
            if message_type == "service_registration":
                await self._handle_service_registration(data)
            elif message_type == "status_update":
                await self._handle_status_update(data)
            elif message_type == "health_report":
                await self._handle_health_report(data)
            elif message_type == "alert":
                await self._handle_alert(data)
            elif message_type == "error_report":
                await self._handle_error_report(data)
            elif message_type == "module_status":
                await self._handle_module_status(data)
            elif message_type == "gateway_metrics":
                await self._handle_gateway_metrics(data)
            else:
                self.logger.warning(f"Unknown message type from RLA: {message_type}")
                
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON message from RLA: {message}")
        except Exception as e:
            self.logger.error(f"Error handling RLA message: {e}")
    
    async def _handle_service_registration(self, data: Dict[str, Any]):
        """Handle service registration from RLA."""
        try:
            self.logger.info(f"RLA service registered: {data}")
            
            # Update RLA status
            self.rla_status.service = data.get("service", "RLA")
            self.rla_status.is_active = True
            self.rla_status.last_update = datetime.now()
            
            # Update gateway metrics
            endpoints = data.get("endpoints", {})
            self.gateway_metrics["activation_port"] = endpoints.get("activation", 3812)
            self.gateway_metrics["data_port"] = endpoints.get("data", 3781)
            self.gateway_metrics["health_port"] = endpoints.get("health", 9090)
            
            self.logger.info("RLA service registration processed")
            
        except Exception as e:
            self.logger.error(f"Error handling service registration: {e}")
    
    async def _handle_status_update(self, data: Dict[str, Any]):
        """Handle status update from RLA."""
        try:
            status = data.get("status", {})
            
            # Update RLA status
            self.rla_status.total_requests = status.get("total_requests", 0)
            self.rla_status.validated_requests = status.get("validated_requests", 0)
            self.rla_status.rejected_requests = status.get("rejected_requests", 0)
            self.rla_status.average_processing_time = status.get("average_processing_time", 0.0)
            self.rla_status.modules = status.get("modules", {})
            self.rla_status.last_update = datetime.now()
            
            # Update gateway metrics
            self.gateway_metrics["current_connections"] = status.get("active_connections", 0)
            self.gateway_metrics["throughput_rps"] = status.get("throughput_rps", 0.0)
            
            self.logger.debug(f"RLA status updated: {status}")
            
        except Exception as e:
            self.logger.error(f"Error handling status update: {e}")
    
    async def _handle_health_report(self, data: Dict[str, Any]):
        """Handle health report from RLA."""
        try:
            modules = data.get("modules", {})
            
            # Update module status
            for module_name, module_data in modules.items():
                if module_name in self.rla_modules:
                    self.rla_modules[module_name]["status"] = "healthy" if module_data.get("healthy", False) else "unhealthy"
                    self.rla_modules[module_name]["last_check"] = datetime.now()
                    
                    # Store additional module data
                    self.rla_modules[module_name]["data"] = module_data
            
            self.logger.debug(f"RLA health report processed: {len(modules)} modules")
            
        except Exception as e:
            self.logger.error(f"Error handling health report: {e}")
    
    async def _handle_alert(self, data: Dict[str, Any]):
        """Handle alert from RLA."""
        try:
            alert_type = data.get("alert_type")
            message = data.get("message")
            severity = data.get("severity", "info")
            
            self.logger.warning(f"RLA Alert [{severity}] {alert_type}: {message}")
            
            # Update gateway metrics based on alert type
            if alert_type == "limit_violation":
                self.gateway_metrics["limit_violations"] += 1
            elif alert_type == "spam_detection":
                self.gateway_metrics["spam_detections"] += 1
            elif alert_type == "security_threat":
                self.gateway_metrics["security_threats"] += 1
            elif alert_type == "validation_failure":
                self.gateway_metrics["validation_failures"] += 1
            
        except Exception as e:
            self.logger.error(f"Error handling alert: {e}")
    
    async def _handle_error_report(self, data: Dict[str, Any]):
        """Handle error report from RLA."""
        try:
            error = data.get("error")
            context = data.get("context", "")
            
            self.logger.error(f"RLA Error Report: {error} (Context: {context})")
            
        except Exception as e:
            self.logger.error(f"Error handling error report: {e}")
    
    async def _handle_module_status(self, data: Dict[str, Any]):
        """Handle individual module status update."""
        try:
            module_name = data.get("module")
            module_status = data.get("status")
            
            if module_name in self.rla_modules:
                self.rla_modules[module_name]["status"] = module_status
                self.rla_modules[module_name]["last_check"] = datetime.now()
                self.rla_modules[module_name]["data"] = data
                
                self.logger.debug(f"RLA module {module_name} status: {module_status}")
            
        except Exception as e:
            self.logger.error(f"Error handling module status: {e}")
    
    async def _handle_gateway_metrics(self, data: Dict[str, Any]):
        """Handle gateway metrics update."""
        try:
            metrics = data.get("metrics", {})
            
            # Update gateway metrics
            self.gateway_metrics.update(metrics)
            
            self.logger.debug(f"Gateway metrics updated: {metrics}")
            
        except Exception as e:
            self.logger.error(f"Error handling gateway metrics: {e}")
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeat to RLA."""
        while self.is_active:
            try:
                if self.is_connected:
                    heartbeat = {
                        "type": "heartbeat",
                        "timestamp": datetime.now().isoformat(),
                        "ccu_status": "active"
                    }
                    
                    await self._send_message(heartbeat)
                
                await asyncio.sleep(30)  # Send heartbeat every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(30)
    
    async def send_command(self, command: str, parameters: Dict[str, Any] = None) -> bool:
        """Send a command to RLA ECM client."""
        try:
            if not self.connected_clients:
                self.logger.warning("Cannot send command - no RLA ECM clients connected")
                return False
            
            command_message = {
                "type": "command",
                "command": command,
                "parameters": parameters or {},
                "timestamp": datetime.now().isoformat(),
                "request_id": f"cmd_{int(datetime.now().timestamp())}",
                "from": "CCU_RLAIM"
            }
            
            # Send to all connected RLA clients (should be only 1)
            success_count = 0
            for client_id, client_info in self.connected_clients.items():
                try:
                    websocket = client_info["websocket"]
                    await websocket.send(json.dumps(command_message))
                    success_count += 1
                    self.logger.info(f"📤 Command '{command}' sent to RLA ECM client {client_id}")
                except Exception as e:
                    self.logger.error(f"❌ Failed to send command to RLA client {client_id}: {e}")
            
            return success_count > 0
            
        except Exception as e:
            self.logger.error(f"❌ Error sending command '{command}' to RLA: {e}")
            return False
    
    async def request_status(self) -> Dict[str, Any]:
        """Request current status from RLA."""
        try:
            if not self.is_connected:
                return {"error": "Not connected to RLA"}
            
            status_request = {
                "type": "status_request",
                "timestamp": datetime.now().isoformat(),
                "request_id": f"status_{int(datetime.now().timestamp())}"
            }
            
            await self._send_message(status_request)
            return {"status": "requested"}
            
        except Exception as e:
            self.logger.error(f"Error requesting status from RLA: {e}")
            return {"error": str(e)}
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status from RLA via HTTP."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.rla_config["endpoints"]["health"]) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {"error": f"Health check failed with status {response.status}"}
                        
        except Exception as e:
            self.logger.error(f"Error getting health status from RLA: {e}")
            return {"error": str(e)}
    
    async def adjust_limits(self, word_limit: int = None, token_limit: int = None) -> bool:
        """Adjust RLA limits."""
        try:
            parameters = {}
            if word_limit is not None:
                parameters["word_limit"] = word_limit
            if token_limit is not None:
                parameters["token_limit"] = token_limit
            
            return await self.send_command("adjust_limits", parameters)
            
        except Exception as e:
            self.logger.error(f"Error adjusting RLA limits: {e}")
            return False
    
    async def block_input_gateway(self) -> bool:
        """Block RLA input gateway to prevent new requests."""
        try:
            return await self.send_command("block_gateway")
        except Exception as e:
            self.logger.error(f"Error blocking RLA input gateway: {e}")
            return False
    
    async def unblock_input_gateway(self) -> bool:
        """Unblock RLA input gateway to allow new requests."""
        try:
            return await self.send_command("unblock_gateway")
        except Exception as e:
            self.logger.error(f"Error unblocking RLA input gateway: {e}")
            return False
    
    async def reload_configuration(self) -> bool:
        """Request RLA to reload its configuration."""
        try:
            return await self.send_command("reload_config")
            
        except Exception as e:
            self.logger.error(f"Error reloading RLA configuration: {e}")
            return False
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get comprehensive service status."""
        return {
            "service_name": self.service_name,
            "is_connected": self.is_connected,
            "is_active": self.rla_status.is_active,
            "last_update": self.rla_status.last_update.isoformat() if self.rla_status.last_update else None,
            "total_requests": self.rla_status.total_requests,
            "validated_requests": self.rla_status.validated_requests,
            "rejected_requests": self.rla_status.rejected_requests,
            "average_processing_time": self.rla_status.average_processing_time,
            "modules": self.rla_modules,
            "gateway_metrics": self.gateway_metrics,
            "connection_stats": self.stats
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the RLAIM module."""
        return {
            "module": self.module_name,
            "is_active": self.is_active,
            "is_connected": self.is_connected,
            "service": self.service_name,
            "last_update": self.rla_status.last_update.isoformat() if self.rla_status.last_update else None,
            "module_count": len(self.rla_modules),
            "healthy_modules": len([m for m in self.rla_modules.values() if m["status"] == "healthy"]),
            "stats": self.stats
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            # Check WebSocket connection
            websocket_healthy = self.is_connected
            
            # Check if RLA is responding
            rla_healthy = False
            if self.is_connected:
                try:
                    health_data = await self.get_health_status()
                    rla_healthy = health_data.get("healthy", False)
                except:
                    rla_healthy = False
            
            # Check module health
            healthy_modules = len([m for m in self.rla_modules.values() if m["status"] == "healthy"])
            total_modules = len(self.rla_modules)
            
            overall_healthy = websocket_healthy and rla_healthy and (healthy_modules > total_modules * 0.8)
            
            return {
                "healthy": overall_healthy,
                "module": self.module_name,
                "timestamp": datetime.now().isoformat(),
                "details": {
                    "websocket_connected": websocket_healthy,
                    "rla_responsive": rla_healthy,
                    "healthy_modules": healthy_modules,
                    "total_modules": total_modules,
                    "module_health_ratio": healthy_modules / total_modules if total_modules > 0 else 0
                }
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "module": self.module_name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            } 