"""
RCM Interaction Module (RCMIM)

This module serves as the adapter between the CCU and the RCM microservice.
It implements the Adapter Pattern to decouple the CCU's core orchestration logic
from the specific implementation details of the RCM microservice.

Key Responsibilities:
- Start WebSocket SERVER for RCM ECM connections (NEW ARCHITECTURE)
- Accept connections from RCM ECM module 
- Send commands and receive responses from RCM
- Monitor RCM health and performance
- Handle RCM-specific error conditions
- Manage RCM configuration updates
- Stream real-time logs and monitoring data from RCM

Architecture: CCU runs WebSocket servers, microservices connect as clients
Based on RCM_CONFIGURATION_PLAN.md specifications for CCU integration.
"""

import asyncio
import logging
import json
import websockets
import requests
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import threading
import queue
import time
import sys

# Add utils path for WebSocketPortManager
sys.path.append(str(Path(__file__).parent.parent / "utils"))
from websocket_port_manager import WebSocketPortManager


class RCMConnectionStatus(Enum):
    """RCM connection status."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    RECONNECTING = "reconnecting"


class RCMStatus(Enum):
    """RCM service status."""
    INACTIVE = "inactive"
    ACTIVE = "active"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class RCMInteractionModule:
    """
    RCM Interaction Module (RCMIM)
    
    Manages all interactions with the RCM microservice including:
    - Service lifecycle management
    - Command/response communication
    - Real-time monitoring and logging
    - Configuration management
    - Error handling and recovery
    """
    
    def __init__(self, ccu_config: Dict[str, Any] = None):
        """Initialize the RCMIM module."""
        self.logger = logging.getLogger(__name__)
        
        # Use WebSocket port manager from CCU config (shared instance)
        self.port_manager = ccu_config.get('websocket_port_manager') if ccu_config else None
        if not self.port_manager:
            # Fallback to creating new instance if not provided
            self.port_manager = WebSocketPortManager()
            self.logger.warning("No WebSocket port manager provided, creating new instance")
        
        # Load RCM configuration from CCU (includes PMM paths and network config)
        rcm_setting = ccu_config.get('rcm_setting', {}) if ccu_config else {}
        
        # Legacy HTTP API configuration (still needed for health checks)
        self.rcm_host = rcm_setting.get("host", "localhost")
        self.rcm_port = rcm_setting.get("ports", {}).get("api", 8080)
        self.rcm_base_url = f"http://{self.rcm_host}:{self.rcm_port}"
        
        # NEW ARCHITECTURE: WebSocket SERVER configuration 
        self.websocket_server = None
        self.websocket_server_port = None
        self.connected_clients = {}  # Track RCM ECM connections
        
        # Connection state
        self.connection_status = RCMConnectionStatus.DISCONNECTED
        self.last_heartbeat = None
        self.max_clients = 1  # Only one RCM ECM should connect
        
        # RCM service state
        self.rcm_status = RCMStatus.INACTIVE
        self.rcm_modules_status = {}
        self.rcm_performance_metrics = {}
        
        # Message handling
        self.message_queue = asyncio.Queue()
        self.response_callbacks = {}
        self.request_id_counter = 0
        
        # Monitoring
        self.monitoring_callbacks = []
        self.log_callbacks = []
        self.error_callbacks = []
        
        # Statistics
        self.stats = {
            "total_commands_sent": 0,
            "total_responses_received": 0,
            "total_errors": 0,
            "connection_uptime": 0,
            "last_activity": None
        }
        
        self.logger.info("RCMIM module initialized")
    
    async def start(self):
        """Start the RCMIM module with WebSocket server."""
        try:
            self.logger.info("Starting RCMIM module with WebSocket server...")
            
            # Start WebSocket server for RCM ECM connections
            await self.start_websocket_server()
            
            # Start background tasks
            asyncio.create_task(self.heartbeat_monitor())
            asyncio.create_task(self.message_processor())
            asyncio.create_task(self.connection_monitor())
            
            self.logger.info(f"✅ RCMIM module started successfully with WebSocket server on port {self.websocket_server_port}")
            
        except Exception as e:
            self.logger.error(f"Failed to start RCMIM module: {e}")
            raise
    
    async def stop(self):
        """Stop the RCMIM module and WebSocket server."""
        try:
            self.logger.info("Stopping RCMIM module...")
            
            # Close all client connections
            for client_id, client_info in list(self.connected_clients.items()):
                try:
                    websocket = client_info["websocket"]
                    await websocket.close()
                    self.logger.info(f"Closed connection to RCM ECM client {client_id}")
                except Exception as e:
                    self.logger.error(f"Error closing client {client_id}: {e}")
            
            self.connected_clients.clear()
            
            # Close WebSocket server
            if self.websocket_server:
                self.websocket_server.close()
                await self.websocket_server.wait_closed()
                self.logger.info(f"RCMIM WebSocket server stopped on port {self.websocket_server_port}")
            
            self.connection_status = RCMConnectionStatus.DISCONNECTED
            
            self.logger.info("✅ RCMIM module stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to stop RCMIM module: {e}")
            raise
    
    async def start_websocket_server(self):
        """Start WebSocket server for RCM ECM connections."""
        try:
            self.connection_status = RCMConnectionStatus.CONNECTING
            self.logger.info("Starting RCMIM WebSocket server...")
            
            # Start WebSocket server using port manager
            self.websocket_server = await self.port_manager.start_ccu_websocket_server(
                "RCMIM", 
                self.handle_rcm_connection
            )
            
            if not self.websocket_server:
                raise Exception("Failed to start WebSocket server - no available ports")
            
            # Get the allocated port
            self.websocket_server_port = self.port_manager.allocated_ports.get("RCMIM")
            
            self.connection_status = RCMConnectionStatus.CONNECTED
            self.logger.info(f"✅ RCMIM WebSocket server started on port {self.websocket_server_port}")
            self.logger.info(f"🔗 RCM ECM should connect to: ws://localhost:{self.websocket_server_port}/ws")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start RCMIM WebSocket server: {e}")
            self.connection_status = RCMConnectionStatus.ERROR
            raise
    
    async def handle_rcm_connection(self, websocket, path):
        """Handle incoming RCM ECM WebSocket connection."""
        try:
            client_id = f"RCM_ECM_{id(websocket)}"
            client_address = websocket.remote_address
            self.logger.info(f"🔗 RCM ECM connected from {client_address} (ID: {client_id})")
            
            # Check if we already have max connections
            if len(self.connected_clients) >= self.max_clients:
                self.logger.warning(f"⚠️ Maximum RCM connections ({self.max_clients}) reached, rejecting new connection")
                await websocket.close(code=1008, reason="Maximum connections reached")
                return
            
            # Add client to connected clients
            self.connected_clients[client_id] = {
                "websocket": websocket,
                "connected_at": datetime.now(),
                "last_heartbeat": datetime.now(),
                "client_address": client_address
            }
            
            self.logger.info(f"✅ RCM ECM client registered (Total clients: {len(self.connected_clients)})")
            
            # Send welcome message
            welcome_msg = {
                "type": "welcome",
                "client_id": client_id,
                "server": "RCMIM",
                "timestamp": datetime.now().isoformat(),
                "message": "Connected to CCU RCMIM WebSocket server"
            }
            await websocket.send(json.dumps(welcome_msg))
            
            # Listen for messages from this RCM ECM client
            await self.handle_client_messages(websocket, client_id)
            
        except Exception as e:
            self.logger.error(f"❌ Error handling RCM connection: {e}")
        finally:
            # Clean up client connection
            if client_id in self.connected_clients:
                del self.connected_clients[client_id]
                self.logger.info(f"🔌 RCM ECM client {client_id} disconnected (Remaining: {len(self.connected_clients)})")

    async def handle_client_messages(self, websocket, client_id: str):
        """Handle messages from a specific RCM ECM client."""
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    
                    # Update last heartbeat
                    if client_id in self.connected_clients:
                        self.connected_clients[client_id]["last_heartbeat"] = datetime.now()
                    
                    # Handle the message
                    await self.handle_rcm_message(data, client_id)
                    
                except json.JSONDecodeError as e:
                    self.logger.error(f"Invalid JSON message from RCM client {client_id}: {e}")
                    error_response = {
                        "type": "error",
                        "error": "invalid_json",
                        "message": str(e),
                        "timestamp": datetime.now().isoformat()
                    }
                    await websocket.send(json.dumps(error_response))
                    
                except Exception as e:
                    self.logger.error(f"Error handling message from RCM client {client_id}: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"RCM ECM client {client_id} disconnected")
        except Exception as e:
            self.logger.error(f"Error in client message handler for {client_id}: {e}")
    
    async def handle_rcm_message(self, data: Dict[str, Any], client_id: str = None):
        """Handle incoming message from RCM."""
        try:
            message_type = data.get('type')
            
            if message_type == 'response':
                await self.handle_command_response(data)
            elif message_type == 'log':
                await self.handle_log_message(data)
            elif message_type == 'monitoring':
                await self.handle_monitoring_data(data)
            elif message_type == 'error':
                await self.handle_error_message(data)
            elif message_type == 'heartbeat':
                await self.handle_heartbeat(data)
            else:
                self.logger.warning(f"Unknown message type from RCM: {message_type}")
            
            self.stats['total_responses_received'] += 1
            self.stats['last_activity'] = datetime.now()
            
        except Exception as e:
            self.logger.error(f"Error handling RCM message: {e}")
    
    async def handle_command_response(self, data: Dict[str, Any]):
        """Handle command response from RCM."""
        request_id = data.get('request_id')
        
        if request_id and request_id in self.response_callbacks:
            callback = self.response_callbacks.pop(request_id)
            await callback(data)
    
    async def handle_log_message(self, data: Dict[str, Any]):
        """Handle log message from RCM."""
        # Forward to registered log callbacks
        for callback in self.log_callbacks:
            try:
                await callback(data)
            except Exception as e:
                self.logger.error(f"Error in log callback: {e}")
    
    async def handle_monitoring_data(self, data: Dict[str, Any]):
        """Handle monitoring data from RCM."""
        # Update performance metrics
        self.rcm_performance_metrics = data.get('metrics', {})
        
        # Forward to registered monitoring callbacks
        for callback in self.monitoring_callbacks:
            try:
                await callback(data)
            except Exception as e:
                self.logger.error(f"Error in monitoring callback: {e}")
    
    async def handle_error_message(self, data: Dict[str, Any]):
        """Handle error message from RCM."""
        self.stats['total_errors'] += 1
        
        # Forward to registered error callbacks
        for callback in self.error_callbacks:
            try:
                await callback(data)
            except Exception as e:
                self.logger.error(f"Error in error callback: {e}")
    
    async def handle_heartbeat(self, data: Dict[str, Any]):
        """Handle heartbeat message from RCM."""
        self.last_heartbeat = datetime.now()
        
        # Update RCM status
        self.rcm_status = RCMStatus(data.get('status', 'unknown'))
        self.rcm_modules_status = data.get('modules', {})
    
    async def send_command(self, command: str, parameters: Dict[str, Any] = None, timeout: float = 30.0) -> Dict[str, Any]:
        """
        Send a command to RCM and wait for response.
        
        Args:
            command: Command name
            parameters: Command parameters
            timeout: Response timeout in seconds
            
        Returns:
            Command response
        """
        try:
            if self.connection_status != RCMConnectionStatus.CONNECTED:
                raise Exception("Not connected to RCM")
            
            # Generate request ID
            request_id = f"rcm_cmd_{self.request_id_counter}"
            self.request_id_counter += 1
            
            # Prepare command message
            message = {
                "command": command,
                "parameters": parameters or {},
                "request_id": request_id,
                "timestamp": datetime.now().isoformat()
            }
            
            # Set up response callback
            response_future = asyncio.Future()
            
            async def response_callback(data):
                if not response_future.done():
                    response_future.set_result(data)
            
            self.response_callbacks[request_id] = response_callback
            
            # Get the first (and should be only) connected RCM client
            if not self.connected_clients:
                raise Exception("No RCM ECM clients connected")
                
            client_id = list(self.connected_clients.keys())[0]
            client_info = self.connected_clients[client_id]
            websocket = client_info["websocket"]
            
            # Send command to RCM ECM client
            message["type"] = "command"
            message["from"] = "CCU_RCMIM"
            await websocket.send(json.dumps(message))
            
            self.stats['total_commands_sent'] += 1
            self.stats['last_activity'] = datetime.now()
            
            self.logger.info(f"Sent command {command} to RCM with request_id {request_id}")
            
            # Wait for response
            try:
                response = await asyncio.wait_for(response_future, timeout=timeout)
                return response
            except asyncio.TimeoutError:
                # Clean up callback
                if request_id in self.response_callbacks:
                    del self.response_callbacks[request_id]
                raise Exception(f"Command {command} timed out after {timeout} seconds")
            
        except Exception as e:
            self.logger.error(f"Error sending command {command} to RCM: {e}")
            raise
    
    # RCM Service Control Commands
    async def activate_rcm(self) -> Dict[str, Any]:
        """Activate RCM service."""
        return await self.send_command("activate")
    
    async def deactivate_rcm(self) -> Dict[str, Any]:
        """Deactivate RCM service."""
        return await self.send_command("deactivate")
    
    async def send_activation_command(self) -> Dict[str, Any]:
        """Send activation command to RCM ECM (Two-Phase Activation)."""
        try:
            self.logger.info("📡 Sending activation command to RCM (Two-Phase Activation)")
            
            activation_message = {
                "type": "activation",
                "command": "activate_gateway",
                "message": "CCU is requesting RCM to activate its gateway for request processing",
                "timestamp": datetime.now().isoformat(),
                "from": "CCU_RCMIM",
                "phase": "gateway_activation"
            }
            
            if not self.connected_clients:
                raise Exception("No RCM ECM clients connected for activation")
            
            # Send to all connected RCM clients (should be only 1)
            results = []
            for client_id, client_info in self.connected_clients.items():
                try:
                    websocket = client_info["websocket"]
                    await websocket.send(json.dumps(activation_message))
                    self.logger.info(f"✅ Activation command sent to RCM ECM client {client_id}")
                    results.append({"client_id": client_id, "status": "sent"})
                except Exception as e:
                    self.logger.error(f"❌ Failed to send activation to client {client_id}: {e}")
                    results.append({"client_id": client_id, "status": "failed", "error": str(e)})
            
            return {"activation_command_sent": True, "results": results}
            
        except Exception as e:
            self.logger.error(f"❌ Failed to send activation command to RCM: {e}")
            return {"activation_command_sent": False, "error": str(e)}
    
    async def get_rcm_status(self) -> Dict[str, Any]:
        """Get RCM service status."""
        return await self.send_command("status")
    
    # RCM Configuration Commands
    async def set_rcm_api_key(self, api_key: str, module: str = None) -> Dict[str, Any]:
        """Set API key for RCM modules."""
        parameters = {"api_key": api_key}
        if module:
            parameters["module"] = module
        return await self.send_command("set_api_key", parameters)
    
    async def set_rcm_rate_limit(self, requests_per_minute: int, requests_per_second: int = 1, module: str = "BAAIM") -> Dict[str, Any]:
        """Configure rate limiting for RCM."""
        parameters = {
            "requests_per_minute": requests_per_minute,
            "requests_per_second": requests_per_second,
            "module": module
        }
        return await self.send_command("set_rate_limit", parameters)
    
    async def set_rcm_port(self, port: int, module: str = "FAIM") -> Dict[str, Any]:
        """Set port for RCM API modules."""
        parameters = {"port": port, "module": module}
        return await self.send_command("set_port", parameters)
    
    # RCM Testing Commands
    async def run_rcm_test(self, test_code: str) -> Dict[str, Any]:
        """Run specific RCM test."""
        return await self.send_command("run_test", {"test_code": test_code})
    
    async def run_rcm_test_suite(self, test_range: str = "T0000001-T0000049") -> Dict[str, Any]:
        """Run RCM test suite."""
        return await self.send_command("run_test_suite", {"test_range": test_range})
    
    # RCM Database Commands
    async def execute_rcm_db_query(self, query: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute database query on RCM."""
        parameters = {"query": query, "params": params or {}}
        return await self.send_command("db_query", parameters)
    
    async def backup_rcm_database(self, backup_name: str = None) -> Dict[str, Any]:
        """Create RCM database backup."""
        backup_name = backup_name or f"rcm_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return await self.send_command("db_backup", {"backup_name": backup_name})
    
    # RCM System Commands
    async def inject_rcm_system_message(self, message: str, priority: str = "NORMAL") -> Dict[str, Any]:
        """Inject system message into RCM."""
        parameters = {"message": message, "priority": priority}
        return await self.send_command("inject_system_message", parameters)
    
    async def switch_rcm_model(self, model: str, module: str = "BAAIM") -> Dict[str, Any]:
        """Switch AI model for RCM."""
        parameters = {"model": model, "module": module}
        return await self.send_command("switch_model", parameters)
    
    async def get_rcm_errors(self, since: str = None, severity: str = None) -> Dict[str, Any]:
        """Get RCM error logs."""
        parameters = {}
        if since:
            parameters["since"] = since
        if severity:
            parameters["severity"] = severity
        return await self.send_command("get_errors", parameters)
    
    async def get_rcm_monitoring(self, metrics: List[str] = None, timeframe: str = "1h") -> Dict[str, Any]:
        """Get RCM monitoring data."""
        parameters = {"timeframe": timeframe}
        if metrics:
            parameters["metrics"] = metrics
        return await self.send_command("get_monitoring", parameters)
    
    # RCM Reset Commands
    async def reset_rcm_module(self, module: str) -> Dict[str, Any]:
        """Reset specific RCM module."""
        return await self.send_command("reset_module", {"module": module})
    
    async def reset_rcm_all(self) -> Dict[str, Any]:
        """Reset all RCM modules."""
        return await self.send_command("reset_all")
    
    # Request Processing
    async def process_request_via_rcm(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a request through RCM."""
        return await self.send_command("process_request", request_data)
    
    async def get_request_status(self, request_id: str) -> Dict[str, Any]:
        """Get status of a request being processed by RCM."""
        return await self.send_command("get_request_status", {"request_id": request_id})
    
    # Callback registration
    def register_monitoring_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Register callback for monitoring data."""
        self.monitoring_callbacks.append(callback)
    
    def register_log_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Register callback for log messages."""
        self.log_callbacks.append(callback)
    
    def register_error_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Register callback for error messages."""
        self.error_callbacks.append(callback)
    
    # Background tasks
    async def heartbeat_monitor(self):
        """Monitor RCM heartbeat."""
        while True:
            try:
                if self.connection_status == RCMConnectionStatus.CONNECTED:
                    if self.last_heartbeat:
                        time_since_heartbeat = (datetime.now() - self.last_heartbeat).total_seconds()
                        
                        if time_since_heartbeat > 60:  # 1 minute timeout
                            self.logger.warning("RCM heartbeat timeout detected")
                            self.connection_status = RCMConnectionStatus.ERROR
                            
                            # Attempt reconnection
                            await self.connect_to_rcm()
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in heartbeat monitor: {e}")
                await asyncio.sleep(30)
    
    async def message_processor(self):
        """Process queued messages."""
        while True:
            try:
                # Process any queued messages
                if not self.message_queue.empty():
                    message = await self.message_queue.get()
                    await self.handle_rcm_message(message)
                
                await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
                
            except Exception as e:
                self.logger.error(f"Error in message processor: {e}")
                await asyncio.sleep(1)
    
    async def connection_monitor(self):
        """Monitor connection status and attempt reconnection."""
        while True:
            try:
                if self.connection_status == RCMConnectionStatus.ERROR:
                    self.logger.info("Attempting to reconnect to RCM...")
                    await self.connect_to_rcm()
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                self.logger.error(f"Error in connection monitor: {e}")
                await asyncio.sleep(10)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the RCMIM module."""
        return {
            'module': 'RCMIM',
            'connection_status': self.connection_status.value,
            'rcm_status': self.rcm_status.value,
            'rcm_modules_status': self.rcm_modules_status,
            'rcm_performance_metrics': self.rcm_performance_metrics,
            'reconnect_attempts': self.reconnect_attempts,
            'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            'stats': self.stats
        }
    
    def is_connected(self) -> bool:
        """Check if connected to RCM."""
        return self.connection_status == RCMConnectionStatus.CONNECTED
    
    def is_rcm_active(self) -> bool:
        """Check if RCM service is active."""
        return self.rcm_status == RCMStatus.ACTIVE
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            if not self.is_connected():
                return {
                    'healthy': False,
                    'error': 'Not connected to RCM',
                    'connection_status': self.connection_status.value
                }
            
            # Try to get status from RCM
            status_response = await self.get_rcm_status()
            
            return {
                'healthy': True,
                'connection_status': self.connection_status.value,
                'rcm_status': status_response
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e),
                'connection_status': self.connection_status.value
            }
    
    async def get_rcm_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive status information from RCM."""
        try:
            # Get basic status
            status = await self.get_rcm_status()
            
            # Get monitoring data
            monitoring = await self.get_rcm_monitoring()
            
            # Get recent errors
            errors = await self.get_rcm_errors(since=(datetime.now() - timedelta(hours=1)).isoformat())
            
            return {
                'status': status,
                'monitoring': monitoring,
                'errors': errors,
                'connection_info': {
                    'connection_status': self.connection_status.value,
                    'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None,
                    'reconnect_attempts': self.reconnect_attempts
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting comprehensive RCM status: {e}")
            return {
                'error': str(e),
                'connection_status': self.connection_status.value
            }
    
    async def insufficient_data_message_sender(self, insufficient_data_recognition: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate insufficient data message for system injection.
        
        Args:
            insufficient_data_recognition: Recognition data from JFA
            
        Returns:
            Formatted message for system injection
        """
        try:
            request_id = insufficient_data_recognition.get("request_id", "unknown")
            missing_data = insufficient_data_recognition.get("missing_data", [])
            insufficient_data = insufficient_data_recognition.get("insufficient_data", [])
            
            # Combine missing and insufficient data
            all_missing_info = missing_data + insufficient_data
            
            if not all_missing_info:
                return {
                    "success": False,
                    "error": "No missing or insufficient data found",
                    "request_id": request_id
                }
            
            # Format the message
            message_lines = ["The data that you send are not enough you miss this information:"]
            
            for i, info in enumerate(all_missing_info, 1):
                message_lines.append(f"{i}. {info}")
            
            formatted_message = "\n".join(message_lines)
            
            result = {
                "success": True,
                "message": formatted_message,
                "request_id": request_id,
                "missing_count": len(missing_data),
                "insufficient_count": len(insufficient_data),
                "total_missing": len(all_missing_info),
                "timestamp": datetime.now().isoformat()
            }
            
            self.logger.info(f"RCMIM: Generated insufficient data message for request {request_id}")
            return result
            
        except Exception as e:
            error_msg = f"Error generating insufficient data message: {e}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "request_id": insufficient_data_recognition.get("request_id", "unknown")
            }
    
    async def invalid_data_message_sender(self, invalid_data_recognition: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate invalid data message for system injection.
        
        Args:
            invalid_data_recognition: Recognition data from JFA
            
        Returns:
            Formatted message for system injection
        """
        try:
            request_id = invalid_data_recognition.get("request_id", "unknown")
            invalid_parts = invalid_data_recognition.get("invalid_parts", [])
            
            if not invalid_parts:
                return {
                    "success": False,
                    "error": "No invalid data parts found",
                    "request_id": request_id
                }
            
            # Format the message
            message_lines = ["The data that you send are invalid you miss this parts:"]
            
            for i, part in enumerate(invalid_parts, 1):
                message_lines.append(f"{i}. {part}")
            
            formatted_message = "\n".join(message_lines)
            
            result = {
                "success": True,
                "message": formatted_message,
                "request_id": request_id,
                "invalid_parts_count": len(invalid_parts),
                "timestamp": datetime.now().isoformat()
            }
            
            self.logger.info(f"RCMIM: Generated invalid data message for request {request_id}")
            return result
            
        except Exception as e:
            error_msg = f"Error generating invalid data message: {e}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "request_id": invalid_data_recognition.get("request_id", "unknown")
            } 