"""
Activation Receiver Module (ARM) for RLA Microservice

This module handles activation requests on port 3812:
- Listens for binary activation key (0x9D37)
- Validates activation requests
- Manages activation state
- Provides activation status to other modules
"""

import asyncio
import logging
import socket
import struct
from typing import Dict, Any, Optional, Callable
from datetime import datetime
import threading


class ActivationReceiverModule:
    """
    Activation Receiver Module
    
    Handles activation requests for the RLA microservice:
    - Listens on port 3812 for activation key
    - Validates binary activation key (0x9D37)
    - Manages activation state
    - Provides activation callbacks
    """
    
    def __init__(self):
        """Initialize the ARM module."""
        self.logger = logging.getLogger(__name__)
        self.module_name = "ARM"
        self.is_active = False
        self.is_listening = False
        
        # Protocol constants
        self.activation_key = 0b1001110100110111  # 0x9D37
        self.activation_port = 3812
        
        # Activation state
        self.activation_state = {
            "activated": False,
            "last_activation": None,
            "activation_count": 0,
            "failed_attempts": 0,
            "last_activator_ip": None
        }
        
        # Statistics
        self.stats = {
            "total_attempts": 0,
            "successful_activations": 0,
            "failed_activations": 0,
            "invalid_keys": 0,
            "connection_errors": 0,
            "last_activity": None
        }
        
        # Network settings
        self.network_settings = {
            "host": "0.0.0.0",
            "port": 3812,
            "timeout": 30,
            "max_connections": 1,
            "reuse_address": True
        }
        
        # Callback functions
        self.callbacks = {
            "on_activation": [],
            "on_deactivation": [],
            "on_failed_attempt": []
        }
        
        # Server socket
        self.server_socket = None
        self.server_task = None
        
        self.logger.info(f"{self.module_name} initialized successfully")
    
    async def start(self):
        """Start the ARM module."""
        try:
            self.is_active = True
            self.logger.info(f"{self.module_name} started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start {self.module_name}: {e}")
            raise
    
    async def stop(self):
        """Stop the ARM module."""
        try:
            self.is_active = False
            
            # Stop activation listener
            if self.is_listening:
                await self.stop_activation_listener()
            
            self.logger.info(f"{self.module_name} stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to stop {self.module_name}: {e}")
            raise
    
    async def start_activation_listener(self, port: int = None, activation_key: int = None):
        """
        Start listening for activation requests.
        
        Args:
            port: Port to listen on (defaults to 3812)
            activation_key: Expected activation key (defaults to 0x9D37)
        """
        try:
            if port:
                self.network_settings["port"] = port
            if activation_key:
                self.activation_key = activation_key
            
            self.logger.info(f"Starting activation listener on port {self.network_settings['port']}")
            
            # Start the server task
            self.server_task = asyncio.create_task(self._activation_server())
            self.is_listening = True
            
            self.logger.info(f"Activation listener started on port {self.network_settings['port']}")
            
        except Exception as e:
            self.logger.error(f"Failed to start activation listener: {e}")
            raise
    
    async def stop_activation_listener(self):
        """Stop the activation listener."""
        try:
            self.logger.info("Stopping activation listener...")
            
            self.is_listening = False
            
            # Close server socket if exists
            if self.server_socket:
                self.server_socket.close()
                self.server_socket = None
            
            # Cancel server task
            if self.server_task:
                self.server_task.cancel()
                try:
                    await self.server_task
                except asyncio.CancelledError:
                    pass
                self.server_task = None
            
            self.logger.info("Activation listener stopped")
            
        except Exception as e:
            self.logger.error(f"Failed to stop activation listener: {e}")
            raise
    
    async def _activation_server(self):
        """Main activation server loop."""
        try:
            while self.is_active and self.is_listening:
                try:
                    # Create server socket
                    self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    self.server_socket.bind((self.network_settings["host"], self.network_settings["port"]))
                    self.server_socket.listen(self.network_settings["max_connections"])
                    self.server_socket.settimeout(self.network_settings["timeout"])
                    
                    self.logger.info(f"Waiting for activation on port {self.network_settings['port']}")
                    
                    # Accept connection
                    try:
                        client_socket, address = self.server_socket.accept()
                        self.logger.info(f"Activation connection from {address}")
                        
                        # Process activation request
                        await self._process_activation_request(client_socket, address)
                        
                    except socket.timeout:
                        self.logger.debug("Activation timeout - no connection received")
                        continue
                    except Exception as e:
                        self.logger.error(f"Connection error: {e}")
                        self.stats["connection_errors"] += 1
                        continue
                    
                except Exception as e:
                    self.logger.error(f"Server error: {e}")
                    self.stats["connection_errors"] += 1
                    await asyncio.sleep(1)
                    continue
                
                finally:
                    # Close server socket
                    if self.server_socket:
                        self.server_socket.close()
                        self.server_socket = None
                
                # Small delay between activation attempts
                await asyncio.sleep(0.1)
                
        except asyncio.CancelledError:
            self.logger.info("Activation server cancelled")
        except Exception as e:
            self.logger.error(f"Activation server error: {e}")
        finally:
            self.is_listening = False
    
    async def _process_activation_request(self, client_socket: socket.socket, address: tuple):
        """Process an activation request."""
        try:
            self.stats["total_attempts"] += 1
            self.stats["last_activity"] = datetime.now()
            
            with client_socket:
                # Set socket timeout
                client_socket.settimeout(10)
                
                # Receive activation key (2 bytes)
                activation_data = self._receive_exact_bytes(client_socket, 2)
                if not activation_data:
                    self.logger.warning(f"No activation data received from {address}")
                    self.stats["failed_activations"] += 1
                    await self._call_callbacks("on_failed_attempt", address, "No data received")
                    return
                
                # Unpack activation key
                try:
                    received_key = struct.unpack('>H', activation_data)[0]
                    self.logger.info(f"Received activation key: 0x{received_key:04X} from {address}")
                except struct.error as e:
                    self.logger.error(f"Failed to unpack activation key: {e}")
                    self.stats["failed_activations"] += 1
                    await self._call_callbacks("on_failed_attempt", address, "Invalid data format")
                    return
                
                # Validate activation key
                if received_key == self.activation_key:
                    # Activation successful
                    self.logger.info(f"Activation successful from {address}")
                    
                    # Update activation state
                    self.activation_state["activated"] = True
                    self.activation_state["last_activation"] = datetime.now()
                    self.activation_state["activation_count"] += 1
                    self.activation_state["last_activator_ip"] = address[0]
                    
                    # Update statistics
                    self.stats["successful_activations"] += 1
                    
                    # Call activation callbacks
                    await self._call_callbacks("on_activation", address, received_key)
                    
                    # Send success response (optional)
                    try:
                        success_response = struct.pack('>H', 0x0001)  # Success code
                        client_socket.send(success_response)
                    except Exception as e:
                        self.logger.warning(f"Failed to send success response: {e}")
                    
                else:
                    # Invalid activation key
                    self.logger.warning(f"Invalid activation key: 0x{received_key:04X} from {address}")
                    
                    # Update statistics
                    self.stats["failed_activations"] += 1
                    self.stats["invalid_keys"] += 1
                    self.activation_state["failed_attempts"] += 1
                    
                    # Call failed attempt callbacks
                    await self._call_callbacks("on_failed_attempt", address, f"Invalid key: 0x{received_key:04X}")
                    
                    # Send failure response (optional)
                    try:
                        failure_response = struct.pack('>H', 0x0000)  # Failure code
                        client_socket.send(failure_response)
                    except Exception as e:
                        self.logger.warning(f"Failed to send failure response: {e}")
                
        except socket.timeout:
            self.logger.warning(f"Activation request timeout from {address}")
            self.stats["failed_activations"] += 1
            await self._call_callbacks("on_failed_attempt", address, "Timeout")
        except Exception as e:
            self.logger.error(f"Error processing activation request from {address}: {e}")
            self.stats["failed_activations"] += 1
            await self._call_callbacks("on_failed_attempt", address, str(e))
    
    def _receive_exact_bytes(self, sock: socket.socket, num_bytes: int) -> bytes:
        """Receive exactly the specified number of bytes."""
        data = b''
        while len(data) < num_bytes:
            try:
                chunk = sock.recv(num_bytes - len(data))
                if not chunk:
                    raise ConnectionError("Connection closed by peer")
                data += chunk
            except socket.timeout:
                raise
            except Exception as e:
                self.logger.error(f"Error receiving data: {e}")
                raise
        return data
    
    async def _call_callbacks(self, callback_type: str, address: tuple, data: Any):
        """Call registered callbacks."""
        try:
            if callback_type in self.callbacks:
                for callback in self.callbacks[callback_type]:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(address, data)
                        else:
                            callback(address, data)
                    except Exception as e:
                        self.logger.error(f"Callback error: {e}")
        except Exception as e:
            self.logger.error(f"Error calling callbacks: {e}")
    
    def register_callback(self, callback_type: str, callback: Callable):
        """Register a callback function."""
        if callback_type in self.callbacks:
            self.callbacks[callback_type].append(callback)
            self.logger.info(f"Registered callback for {callback_type}")
        else:
            self.logger.warning(f"Unknown callback type: {callback_type}")
    
    def unregister_callback(self, callback_type: str, callback: Callable):
        """Unregister a callback function."""
        if callback_type in self.callbacks:
            if callback in self.callbacks[callback_type]:
                self.callbacks[callback_type].remove(callback)
                self.logger.info(f"Unregistered callback for {callback_type}")
        else:
            self.logger.warning(f"Unknown callback type: {callback_type}")
    
    async def activate_manually(self, source_ip: str = "manual") -> bool:
        """Manually activate the service."""
        try:
            self.logger.info(f"Manual activation triggered from {source_ip}")
            
            # Update activation state
            self.activation_state["activated"] = True
            self.activation_state["last_activation"] = datetime.now()
            self.activation_state["activation_count"] += 1
            self.activation_state["last_activator_ip"] = source_ip
            
            # Update statistics
            self.stats["successful_activations"] += 1
            
            # Call activation callbacks
            await self._call_callbacks("on_activation", (source_ip, 0), "manual")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Manual activation failed: {e}")
            return False
    
    async def deactivate(self) -> bool:
        """Deactivate the service."""
        try:
            self.logger.info("Deactivating service")
            
            # Update activation state
            old_state = self.activation_state["activated"]
            self.activation_state["activated"] = False
            
            # Call deactivation callbacks if was activated
            if old_state:
                await self._call_callbacks("on_deactivation", ("system", 0), "deactivated")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Deactivation failed: {e}")
            return False
    
    def is_activated(self) -> bool:
        """Check if the service is activated."""
        return self.activation_state["activated"]
    
    def get_activation_state(self) -> Dict[str, Any]:
        """Get the current activation state."""
        return self.activation_state.copy()
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the ARM module."""
        return {
            "module": self.module_name,
            "is_active": self.is_active,
            "is_listening": self.is_listening,
            "activation_state": self.activation_state,
            "statistics": self.stats,
            "network_settings": self.network_settings,
            "activation_key": f"0x{self.activation_key:04X}",
            "callbacks_registered": {k: len(v) for k, v in self.callbacks.items()}
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            # Check if listener is running
            listener_healthy = self.is_listening if self.is_active else True
            
            # Check recent activity
            recent_activity = False
            if self.stats["last_activity"]:
                time_diff = (datetime.now() - self.stats["last_activity"]).total_seconds()
                recent_activity = time_diff < 3600  # Activity within last hour
            
            return {
                "healthy": self.is_active and listener_healthy,
                "module": self.module_name,
                "timestamp": datetime.now().isoformat(),
                "listener_running": self.is_listening,
                "activation_state": self.activation_state["activated"],
                "recent_activity": recent_activity,
                "statistics": self.stats
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "module": self.module_name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            } 