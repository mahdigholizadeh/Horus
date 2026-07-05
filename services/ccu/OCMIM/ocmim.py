"""
OCM Interaction Module (OCMIM) for CCU

This module manages the complete integration between CCU and the OCM (Output Cache Management) 
microservice. It provides WebSocket-based communication, SSL certificate distribution, 
service control, monitoring, and comprehensive output processing coordination.

Key Responsibilities:
- WebSocket connection management with OCM's ECM module
- SSL/TLS certificate distribution and hot-reload
- Service control operations (start, stop, restart, configure)
- Real-time monitoring and health checks
- Output processing request coordination
- Priority-based request management
- Error handling and escalation
- Testing and validation coordination
"""

import asyncio
import logging
import json
import ssl
import websockets
import aiohttp
from typing import Dict, Any, Optional, List, Callable, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import sys
from pathlib import Path

# Add utils path for WebSocketPortManager
sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
from websocket_port_manager import WebSocketPortManager
import hashlib
import time

class OCMStatus(Enum):
    """OCM service connection status."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    ERROR = "error"
    TIMEOUT = "timeout"

class RequestPriority(Enum):
    """Request priority levels matching OCM."""
    A = "A"  # Highest priority
    B = "B"  # High priority  
    C = "C"  # Medium priority
    D = "D"  # Low priority

class CommandType(Enum):
    """Types of commands that can be sent to OCM."""
    SERVICE_CONTROL = "service_control"
    CONFIGURATION_UPDATE = "configuration_update"
    CERTIFICATE_UPDATE = "certificate_update"
    TEST_EXECUTION = "test_execution"
    DATABASE_QUERY = "database_query"
    MONITORING_REQUEST = "monitoring_request"
    RESET_COMMAND = "reset_command"
    REPORT_STATUS_QUERY = "report_status_query"
    PRIORITY_ADJUSTMENT = "priority_adjustment"
    OUTPUT_VALIDATION = "output_validation"
    HEALTH_CHECK = "health_check"

@dataclass
class OCMRequest:
    """OCM output processing request."""
    request_id: str
    priority: RequestPriority
    request_type: str
    source_module: str
    data: Dict[str, Any]
    created_at: datetime
    timeout_seconds: int = 300
    retry_attempts: int = 3
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class OCMResponse:
    """OCM processing response."""
    request_id: str
    status: str
    response_data: Dict[str, Any]
    processing_time_ms: int
    generated_reports: List[str] = None
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.generated_reports is None:
            self.generated_reports = []

class OCMInteractionModule:
    """
    OCM Interaction Module (OCMIM) for CCU
    
    Comprehensive integration module that manages all communication and coordination
    between CCU and the OCM microservice, including WebSocket communication,
    SSL certificate management, service control, and output processing.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the OCMIM module."""
        self.logger = logging.getLogger(__name__)
        self.module_name = "OCMIM"
        
        # Configuration (PMM-compatible)
        self.config = config or {}
        
        # Extract OCM configuration from CCU config (includes PMM paths)
        ocm_setting = self.config.get('ocm_setting', {})
        self.ocm_config = ocm_setting.get('ocm_integration', {})
        
        # If no ocm_integration found, use network config directly (PMM structure)
        if not self.ocm_config and 'network' in ocm_setting:
            self.ocm_config = ocm_setting.get('network', {})
        
        # Connection settings
        self.ocm_host = self.ocm_config.get('host', 'localhost')
        self.ocm_websocket_port = self.ocm_config.get('websocket_port', 47811)
        self.ocm_api_port = self.ocm_config.get('api_port', 47812)
        self.ccu_service_id = self.ocm_config.get('ccu_service_id', 'CCU_PRIMARY')
        
        # WebSocket connection
        self.websocket = None
        self.connection_status = OCMStatus.DISCONNECTED
        self.last_heartbeat = None
        self.heartbeat_interval = self.ocm_config.get('heartbeat_interval', 30)
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = self.ocm_config.get('max_reconnect_attempts', 10)
        
        # SSL certificate management
        self.certificate_manager = None  # Will be set by CCU
        self.ssl_certificates = {}
        
        # Request management
        self.pending_requests = {}  # request_id -> OCMRequest
        self.completed_requests = {}  # request_id -> OCMResponse
        self.request_timeout = self.ocm_config.get('request_timeout', 300)
        
        # Command tracking
        self.pending_commands = {}  # command_id -> command_info
        self.command_responses = {}  # command_id -> response
        
        # Monitoring and health
        self.ocm_health_status = None
        self.last_health_check = None
        self.performance_metrics = {}
        
        # Event handlers
        self.event_handlers = {
            'connection_established': [],
            'connection_lost': [],
            'request_completed': [],
            'error_occurred': [],
            'health_status_changed': []
        }
        
        # Statistics
        self.stats = {
            'total_requests_sent': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'connection_count': 0,
            'disconnection_count': 0,
            'certificate_updates': 0,
            'commands_sent': 0,
            'health_checks_performed': 0,
            'start_time': None,
            'last_activity': None
        }
        
        # Background tasks
        self.background_tasks = set()
        self.is_active = False
        
        
        # Use WebSocket port manager from CCU config (shared instance)
        self.port_manager = config.get('websocket_port_manager') if config else None
        if not self.port_manager:
            # Fallback to creating new instance if not provided
            self.port_manager = WebSocketPortManager()
            self.logger.warning("No WebSocket port manager provided, creating new instance")
        
        # NEW ARCHITECTURE: WebSocket SERVER configuration
        self.websocket_server = None
        self.websocket_server_port = None
        self.connected_clients = {}  # Track ECM connections
        self.max_clients = 1  # Only one ECM should connect
        self.logger.info(f"{self.module_name} initialized - OCM target: {self.ocm_host}:{self.ocm_websocket_port}")
    
    def set_certificate_manager(self, certificate_manager):
        """Set reference to CCU's certificate manager."""
        self.certificate_manager = certificate_manager
        self.logger.info("Certificate manager reference set")
    
    async def start(self):
        """Start the OCMIM module."""
        try:
            self.is_active = True
            
            # Start WebSocket server for ECM connections
            await self.start_websocket_server()
            self.stats['start_time'] = datetime.now().isoformat()
            
            self.logger.info("Starting OCMIM module")
            
            # Start background tasks
            self._start_background_tasks()
            
            # Attempt initial connection
            await self._connect_to_ocm()
            
            self.logger.info("OCMIM module started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start OCMIM module: {e}")
            raise
    async def start_websocket_server(self):
        """Start WebSocket server for OCM ECM connections."""
        try:
            self.logger.info("Starting OCMIM WebSocket server...")
            
            # Start WebSocket server using port manager
            self.websocket_server = await self.port_manager.start_ccu_websocket_server(
                "OCMIM", 
                self.handle_ocm_connection
            )
            
            if not self.websocket_server:
                raise Exception("Failed to start WebSocket server - no available ports")
            
            # Get the allocated port
            self.websocket_server_port = self.port_manager.allocated_ports.get("OCMIM")
            
            self.logger.info(f"✅ OCMIM WebSocket server started on port {self.websocket_server_port}")
            self.logger.info(f"🔗 OCM ECM should connect to: ws://localhost:{self.websocket_server_port}/ws")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start OCMIM WebSocket server: {e}")
            raise
    
    async def handle_ocm_connection(self, websocket, path):
        """Handle incoming OCM ECM WebSocket connection."""
        client_id = None
        try:
            client_id = f"OCM_ECM_{id(websocket)}"
            client_address = websocket.remote_address
            self.logger.info(f"🔗 OCM ECM connected from {client_address} (ID: {client_id})")
            
            # Check if we already have max connections
            if len(self.connected_clients) >= self.max_clients:
                self.logger.warning(f"⚠️ Maximum OCM connections ({self.max_clients}) reached, rejecting new connection")
                await websocket.close(code=1008, reason="Maximum connections reached")
                return
            
            # Add client to connected clients
            self.connected_clients[client_id] = {
                "websocket": websocket,
                "connected_at": datetime.now(),
                "last_heartbeat": datetime.now(),
                "client_address": client_address
            }
            
            self.logger.info(f"✅ OCM ECM client registered (Total clients: {len(self.connected_clients)})")
            
            # Send welcome message
            welcome_msg = {
                "type": "welcome",
                "client_id": client_id,
                "server": "OCMIM",
                "timestamp": datetime.now().isoformat(),
                "message": "Connected to CCU OCMIM WebSocket server"
            }
            await websocket.send(json.dumps(welcome_msg))
            
            # Listen for messages from this OCM ECM client
            await self.handle_client_messages(websocket, client_id)
            
        except Exception as e:
            self.logger.error(f"❌ Error handling OCM connection: {e}")
        finally:
            # Clean up client connection
            if client_id and client_id in self.connected_clients:
                del self.connected_clients[client_id]
                self.logger.info(f"🔌 OCM ECM client {client_id} disconnected")
    
    async def handle_client_messages(self, websocket, client_id: str):
        """Listen for messages from a specific OCM ECM client."""
        try:
            async for message in websocket:
                self.logger.debug(f"Received message from OCM ECM {client_id}: {message}")
                
                # Update heartbeat
                if client_id in self.connected_clients:
                    self.connected_clients[client_id]["last_heartbeat"] = datetime.now()
                
                try:
                    data = json.loads(message)
                    # Process message
                    await self.handle_ocm_message(data, client_id)
                except json.JSONDecodeError as e:
                    self.logger.error(f"Invalid JSON message from OCM client {client_id}: {e}")
                    error_response = {
                        "type": "error",
                        "error": "invalid_json",
                        "message": str(e),
                        "timestamp": datetime.now().isoformat()
                    }
                    await websocket.send(json.dumps(error_response))
                
        except Exception as e:
            self.logger.error(f"Error handling messages from OCM ECM {client_id}: {e}")
    
    async def handle_ocm_message(self, data: Dict[str, Any], client_id: str):
        """Handle a message from OCM ECM."""
        try:
            message_type = data.get("type", "unknown")
            
            self.logger.debug(f"Processing {message_type} message from OCM ECM {client_id}")
            
            # Handle different message types
            if message_type == "heartbeat":
                await self._handle_ocm_heartbeat(data, client_id)
            elif message_type == "status_update":
                await self._handle_ocm_status_update(data)
            elif message_type == "processing_result":
                await self._handle_ocm_processing_result(data)
            elif message_type == "certificate_update_result":
                await self._handle_certificate_update_result(data)
            elif message_type == "report_delivery_status":
                await self._handle_report_delivery_status(data)
            elif message_type == "health_report":
                await self._handle_ocm_health_report(data)
            elif message_type == "error_report":
                await self._handle_ocm_error_report(data)
            else:
                self.logger.warning(f"Unknown message type '{message_type}' from OCM ECM {client_id}")
                
        except Exception as e:
            self.logger.error(f"Error processing message from OCM ECM {client_id}: {e}")
    
    async def _handle_ocm_heartbeat(self, data: Dict[str, Any], client_id: str):
        """Handle heartbeat from OCM ECM."""
        response = {
            "type": "heartbeat_response",
            "timestamp": datetime.now().isoformat(),
            "server": "OCMIM",
            "client_id": client_id
        }
        
        if client_id in self.connected_clients:
            try:
                await self.connected_clients[client_id]["websocket"].send(json.dumps(response))
            except Exception as e:
                self.logger.error(f"Failed to send heartbeat response to {client_id}: {e}")
    
    async def _handle_ocm_status_update(self, data: Dict[str, Any]):
        """Handle status update from OCM service."""
        try:
            status = data.get("status", {})
            self.ocm_health_status = status
            self.last_health_check = datetime.now()
            self.logger.debug(f"Received OCM status update: {status}")
        except Exception as e:
            self.logger.error(f"Error handling OCM status update: {e}")
    
    async def _handle_ocm_processing_result(self, data: Dict[str, Any]):
        """Handle processing result from OCM service."""
        try:
            request_id = data.get("request_id")
            result = data.get("result", {})
            
            if request_id in self.pending_requests:
                # Move to completed requests
                response = OCMResponse(
                    request_id=request_id,
                    status="completed",
                    response_data=result,
                    processing_time_ms=result.get("processing_time_ms", 0),
                    generated_reports=result.get("generated_reports", []),
                    delivered_at=datetime.now()
                )
                self.completed_requests[request_id] = response
                del self.pending_requests[request_id]
                self.logger.info(f"OCM processing completed for request {request_id}")
            
        except Exception as e:
            self.logger.error(f"Error handling OCM processing result: {e}")
    
    async def _handle_certificate_update_result(self, data: Dict[str, Any]):
        """Handle certificate update result from OCM."""
        try:
            cert_info = data.get("certificate", {})
            self.logger.info(f"OCM certificate update result: {cert_info}")
        except Exception as e:
            self.logger.error(f"Error handling certificate update result: {e}")
    
    async def _handle_report_delivery_status(self, data: Dict[str, Any]):
        """Handle report delivery status from OCM."""
        try:
            delivery_info = data.get("delivery", {})
            self.logger.info(f"OCM report delivery status: {delivery_info}")
        except Exception as e:
            self.logger.error(f"Error handling report delivery status: {e}")
    
    async def _handle_ocm_health_report(self, data: Dict[str, Any]):
        """Handle health report from OCM service."""
        try:
            health_info = data.get("health", {})
            self.ocm_health_status = health_info
            self.last_health_check = datetime.now()
            self.logger.debug(f"OCM health report: {health_info}")
        except Exception as e:
            self.logger.error(f"Error handling OCM health report: {e}")
    
    async def _handle_ocm_error_report(self, data: Dict[str, Any]):
        """Handle error report from OCM service."""
        try:
            error_info = data.get("error", {})
            self.logger.error(f"OCM error report: {error_info}")
        except Exception as e:
            self.logger.error(f"Error handling OCM error report: {e}")
    
    async def send_command_to_ocm(self, command: Dict[str, Any]) -> bool:
        """Send command to connected OCM ECM client."""
        if not self.connected_clients:
            self.logger.warning("No OCM ECM clients connected - cannot send command")
            return False
        
        try:
            # Send to all connected clients (should be just one)
            for client_id, client_info in self.connected_clients.items():
                websocket = client_info["websocket"]
                await websocket.send(json.dumps(command))
                self.logger.debug(f"Sent command to OCM ECM {client_id}: {command.get('type', 'unknown')}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending command to OCM ECM: {e}")
            return False


    
    async def stop(self):
        """Stop the OCMIM module gracefully."""
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
            
            self.logger.info("Stopping OCMIM module")
            
            # Close WebSocket connection
            if self.websocket:
                await self.websocket.close()
                self.websocket = None
            
            # Cancel background tasks
            for task in self.background_tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for tasks to complete
            if self.background_tasks:
                await asyncio.gather(*self.background_tasks, return_exceptions=True)
            
            self.connection_status = OCMStatus.DISCONNECTED
            
            self.logger.info("OCMIM module stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping OCMIM module: {e}")
    
    def _start_background_tasks(self):
        """Start background monitoring tasks."""
        # Heartbeat task
        task = asyncio.create_task(self._heartbeat_loop())
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)
        
        # Health monitoring task
        task = asyncio.create_task(self._health_monitor_loop())
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)
        
        # Request timeout monitoring
        task = asyncio.create_task(self._request_timeout_monitor())
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)
        
        # Connection maintenance
        task = asyncio.create_task(self._connection_maintenance_loop())
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)
    
    async def _connect_to_ocm(self) -> bool:
        """Establish WebSocket connection with OCM."""
        try:
            if self.connection_status in [OCMStatus.CONNECTED, OCMStatus.AUTHENTICATED]:
                return True
            
            self.connection_status = OCMStatus.CONNECTING
            self.stats['connection_count'] += 1
            
            # WebSocket URI
            ws_uri = f"ws://{self.ocm_host}:{self.ocm_websocket_port}/ccu"
            
            self.logger.info(f"Connecting to OCM at {ws_uri}")
            
            # Establish WebSocket connection
            self.websocket = await websockets.connect(
                ws_uri,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            
            self.connection_status = OCMStatus.CONNECTED
            self.last_heartbeat = datetime.now()
            
            # Send authentication message
            auth_message = {
                'type': 'authenticate',
                'service_id': self.ccu_service_id,
                'timestamp': datetime.now().isoformat(),
                'capabilities': [
                    'certificate_management',
                    'service_control',
                    'monitoring',
                    'output_processing'
                ]
            }
            
            await self._send_websocket_message(auth_message)
            
            # Start message handler
            task = asyncio.create_task(self._websocket_message_handler())
            self.background_tasks.add(task)
            task.add_done_callback(self.background_tasks.discard)
            
            # Trigger connection event
            await self._trigger_event('connection_established', {'timestamp': datetime.now()})
            
            self.logger.info("Successfully connected to OCM")
            self.reconnect_attempts = 0
            
            return True
            
        except Exception as e:
            self.connection_status = OCMStatus.ERROR
            self.logger.error(f"Failed to connect to OCM: {e}")
            
            # Schedule reconnection
            if self.reconnect_attempts < self.max_reconnect_attempts:
                self.reconnect_attempts += 1
                reconnect_delay = min(60, 5 * self.reconnect_attempts)
                self.logger.info(f"Will retry connection in {reconnect_delay} seconds (attempt {self.reconnect_attempts})")
                
                task = asyncio.create_task(self._schedule_reconnect(reconnect_delay))
                self.background_tasks.add(task)
                task.add_done_callback(self.background_tasks.discard)
            
            return False
    
    async def _schedule_reconnect(self, delay: int):
        """Schedule a reconnection attempt."""
        await asyncio.sleep(delay)
        if self.is_active:
            await self._connect_to_ocm()
    
    async def _websocket_message_handler(self):
        """Handle incoming WebSocket messages from OCM."""
        try:
            while self.is_active and self.websocket:
                try:
                    message = await self.websocket.recv()
                    await self._process_websocket_message(json.loads(message))
                    
                except websockets.exceptions.ConnectionClosed:
                    self.logger.warning("WebSocket connection closed by OCM")
                    break
                except json.JSONDecodeError as e:
                    self.logger.error(f"Invalid JSON received from OCM: {e}")
                except Exception as e:
                    self.logger.error(f"Error processing OCM message: {e}")
                    
        except Exception as e:
            self.logger.error(f"WebSocket message handler error: {e}")
        finally:
            self.connection_status = OCMStatus.DISCONNECTED
            self.stats['disconnection_count'] += 1
            await self._trigger_event('connection_lost', {'timestamp': datetime.now()})
    
    async def _process_websocket_message(self, message: Dict[str, Any]):
        """Process incoming WebSocket message from OCM."""
        try:
            message_type = message.get('type')
            self.stats['last_activity'] = datetime.now().isoformat()
            
            if message_type == 'authenticate_response':
                await self._handle_authentication_response(message)
            elif message_type == 'heartbeat_response':
                await self._handle_heartbeat_response(message)
            elif message_type == 'command_response':
                await self._handle_command_response(message)
            elif message_type == 'request_response':
                await self._handle_request_response(message)
            elif message_type == 'health_status':
                await self._handle_health_status(message)
            elif message_type == 'error':
                await self._handle_error_message(message)
            elif message_type == 'certificate_request':
                await self._handle_certificate_request(message)
            elif message_type == 'monitoring_data':
                await self._handle_monitoring_data(message)
            else:
                self.logger.warning(f"Unknown message type from OCM: {message_type}")
                
        except Exception as e:
            self.logger.error(f"Error processing WebSocket message: {e}")
    
    async def _handle_authentication_response(self, message: Dict[str, Any]):
        """Handle authentication response from OCM."""
        if message.get('status') == 'authenticated':
            self.connection_status = OCMStatus.AUTHENTICATED
            self.logger.info("Successfully authenticated with OCM")
            
            # Send initial SSL certificates
            await self._send_ssl_certificates()
            
        else:
            self.logger.error(f"OCM authentication failed: {message.get('message')}")
            self.connection_status = OCMStatus.ERROR
    
    async def _handle_heartbeat_response(self, message: Dict[str, Any]):
        """Handle heartbeat response from OCM."""
        self.last_heartbeat = datetime.now()
        
        # Update OCM health status from heartbeat
        if 'health_status' in message:
            self.ocm_health_status = message['health_status']
    
    async def _handle_command_response(self, message: Dict[str, Any]):
        """Handle command response from OCM."""
        command_id = message.get('command_id')
        if command_id and command_id in self.pending_commands:
            self.command_responses[command_id] = message
            del self.pending_commands[command_id]
            self.logger.debug(f"Received response for command {command_id}")
    
    async def _handle_request_response(self, message: Dict[str, Any]):
        """Handle output processing request response from OCM."""
        request_id = message.get('request_id')
        if request_id and request_id in self.pending_requests:
            
            # Create response object
            response = OCMResponse(
                request_id=request_id,
                status=message.get('status', 'unknown'),
                response_data=message.get('data', {}),
                processing_time_ms=message.get('processing_time_ms', 0),
                generated_reports=message.get('generated_reports', []),
                delivered_at=datetime.fromisoformat(message.get('delivered_at')) if message.get('delivered_at') else None,
                error_message=message.get('error_message')
            )
            
            # Store response
            self.completed_requests[request_id] = response
            del self.pending_requests[request_id]
            
            # Update statistics
            if response.status == 'success':
                self.stats['successful_requests'] += 1
            else:
                self.stats['failed_requests'] += 1
            
            # Trigger event
            await self._trigger_event('request_completed', {
                'request_id': request_id,
                'status': response.status,
                'processing_time': response.processing_time_ms
            })
            
            self.logger.info(f"Request {request_id} completed with status: {response.status}")
    
    async def _handle_health_status(self, message: Dict[str, Any]):
        """Handle health status update from OCM."""
        old_status = self.ocm_health_status
        self.ocm_health_status = message.get('health_data', {})
        self.last_health_check = datetime.now()
        
        # Trigger event if status changed significantly
        if old_status != self.ocm_health_status:
            await self._trigger_event('health_status_changed', {
                'old_status': old_status,
                'new_status': self.ocm_health_status
            })
    
    async def _handle_error_message(self, message: Dict[str, Any]):
        """Handle error message from OCM."""
        error_data = {
            'error_type': message.get('error_type'),
            'error_message': message.get('message'),
            'timestamp': message.get('timestamp'),
            'context': message.get('context', {})
        }
        
        self.logger.error(f"OCM Error: {error_data['error_message']}")
        
        await self._trigger_event('error_occurred', error_data)
    
    async def _handle_certificate_request(self, message: Dict[str, Any]):
        """Handle SSL certificate request from OCM."""
        try:
            if not self.certificate_manager:
                self.logger.error("Certificate manager not available")
                return
            
            # Get current certificates from certificate manager
            certificates = await self._get_ssl_certificates()
            
            if certificates:
                await self._send_ssl_certificates(certificates)
                self.logger.info("Sent SSL certificates to OCM")
            else:
                self.logger.error("No SSL certificates available to send")
                
        except Exception as e:
            self.logger.error(f"Error handling certificate request: {e}")
    
    async def _handle_monitoring_data(self, message: Dict[str, Any]):
        """Handle monitoring data from OCM."""
        self.performance_metrics.update(message.get('metrics', {}))
        
        # Log significant performance changes
        if 'error_rate' in self.performance_metrics:
            error_rate = self.performance_metrics['error_rate']
            if error_rate > 10:  # More than 10% error rate
                self.logger.warning(f"OCM error rate is high: {error_rate}%")
    
    async def _send_websocket_message(self, message: Dict[str, Any]):
        """Send message to OCM via WebSocket."""
        try:
            if self.websocket and self.connection_status in [OCMStatus.CONNECTED, OCMStatus.AUTHENTICATED]:
                await self.websocket.send(json.dumps(message))
            else:
                raise ConnectionError("WebSocket not connected")
        except Exception as e:
            self.logger.error(f"Failed to send WebSocket message: {e}")
            raise
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats to OCM."""
        while self.is_active:
            try:
                if self.connection_status == OCMStatus.AUTHENTICATED:
                    heartbeat_message = {
                        'type': 'heartbeat',
                        'service_id': self.ccu_service_id,
                        'timestamp': datetime.now().isoformat(),
                        'status': 'active'
                    }
                    
                    await self._send_websocket_message(heartbeat_message)
                
                await asyncio.sleep(self.heartbeat_interval)
                
            except Exception as e:
                self.logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(5)
    
    async def _health_monitor_loop(self):
        """Monitor OCM health status."""
        while self.is_active:
            try:
                if self.connection_status == OCMStatus.AUTHENTICATED:
                    # Request health status
                    await self._send_command('health_check', {})
                    self.stats['health_checks_performed'] += 1
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Error in health monitor loop: {e}")
                await asyncio.sleep(30)
    
    async def _request_timeout_monitor(self):
        """Monitor and timeout pending requests."""
        while self.is_active:
            try:
                current_time = datetime.now()
                timed_out_requests = []
                
                for request_id, request in self.pending_requests.items():
                    age = current_time - request.created_at
                    if age.total_seconds() > request.timeout_seconds:
                        timed_out_requests.append(request_id)
                
                # Handle timed out requests
                for request_id in timed_out_requests:
                    request = self.pending_requests[request_id]
                    
                    # Create timeout response
                    timeout_response = OCMResponse(
                        request_id=request_id,
                        status='timeout',
                        response_data={},
                        processing_time_ms=int((current_time - request.created_at).total_seconds() * 1000),
                        error_message=f'Request timed out after {request.timeout_seconds} seconds'
                    )
                    
                    self.completed_requests[request_id] = timeout_response
                    del self.pending_requests[request_id]
                    
                    self.stats['failed_requests'] += 1
                    
                    self.logger.warning(f"Request {request_id} timed out")
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in request timeout monitor: {e}")
                await asyncio.sleep(30)
    
    async def _connection_maintenance_loop(self):
        """Maintain WebSocket connection."""
        while self.is_active:
            try:
                # Check if connection is healthy
                if self.connection_status == OCMStatus.DISCONNECTED:
                    await self._connect_to_ocm()
                elif self.last_heartbeat:
                    # Check if heartbeat is too old
                    age = datetime.now() - self.last_heartbeat
                    if age.total_seconds() > self.heartbeat_interval * 3:
                        self.logger.warning("OCM heartbeat timeout - reconnecting")
                        self.connection_status = OCMStatus.DISCONNECTED
                        if self.websocket:
                            await self.websocket.close()
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in connection maintenance: {e}")
                await asyncio.sleep(30)
    
    # Public API methods
    
    async def send_output_request(self, request_data: Dict[str, Any], 
                                priority: RequestPriority = RequestPriority.C,
                                timeout_seconds: int = 300) -> str:
        """Send output processing request to OCM."""
        try:
            if self.connection_status != OCMStatus.AUTHENTICATED:
                raise ConnectionError("Not connected to OCM")
            
            # Create request
            request_id = f"ocm_req_{uuid.uuid4().hex}"
            request = OCMRequest(
                request_id=request_id,
                priority=priority,
                request_type='output_processing',
                source_module='CCU',
                data=request_data,
                created_at=datetime.now(),
                timeout_seconds=timeout_seconds
            )
            
            # Store pending request
            self.pending_requests[request_id] = request
            
            # Send request message
            message = {
                'type': 'output_request',
                'request_id': request_id,
                'priority': priority.value,
                'data': request_data,
                'timeout_seconds': timeout_seconds,
                'timestamp': datetime.now().isoformat()
            }
            
            await self._send_websocket_message(message)
            
            self.stats['total_requests_sent'] += 1
            
            self.logger.info(f"Sent output request {request_id} with priority {priority.value}")
            
            return request_id
            
        except Exception as e:
            self.logger.error(f"Failed to send output request: {e}")
            raise
    
    async def _send_command(self, command_type: str, parameters: Dict[str, Any] = None) -> str:
        """Send command to OCM."""
        try:
            if self.connection_status != OCMStatus.AUTHENTICATED:
                raise ConnectionError("Not connected to OCM")
            
            command_id = f"cmd_{uuid.uuid4().hex}"
            
            message = {
                'type': 'command',
                'command_id': command_id,
                'command_type': command_type,
                'parameters': parameters or {},
                'timestamp': datetime.now().isoformat()
            }
            
            # Store pending command
            self.pending_commands[command_id] = {
                'command_type': command_type,
                'parameters': parameters,
                'sent_at': datetime.now()
            }
            
            await self._send_websocket_message(message)
            
            self.stats['commands_sent'] += 1
            
            return command_id
            
        except Exception as e:
            self.logger.error(f"Failed to send command: {e}")
            raise
    
    async def get_request_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get status of an output processing request."""
        # Check completed requests
        if request_id in self.completed_requests:
            response = self.completed_requests[request_id]
            return asdict(response)
        
        # Check pending requests
        if request_id in self.pending_requests:
            request = self.pending_requests[request_id]
            return {
                'request_id': request_id,
                'status': 'pending',
                'created_at': request.created_at.isoformat(),
                'priority': request.priority.value,
                'age_seconds': (datetime.now() - request.created_at).total_seconds()
            }
        
        return None
    
    async def _get_ssl_certificates(self) -> Optional[Dict[str, Any]]:
        """Get SSL certificates from certificate manager."""
        try:
            if not self.certificate_manager:
                return None
            
            # Get certificates from CCU's certificate manager
            cert_data = await self.certificate_manager.get_certificates_for_service('OCM')
            
            if cert_data:
                return {
                    'cert_content': cert_data.get('cert_content'),
                    'key_content': cert_data.get('key_content'),
                    'cert_hash': cert_data.get('cert_hash'),
                    'key_hash': cert_data.get('key_hash'),
                    'expires_at': cert_data.get('expires_at'),
                    'updated_at': datetime.now().isoformat()
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get SSL certificates: {e}")
            return None
    
    async def _send_ssl_certificates(self, certificates: Dict[str, Any] = None):
        """Send SSL certificates to OCM."""
        try:
            if not certificates:
                certificates = await self._get_ssl_certificates()
            
            if certificates:
                message = {
                    'type': 'certificate_update',
                    'certificates': certificates,
                    'timestamp': datetime.now().isoformat()
                }
                
                await self._send_websocket_message(message)
                self.stats['certificate_updates'] += 1
                self.logger.info("SSL certificates sent to OCM")
            
        except Exception as e:
            self.logger.error(f"Failed to send SSL certificates: {e}")
    
    async def update_ocm_configuration(self, config_updates: Dict[str, Any]) -> bool:
        """Update OCM service configuration."""
        try:
            command_id = await self._send_command('configuration_update', {
                'config_updates': config_updates
            })
            
            # Wait for response
            timeout = 30
            start_time = time.time()
            
            while command_id not in self.command_responses:
                if time.time() - start_time > timeout:
                    raise TimeoutError("Configuration update timed out")
                await asyncio.sleep(0.1)
            
            response = self.command_responses[command_id]
            return response.get('status') == 'success'
            
        except Exception as e:
            self.logger.error(f"Failed to update OCM configuration: {e}")
            return False
    
    async def restart_ocm_service(self) -> bool:
        """Restart OCM service."""
        try:
            command_id = await self._send_command('service_control', {
                'action': 'restart'
            })
            
            # Wait for response
            timeout = 60  # Restart can take longer
            start_time = time.time()
            
            while command_id not in self.command_responses:
                if time.time() - start_time > timeout:
                    raise TimeoutError("Service restart timed out")
                await asyncio.sleep(0.5)
            
            response = self.command_responses[command_id]
            return response.get('status') == 'success'
            
        except Exception as e:
            self.logger.error(f"Failed to restart OCM service: {e}")
            return False
    
    async def run_ocm_tests(self, test_types: List[str] = None) -> Dict[str, Any]:
        """Run tests on OCM service."""
        try:
            command_id = await self._send_command('test_execution', {
                'test_types': test_types or ['health', 'integration']
            })
            
            # Wait for response
            timeout = 120  # Tests can take longer
            start_time = time.time()
            
            while command_id not in self.command_responses:
                if time.time() - start_time > timeout:
                    raise TimeoutError("Test execution timed out")
                await asyncio.sleep(1)
            
            response = self.command_responses[command_id]
            return response.get('data', {})
            
        except Exception as e:
            self.logger.error(f"Failed to run OCM tests: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def add_event_handler(self, event_type: str, handler: Callable):
        """Add event handler for OCM events."""
        if event_type in self.event_handlers:
            self.event_handlers[event_type].append(handler)
            self.logger.debug(f"Added event handler for {event_type}")
    
    async def _trigger_event(self, event_type: str, event_data: Dict[str, Any]):
        """Trigger event handlers."""
        try:
            if event_type in self.event_handlers:
                for handler in self.event_handlers[event_type]:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(event_data)
                        else:
                            handler(event_data)
                    except Exception as e:
                        self.logger.error(f"Error in event handler for {event_type}: {e}")
        except Exception as e:
            self.logger.error(f"Error triggering event {event_type}: {e}")
    
    async def get_ocm_status(self) -> Dict[str, Any]:
        """Get comprehensive OCM status."""
        return {
            'connection_status': self.connection_status.value,
            'is_connected': self.connection_status == OCMStatus.AUTHENTICATED,
            'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            'health_status': self.ocm_health_status,
            'performance_metrics': self.performance_metrics,
            'pending_requests': len(self.pending_requests),
            'completed_requests': len(self.completed_requests),
            'reconnect_attempts': self.reconnect_attempts,
            'statistics': self.stats.copy()
        }
    
    async def health_check(self) -> bool:
        """Perform health check."""
        try:
            if self.connection_status != OCMStatus.AUTHENTICATED:
                return False
            
            # Send health check command
            command_id = await self._send_command('health_check')
            
            # Wait briefly for response
            timeout = 10
            start_time = time.time()
            
            while command_id not in self.command_responses and (time.time() - start_time) < timeout:
                await asyncio.sleep(0.1)
            
            if command_id in self.command_responses:
                response = self.command_responses[command_id]
                return response.get('status') == 'success'
            
            return False
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current OCMIM module status."""
        return {
            'module': self.module_name,
            'active': self.is_active,
            'connection_status': self.connection_status.value,
            'ocm_host': self.ocm_host,
            'ocm_websocket_port': self.ocm_websocket_port,
            'ocm_api_port': self.ocm_api_port,
            'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            'pending_requests': len(self.pending_requests),
            'completed_requests': len(self.completed_requests),
            'reconnect_attempts': self.reconnect_attempts,
            'statistics': self.stats.copy()
        } 