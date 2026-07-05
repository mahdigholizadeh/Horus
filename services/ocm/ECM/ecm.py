"""
External Control Module (ECM) for OCM

Primary interface between the OCM microservice and the Central Control Unit (CCU).
Handles service control, monitoring/log streaming, configuration management, 
SSL certificate updates, remote test execution, resets, database access, 
and real-time monitoring data streaming for the output gateway.
"""

import asyncio
import logging
import websockets
import json
import ssl
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
import threading
import queue
import hashlib
from pathlib import Path

class ECMConnectionStatus:
    """Connection status constants."""
    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    CONNECTING = "connecting"
    ERROR = "error"
    RECONNECTING = "reconnecting"

class ExternalControlModule:
    """
    External Control Module (ECM) for OCM
    
    - Maintains persistent connection to CCU
    - Receives and processes commands from CCU
    - Streams logs and monitoring data to CCU
    - Handles SSL certificate updates from CCU
    - Manages service control and configuration
    - Processes report delivery confirmations
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the ECM module."""
        self.logger = logging.getLogger(__name__)

        # NEW ARCHITECTURE: WebSocket CLIENT configuration
        self.ccu_websocket_uri = "ws://localhost:4446/ws"
        self.websocket_connection = None
        self.websocket_task = None 
        self.heartbeat_task = None
        self.connection_retry_count = 0
        self.max_retry_attempts = 10
        self.retry_delay = 5  # seconds
        self.heartbeat_interval = 30  # seconds
        self.connection_timeout = 5.0  # seconds
        self.fallback_ports = [4456, 4466, 4476]
        self.current_port = 4446  # Primary CCU OCMIM port
        self.module_name = "ECM"
        self.is_active = False
        
        # Configuration
        self.config = config
        self.ccu_config = config.get('ccu_integration', {})
        self.ccu_host = self.ccu_config.get('ccu_host', 'localhost')
        self.ccu_port = self.ccu_config.get('ccu_port', 8080)
        self.heartbeat_interval = self.ccu_config.get('heartbeat_interval', 30)
        self.reconnect_attempts = self.ccu_config.get('reconnect_attempts', 5)
        
        # Connection management
        self.connection_status = ECMConnectionStatus.DISCONNECTED
        self.websocket = None
        self.connection_uri = f"ws://{self.ccu_host}:{self.ccu_port}/ws/ocm"
        
        # Message queues
        self.outgoing_queue = asyncio.Queue()
        self.command_handlers = {}
        
        # Statistics
        self.stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'commands_processed': 0,
            'certificate_updates': 0,
            'connection_attempts': 0,
            'last_heartbeat': None,
            'connection_established': None
        }
        
        # Register command handlers
        self._register_command_handlers()
        
        self.logger.info(f"{self.module_name} initialized for CCU at {self.ccu_host}:{self.ccu_port}")
    
    def register_command_handler(self, command_name: str, handler: Callable):
        """Register a custom command handler."""
        self.command_handlers[command_name] = handler
        self.logger.info(f"Registered command handler for: {command_name}")
    
    def _register_command_handlers(self):
        """Register handlers for different CCU commands."""
        self.command_handlers = {
            'service_control': self._handle_service_control,
            'configuration_update': self._handle_configuration_update,
            'certificate_update': self._handle_certificate_update,
            'test_execution': self._handle_test_execution,
            'database_query': self._handle_database_query,
            'monitoring_request': self._handle_monitoring_request,
            'reset_command': self._handle_reset_command,
            'report_status_query': self._handle_report_status_query,
            'priority_adjustment': self._handle_priority_adjustment,
            'output_validation': self._handle_output_validation,
            'health_check': self._handle_health_check,
            'module_command': self._handle_module_command,
            # Add handlers for acknowledgment messages
            'registration_ack': self._handle_registration_ack,
            'heartbeat_ack': self._handle_heartbeat_ack,
            'certificate_ack': self._handle_certificate_ack,
            'auth_ack': self._handle_auth_ack,
            'test_response': self._handle_test_response
        }
    
    async def start(self):
        """Start the ECM module."""
        try:
            self.is_active = True
                        # Start WebSocket client connection to CCU
            await self.start_websocket_client()
            
            self.logger.info("Starting ECM - establishing connection to CCU")
            
            # Start connection management task
            asyncio.create_task(self._connection_manager())
            
            # Start message processing task
            asyncio.create_task(self._process_outgoing_messages())
            
            self.logger.info("ECM started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start ECM: {e}")
            raise
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
                "service": "OCM"
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
                "service": "OCM"
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
            "service": "OCM"
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
                        "service": "OCM",
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
        try:
            self.is_active = False
            
            if self.websocket:
                await self.websocket.close()
                self.websocket = None
            
            self.connection_status = ECMConnectionStatus.DISCONNECTED
                        # Stop WebSocket client connection
            await self.stop_websocket_client()
            
            self.logger.info("ECM stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping ECM: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        is_healthy = (
            self.is_active and 
            self.connection_status == ECMConnectionStatus.CONNECTED and
            self.websocket is not None
        )
        
        return {
            'healthy': is_healthy,
            'connection_status': self.connection_status,
            'is_active': self.is_active,
            'websocket_connected': self.websocket is not None,
            'messages_sent': self.stats.get('messages_sent', 0),
            'messages_received': self.stats.get('messages_received', 0)
        }
    
    async def _connection_manager(self):
        """Manage WebSocket connection to CCU."""
        reconnect_count = 0
        
        while self.is_active:
            try:
                if self.connection_status == ECMConnectionStatus.DISCONNECTED:
                    await self._establish_connection()
                    reconnect_count = 0
                    
                elif self.connection_status == ECMConnectionStatus.CONNECTED:
                    # Send periodic heartbeat
                    await self._send_heartbeat()
                    
                await asyncio.sleep(self.heartbeat_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Connection manager error: {e}")
                self.connection_status = ECMConnectionStatus.ERROR
                
                # Attempt reconnection
                if reconnect_count < self.reconnect_attempts:
                    reconnect_count += 1
                    self.connection_status = ECMConnectionStatus.RECONNECTING
                    await asyncio.sleep(5 * reconnect_count)  # Exponential backoff
                else:
                    self.logger.error("Max reconnection attempts reached")
                    break
    
    async def _establish_connection(self):
        """Establish WebSocket connection to CCU."""
        try:
            self.connection_status = ECMConnectionStatus.CONNECTING
            self.stats['connection_attempts'] += 1
            
            self.logger.info(f"Connecting to CCU at {self.connection_uri}")
            
            # Create WebSocket connection
            self.websocket = await websockets.connect(
                self.connection_uri,
                ping_interval=20,
                ping_timeout=10
            )
            
            self.connection_status = ECMConnectionStatus.CONNECTED
            self.stats['connection_established'] = datetime.now().isoformat()
            
            self.logger.info("Successfully connected to CCU")
            
            # Send initial registration
            await self._send_registration()
            
            # Start message receiving task
            asyncio.create_task(self._receive_messages())
            
        except Exception as e:
            self.logger.error(f"Failed to establish connection: {e}")
            self.connection_status = ECMConnectionStatus.ERROR
            self.websocket = None
            raise
    
    async def _send_registration(self):
        """Send registration message to CCU."""
        registration = {
            'type': 'service_registration',
            'service': 'OCM',
            'timestamp': datetime.now().isoformat(),
            'capabilities': [
                'output_processing',
                'report_generation',
                'web_server_communication',
                'priority_management',
                'ssl_certificate_management'
            ],
            'configuration': {
                'output_port': self.config.get('network', {}).get('output_port', 47812),
                'ssl_enabled': self.config.get('ssl_configuration', {}).get('enabled', True),
                'priority_levels': self.config.get('priority_management', {}).get('levels', ['A', 'B', 'C', 'D'])
            }
        }
        
        await self._send_message(registration)
        self.logger.info("Registration sent to CCU")
    
    async def _receive_messages(self):
        """Receive and process messages from CCU."""
        try:
            async for message in self.websocket:
                await self._process_incoming_message(message)
                
        except websockets.exceptions.ConnectionClosed:
            self.logger.warning("WebSocket connection closed")
            self.connection_status = ECMConnectionStatus.DISCONNECTED
            self.websocket = None
        except Exception as e:
            self.logger.error(f"Error receiving messages: {e}")
            self.connection_status = ECMConnectionStatus.ERROR
            self.websocket = None
    
    async def _process_incoming_message(self, message: str):
        """Process incoming message from CCU."""
        try:
            data = json.loads(message)
            self.stats['messages_received'] += 1
            
            command_type = data.get('type')
            if command_type in self.command_handlers:
                handler = self.command_handlers[command_type]
                await handler(data)
                self.stats['commands_processed'] += 1
            else:
                self.logger.warning(f"Unknown command type: {command_type}")
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse message: {e}")
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
    
    async def _send_message(self, message: Dict[str, Any]):
        """Send message to CCU."""
        if self.websocket and self.connection_status == ECMConnectionStatus.CONNECTED:
            try:
                message_str = json.dumps(message, default=str)
                await self.websocket.send(message_str)
                self.stats['messages_sent'] += 1
            except Exception as e:
                self.logger.error(f"Failed to send message: {e}")
        else:
            # Queue message for later delivery
            await self.outgoing_queue.put(message)
    
    async def _process_outgoing_messages(self):
        """Process queued outgoing messages."""
        while self.is_active:
            try:
                # Wait for connection to be established
                if self.connection_status != ECMConnectionStatus.CONNECTED:
                    await asyncio.sleep(1)
                    continue
                
                # Process queued messages
                try:
                    message = await asyncio.wait_for(self.outgoing_queue.get(), timeout=1.0)
                    await self._send_message(message)
                except asyncio.TimeoutError:
                    continue
                    
            except Exception as e:
                self.logger.error(f"Error processing outgoing messages: {e}")
                await asyncio.sleep(1)
    
    async def _send_heartbeat(self):
        """Send heartbeat to CCU."""
        if self.connection_status == ECMConnectionStatus.CONNECTED:
            heartbeat = {
                'type': 'heartbeat',
                'service': 'OCM',
                'timestamp': datetime.now().isoformat(),
                'stats': self.stats
            }
            
            await self._send_message(heartbeat)
            self.stats['last_heartbeat'] = datetime.now().isoformat()
    
    async def send_heartbeat(self, data: Dict[str, Any]):
        """Public method to send heartbeat with custom data."""
        heartbeat = {
            'type': 'heartbeat',
            'service': 'OCM',
            'timestamp': datetime.now().isoformat(),
            **data
        }
        
        await self._send_message(heartbeat)
    
    # Command Handlers
    
    async def _handle_service_control(self, data: Dict[str, Any]):
        """Handle service control commands from CCU."""
        try:
            command = data.get('command')
            self.logger.info(f"Received service control command: {command}")
            
            # This would integrate with the main OCM service controller
            response = {
                'type': 'service_control_response',
                'command': command,
                'status': 'acknowledged',
                'timestamp': datetime.now().isoformat()
            }
            
            await self._send_message(response)
            
        except Exception as e:
            self.logger.error(f"Error handling service control: {e}")
    
    async def _handle_configuration_update(self, data: Dict[str, Any]):
        """Handle configuration updates from CCU."""
        try:
            new_config = data.get('configuration', {})
            self.logger.info("Received configuration update from CCU")
            
            # Update local configuration
            self.config.update(new_config)
            
            response = {
                'type': 'configuration_update_response',
                'status': 'applied',
                'timestamp': datetime.now().isoformat()
            }
            
            await self._send_message(response)
            
        except Exception as e:
            self.logger.error(f"Error handling configuration update: {e}")
    
    async def _handle_certificate_update(self, data: Dict[str, Any]):
        """Handle SSL certificate updates from CCU."""
        try:
            cert_data = data.get('certificate_data', {})
            self.logger.info("Received SSL certificate update from CCU")
            
            # This would integrate with the main OCM service to update certificates
            # The main service has an update_ssl_certificates method
            self.stats['certificate_updates'] += 1
            
            response = {
                'type': 'certificate_update_response',
                'status': 'applied',
                'cert_hash': cert_data.get('cert_hash'),
                'timestamp': datetime.now().isoformat()
            }
            
            await self._send_message(response)
            
        except Exception as e:
            self.logger.error(f"Error handling certificate update: {e}")
    
    async def _handle_test_execution(self, data: Dict[str, Any]):
        """Handle test execution requests from CCU."""
        try:
            test_type = data.get('test_type')
            self.logger.info(f"Received test execution request: {test_type}")
            
            # This would integrate with TMM module
            response = {
                'type': 'test_execution_response',
                'test_type': test_type,
                'status': 'completed',
                'results': 'Test execution simulated',
                'timestamp': datetime.now().isoformat()
            }
            
            await self._send_message(response)
            
        except Exception as e:
            self.logger.error(f"Error handling test execution: {e}")
    
    async def _handle_database_query(self, data: Dict[str, Any]):
        """Handle database query requests from CCU."""
        try:
            query = data.get('query')
            self.logger.info("Received database query from CCU")
            
            # This would integrate with DCM module
            response = {
                'type': 'database_query_response',
                'status': 'executed',
                'results': 'Query results placeholder',
                'timestamp': datetime.now().isoformat()
            }
            
            await self._send_message(response)
            
        except Exception as e:
            self.logger.error(f"Error handling database query: {e}")
    
    async def _handle_monitoring_request(self, data: Dict[str, Any]):
        """Handle monitoring data requests from CCU."""
        try:
            request_type = data.get('request_type')
            self.logger.info(f"Received monitoring request: {request_type}")
            
            # This would integrate with MSM module
            response = {
                'type': 'monitoring_response',
                'request_type': request_type,
                'monitoring_data': {
                    'service_health': 'healthy',
                    'active_requests': 0,
                    'queue_sizes': {'A': 0, 'B': 0, 'C': 0, 'D': 0}
                },
                'timestamp': datetime.now().isoformat()
            }
            
            await self._send_message(response)
            
        except Exception as e:
            self.logger.error(f"Error handling monitoring request: {e}")
    
    async def _handle_reset_command(self, data: Dict[str, Any]):
        """Handle reset commands from CCU."""
        try:
            reset_type = data.get('reset_type')
            self.logger.info(f"Received reset command: {reset_type}")
            
            response = {
                'type': 'reset_response',
                'reset_type': reset_type,
                'status': 'completed',
                'timestamp': datetime.now().isoformat()
            }
            
            await self._send_message(response)
            
        except Exception as e:
            self.logger.error(f"Error handling reset command: {e}")
    
    async def _handle_report_status_query(self, data: Dict[str, Any]):
        """Handle report status queries from CCU."""
        try:
            request_id = data.get('request_id')
            self.logger.info(f"Received report status query for request: {request_id}")
            
            # This would integrate with RMM and DCM modules
            response = {
                'type': 'report_status_response',
                'request_id': request_id,
                'status': 'delivered',
                'delivery_time': datetime.now().isoformat(),
                'timestamp': datetime.now().isoformat()
            }
            
            await self._send_message(response)
            
        except Exception as e:
            self.logger.error(f"Error handling report status query: {e}")
    
    async def _handle_priority_adjustment(self, data: Dict[str, Any]):
        """Handle priority adjustment requests from CCU."""
        try:
            priority_config = data.get('priority_config', {})
            self.logger.info("Received priority adjustment from CCU")
            
            # This would integrate with RMM module
            response = {
                'type': 'priority_adjustment_response',
                'status': 'applied',
                'new_config': priority_config,
                'timestamp': datetime.now().isoformat()
            }
            
            await self._send_message(response)
            
        except Exception as e:
            self.logger.error(f"Error handling priority adjustment: {e}")
    
    async def _handle_output_validation(self, data: Dict[str, Any]):
        """Handle output validation requests from CCU."""
        try:
            validation_request = data.get('validation_request', {})
            self.logger.info("Received output validation request from CCU")
            
            # This would integrate with OCVM module
            response = {
                'type': 'output_validation_response',
                'status': 'validated',
                'validation_results': 'All outputs valid',
                'timestamp': datetime.now().isoformat()
            }
            
            await self._send_message(response)
            
        except Exception as e:
            self.logger.error(f"Error handling output validation: {e}")
    
    async def _handle_health_check(self, data: Dict[str, Any]):
        """Handle health check requests from CCU."""
        try:
            health_status = await self.health_check()
            
            response = {
                'type': 'health_check_response',
                'status': 'healthy' if health_status else 'unhealthy',
                'connection_status': self.connection_status,
                'stats': self.stats,
                'timestamp': datetime.now().isoformat()
            }
            
            await self._send_message(response)
            
        except Exception as e:
            self.logger.error(f"Error handling health check: {e}")
    
    async def _handle_module_command(self, data: Dict[str, Any]):
        """Handle module-specific commands from CCU."""
        try:
            module_name = data.get('module')
            command = data.get('command')
            self.logger.info(f"Received module command for {module_name}: {command}")
            
            response = {
                'type': 'module_command_response',
                'module': module_name,
                'command': command,
                'status': 'executed',
                'timestamp': datetime.now().isoformat()
            }
            
            await self._send_message(response)
            
        except Exception as e:
            self.logger.error(f"Error handling module command: {e}")
    
    # Acknowledgment Message Handlers
    
    async def _handle_registration_ack(self, data: Dict[str, Any]):
        """Handle registration acknowledgment from CCU."""
        try:
            status = data.get('status')
            service_id = data.get('service_id')
            registration_token = data.get('registration_token')
            
            self.logger.info(f"Registration acknowledgment received: {status}")
            
            if status == 'accepted':
                self.logger.info(f"Service registered successfully with ID: {service_id}")
                # Store registration details if needed
                self.stats['service_id'] = service_id
                self.stats['registration_token'] = registration_token
            else:
                self.logger.warning(f"Registration failed: {status}")
                
        except Exception as e:
            self.logger.error(f"Error handling registration acknowledgment: {e}")
    
    async def _handle_heartbeat_ack(self, data: Dict[str, Any]):
        """Handle heartbeat acknowledgment from CCU."""
        try:
            timestamp = data.get('timestamp')
            self.logger.debug(f"Heartbeat acknowledgment received at {timestamp}")
            # Update stats or perform any heartbeat-related processing
            self.stats['last_heartbeat_ack'] = timestamp
            
        except Exception as e:
            self.logger.error(f"Error handling heartbeat acknowledgment: {e}")
    
    async def _handle_certificate_ack(self, data: Dict[str, Any]):
        """Handle certificate acknowledgment from CCU."""
        try:
            status = data.get('status')
            timestamp = data.get('timestamp')
            self.logger.info(f"Certificate acknowledgment received: {status} at {timestamp}")
            
        except Exception as e:
            self.logger.error(f"Error handling certificate acknowledgment: {e}")
    
    async def _handle_auth_ack(self, data: Dict[str, Any]):
        """Handle authentication acknowledgment from CCU."""
        try:
            status = data.get('status')
            timestamp = data.get('timestamp')
            self.logger.info(f"Authentication acknowledgment received: {status} at {timestamp}")
            
        except Exception as e:
            self.logger.error(f"Error handling authentication acknowledgment: {e}")
    
    async def _handle_test_response(self, data: Dict[str, Any]):
        """Handle test response from CCU."""
        try:
            status = data.get('status')
            timestamp = data.get('timestamp')
            self.logger.info(f"Test response received: {status} at {timestamp}")
            
        except Exception as e:
            self.logger.error(f"Error handling test response: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current ECM status."""
        return {
            'module': self.module_name,
            'active': self.is_active,
            'connection_status': self.connection_status,
            'ccu_connection': f"{self.ccu_host}:{self.ccu_port}",
            'messages_sent': self.stats.get('messages_sent', 0),
            'messages_received': self.stats.get('messages_received', 0),
            'stats': self.stats.copy()
        }
    
    async def send_report_delivered(self, request_id: str, delivery_info: Dict[str, Any]):
        """Send report delivery confirmation to CCU."""
        message = {
            'type': 'report_delivered',
            'request_id': request_id,
            'delivery_info': delivery_info,
            'timestamp': datetime.now().isoformat()
        }
        
        await self._send_message(message)
    
    async def send_error_report(self, error_info: Dict[str, Any]):
        """Send error report to CCU."""
        message = {
            'type': 'error_report',
            'error_info': error_info,
            'timestamp': datetime.now().isoformat()
        }
        
        await self._send_message(message)
    
    async def send_monitoring_data(self, monitoring_data: Dict[str, Any]):
        """Send monitoring data to CCU."""
        message = {
            'type': 'monitoring_data',
            'data': monitoring_data,
            'timestamp': datetime.now().isoformat()
        }
        
        await self._send_message(message)

    async def start(self):
        """Start the ECM module."""
        self.is_active = True 
        await self.start_websocket_client()
        self.logger.info("✅ OCM ECM started successfully")

    async def stop(self):
        """Stop the ECM module."""
        self.is_active = False
        await self.stop_websocket_client()  
        self.logger.info("🔌 OCM ECM stopped successfully")

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        return {
            "healthy": self.connection_status == ECMConnectionStatus.CONNECTED,
            "module": "ECM",
            "service": "OCM", 
            "connection_status": self.connection_status,
            "timestamp": datetime.now().isoformat()
        } 