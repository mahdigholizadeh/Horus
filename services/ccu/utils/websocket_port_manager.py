"""
WebSocket Port Manager

Handles port availability checking, fallback logic, and WebSocket server/client management
for the CCU-Microservice communication architecture.

Architecture: 6 WebSocket servers in CCU (one per interaction module)
"""

import asyncio
import json
import logging
import socket
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import websockets
from datetime import datetime


class WebSocketPortManager:
    """Manages WebSocket ports for CCU and microservices with fallback logic."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the port manager with configuration."""
        self.logger = logging.getLogger(__name__)
        
        # Load WebSocket port configuration
        if config_path is None:
            config_path = Path(__file__).parent.parent / "ccu_setting" / "websocket_ports.json"
        
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
            self.logger.info(f"Loaded WebSocket port configuration from {config_path}")
        except Exception as e:
            self.logger.error(f"Failed to load WebSocket port config: {e}")
            # Fallback to default configuration
            self.config = self._get_default_config()
        
        # Port allocation tracking
        self.allocated_ports = {}
        self.server_instances = {}
        
    def _get_default_config(self) -> Dict:
        """Get default configuration if config file fails to load."""
        return {
            "port_fallback_logic": {
                "enabled": True,
                "fallback_increment": 10,
                "connection_timeout_ms": 5000,
                "max_fallback_attempts": 3
            },
            "ccu_websocket_servers": {
                "RLAIM": {"primary_port": 4441, "fallback_ports": [4451, 4461, 4471]},
                "TPPIM": {"primary_port": 4442, "fallback_ports": [4452, 4462, 4472]},
                "RCMIM": {"primary_port": 4443, "fallback_ports": [4453, 4463, 4473]},
                "JFAIM": {"primary_port": 4444, "fallback_ports": [4454, 4464, 4474]},
                "TDIM": {"primary_port": 4445, "fallback_ports": [4455, 4465, 4475]},
                "OCMIM": {"primary_port": 4446, "fallback_ports": [4456, 4466, 4476]}
            },
            "microservice_ecm_clients": {
                "RLA": {"connects_to_ccu_port": 4441, "local_binding_port": 3331},
                "TPP": {"connects_to_ccu_port": 4442, "local_binding_port": 3332},
                "RCM": {"connects_to_ccu_port": 4443, "local_binding_port": 3333},
                "JFA": {"connects_to_ccu_port": 4444, "local_binding_port": 3334},
                "TD": {"connects_to_ccu_port": 4445, "local_binding_port": 3335},
                "OCM": {"connects_to_ccu_port": 4446, "local_binding_port": 3336}
            }
        }
    
    def is_port_available(self, port: int, host: str = "127.0.0.1") -> bool:
        """Check if a port is available for binding."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((host, port))
                return True
        except OSError:
            return False
    
    def get_available_port(self, primary_port: int, fallback_ports: List[int]) -> Optional[int]:
        """Get an available port using fallback logic."""
        # Try primary port first
        if self.is_port_available(primary_port):
            self.logger.info(f"Primary port {primary_port} is available")
            return primary_port
        
        # Try fallback ports
        for fallback_port in fallback_ports:
            if self.is_port_available(fallback_port):
                self.logger.info(f"Using fallback port {fallback_port} (primary {primary_port} was busy)")
                return fallback_port
        
        # No ports available
        self.logger.error(f"No available ports found. Tried: {primary_port}, {fallback_ports}")
        return None
    
    def get_ccu_server_port(self, interaction_module: str) -> Optional[int]:
        """Get available port for CCU WebSocket server (interaction module)."""
        server_config = self.config["ccu_websocket_servers"].get(interaction_module)
        if not server_config:
            self.logger.error(f"No configuration found for CCU interaction module: {interaction_module}")
            return None
        
        primary_port = server_config["primary_port"]
        fallback_ports = server_config["fallback_ports"]
        
        available_port = self.get_available_port(primary_port, fallback_ports)
        if available_port:
            self.allocated_ports[interaction_module] = available_port
        
        return available_port
    
    def get_microservice_connection_info(self, microservice: str) -> Optional[Dict]:
        """Get connection info for microservice ECM client."""
        client_config = self.config["microservice_ecm_clients"].get(microservice)
        if not client_config:
            self.logger.error(f"No configuration found for microservice: {microservice}")
            return None
        
        return {
            "ccu_server_port": client_config["connects_to_ccu_port"],
            "local_binding_port": client_config["local_binding_port"],
            "fallback_ports": client_config.get("fallback_ports", []),
            "connection_timeout_ms": self.config["port_fallback_logic"]["connection_timeout_ms"]
        }
    
    async def start_ccu_websocket_server(self, interaction_module: str, message_handler) -> Optional[websockets.WebSocketServer]:
        """Start a WebSocket server for a CCU interaction module."""
        port = self.get_ccu_server_port(interaction_module)
        if not port:
            return None
        
        try:
            self.logger.info(f"Starting {interaction_module} WebSocket server on port {port}")
            
            server = await websockets.serve(
                message_handler,
                "127.0.0.1",
                port,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            
            self.server_instances[interaction_module] = {
                "server": server,
                "port": port,
                "started_at": datetime.now()
            }
            
            self.logger.info(f"✅ {interaction_module} WebSocket server started successfully on port {port}")
            return server
            
        except Exception as e:
            import traceback
            self.logger.error(f"Failed to start {interaction_module} WebSocket server on port {port}: {e}")
            self.logger.error(f"Full error traceback: {traceback.format_exc()}")
            
            # Try to diagnose the specific issue
            if "Address already in use" in str(e):
                self.logger.error(f"Port {port} is already in use by another process")
            elif "Permission denied" in str(e):
                self.logger.error(f"Permission denied binding to port {port} - may need elevated privileges")
            elif "Cannot assign requested address" in str(e):
                self.logger.error(f"Cannot bind to 0.0.0.0:{port} - network interface issue")
            
            return None
    
    async def connect_to_ccu_server(self, microservice: str, max_retries: int = 3) -> Optional[websockets.WebSocketClientProtocol]:
        """Connect microservice ECM to CCU WebSocket server with fallback logic."""
        connection_info = self.get_microservice_connection_info(microservice)
        if not connection_info:
            return None
        
        primary_port = connection_info["ccu_server_port"]
        timeout_ms = connection_info["connection_timeout_ms"]
        timeout_seconds = timeout_ms / 1000.0
        
        # Try primary port first
        uri = f"ws://localhost:{primary_port}/ws"
        
        for attempt in range(max_retries):
            try:
                self.logger.info(f"Attempt {attempt + 1}: {microservice} ECM connecting to {uri}")
                
                websocket = await asyncio.wait_for(
                    websockets.connect(
                        uri,
                        ping_interval=20,
                        ping_timeout=10,
                        close_timeout=10
                    ),
                    timeout=timeout_seconds
                )
                
                self.logger.info(f"✅ {microservice} ECM connected successfully to {uri}")
                return websocket
                
            except asyncio.TimeoutError:
                self.logger.warning(f"⏱️ {microservice} ECM connection timeout to {uri} after {timeout_seconds}s")
                
                # Try fallback port
                fallback_port = primary_port + 10
                uri = f"ws://localhost:{fallback_port}/ws"
                self.logger.info(f"Trying fallback port: {fallback_port}")
                
            except Exception as e:
                self.logger.error(f"❌ {microservice} ECM connection failed to {uri}: {e}")
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)  # Wait before retry
        
        self.logger.error(f"❌ {microservice} ECM failed to connect after {max_retries} attempts")
        return None
    
    def get_server_status(self) -> Dict:
        """Get status of all running WebSocket servers."""
        status = {
            "allocated_ports": self.allocated_ports.copy(),
            "running_servers": {},
            "total_servers": len(self.server_instances)
        }
        
        for module, server_info in self.server_instances.items():
            status["running_servers"][module] = {
                "port": server_info["port"],
                "started_at": server_info["started_at"].isoformat(),
                "is_serving": server_info["server"].is_serving() if hasattr(server_info["server"], 'is_serving') else True
            }
        
        return status
    
    async def stop_all_servers(self):
        """Stop all running WebSocket servers."""
        self.logger.info("Stopping all WebSocket servers...")
        
        for module, server_info in self.server_instances.items():
            try:
                server = server_info["server"]
                server.close()
                await server.wait_closed()
                self.logger.info(f"Stopped {module} WebSocket server on port {server_info['port']}")
            except Exception as e:
                self.logger.error(f"Error stopping {module} WebSocket server: {e}")
        
        self.server_instances.clear()
        self.allocated_ports.clear()
        self.logger.info("All WebSocket servers stopped")


# Global instance for easy access
websocket_port_manager = WebSocketPortManager()