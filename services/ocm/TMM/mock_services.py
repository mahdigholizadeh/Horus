"""
Mock Services for OCM Testing

This module provides mock implementations of external dependencies
used by the OCM microservice for testing purposes.
"""

import asyncio
import json
import logging
import websockets
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

class MockWebSocketServer:
    """Mock WebSocket server for CCU simulation."""
    
    def __init__(self, host: str = "localhost", port: int = 8080):
        self.host = host
        self.port = port
        self.server = None
        self.clients = []
        self.messages_received = []
        self.messages_sent = []
        self.logger = logging.getLogger(__name__)
        
    async def start(self):
        """Start the mock WebSocket server."""
        try:
            # Create a simple handler that works with websockets 15.0.1
            async def simple_handler(websocket):
                path = getattr(websocket, 'path', '/unknown')
                self.clients.append(websocket)
                self.logger.info(f"Client connected to path '{path}'. Total clients: {len(self.clients)}")
                
                try:
                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            self.messages_received.append(data)
                            self.logger.info(f"Received message: {data.get('type', 'unknown')}")
                            
                            # Handle different message types
                            response = await self._process_message(data)
                            if response:
                                await websocket.send(json.dumps(response))
                                self.messages_sent.append(response)
                        except json.JSONDecodeError:
                            self.logger.warning("Received invalid JSON message")
                        except Exception as e:
                            self.logger.error(f"Error processing message: {e}")
                            
                except websockets.exceptions.ConnectionClosed:
                    pass
                except Exception as e:
                    self.logger.error(f"Error handling client: {e}")
                finally:
                    if websocket in self.clients:
                        self.clients.remove(websocket)
                    self.logger.info(f"Client disconnected. Total clients: {len(self.clients)}")
            
            # Start the server with the simple handler
            self.server = await websockets.serve(simple_handler, self.host, self.port)
            self.logger.info(f"Mock WebSocket server started on {self.host}:{self.port}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to start mock server: {e}")
            return False
    
    async def stop(self):
        """Stop the mock WebSocket server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.logger.info("Mock WebSocket server stopped")
    
    async def _process_message(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process incoming messages and return appropriate responses."""
        msg_type = data.get('type')
        
        if msg_type == 'service_registration':
            return {
                "type": "registration_ack",
                "status": "accepted",
                "service_id": "ocm_001",
                "registration_token": "reg_token_12345",
                "timestamp": datetime.now().isoformat(),
                "capabilities_confirmed": data.get('capabilities', []),
                "configuration_confirmed": data.get('configuration', {})
            }
        
        elif msg_type == 'heartbeat':
            return {
                "type": "heartbeat_ack",
                "timestamp": datetime.now().isoformat()
            }
        
        elif msg_type == 'certificate_update':
            return {
                "type": "certificate_ack",
                "status": "received",
                "timestamp": datetime.now().isoformat()
            }
        
        elif msg_type == 'authentication':
            return {
                "type": "auth_ack",
                "status": "authenticated",
                "timestamp": datetime.now().isoformat()
            }
        
        elif msg_type == 'test':
            return {
                "type": "test_response",
                "status": "ok",
                "timestamp": datetime.now().isoformat()
            }
        
        return None

class MockPDFEngine:
    """Mock PDF generation engine."""
    
    def __init__(self):
        self.generated_pdfs = []
        self.logger = logging.getLogger(__name__)
    
    def generate_pdf(self, html_content: str, output_path: str) -> bool:
        """Mock PDF generation."""
        try:
            # Create a mock PDF file
            mock_pdf_content = f"Mock PDF content for: {html_content[:50]}..."
            Path(output_path).write_text(mock_pdf_content)
            self.generated_pdfs.append(output_path)
            self.logger.info(f"Mock PDF generated: {output_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to generate mock PDF: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if PDF engine is available."""
        return True

class MockSSLManager:
    """Mock SSL certificate manager."""
    
    def __init__(self):
        self.certificates = {
            'cert_content': '-----BEGIN CERTIFICATE-----\nMOCK_CERT_CONTENT\n-----END CERTIFICATE-----',
            'key_content': '-----BEGIN PRIVATE KEY-----\nMOCK_KEY_CONTENT\n-----END PRIVATE KEY-----',
            'expires_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        self.logger = logging.getLogger(__name__)
    
    def get_certificates(self) -> Dict[str, Any]:
        """Get mock SSL certificates."""
        return self.certificates.copy()
    
    def update_certificates(self, cert_data: Dict[str, Any]) -> bool:
        """Update mock SSL certificates."""
        try:
            self.certificates.update(cert_data)
            self.certificates['updated_at'] = datetime.now().isoformat()
            self.logger.info("Mock SSL certificates updated")
            return True
        except Exception as e:
            self.logger.error(f"Failed to update mock SSL certificates: {e}")
            return False
    
    def is_valid(self) -> bool:
        """Check if certificates are valid."""
        return True

class MockDatabase:
    """Mock database for testing."""
    
    def __init__(self):
        self.data = {}
        self.logger = logging.getLogger(__name__)
    
    async def connect(self) -> bool:
        """Mock database connection."""
        self.logger.info("Mock database connected")
        return True
    
    async def disconnect(self) -> bool:
        """Mock database disconnection."""
        self.logger.info("Mock database disconnected")
        return True
    
    async def execute(self, query: str, params: Dict[str, Any] = None) -> bool:
        """Mock query execution."""
        self.logger.info(f"Mock query executed: {query}")
        return True
    
    async def fetch_one(self, query: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Mock fetch one result."""
        return {"id": 1, "status": "mock"}
    
    async def fetch_all(self, query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Mock fetch all results."""
        return [{"id": 1, "status": "mock"}]

class TestEnvironment:
    """Test environment manager."""
    
    def __init__(self):
        self.mock_websocket_server = None
        self.mock_pdf_engine = None
        self.mock_ssl_manager = None
        self.mock_database = None
        self.logger = logging.getLogger(__name__)
    
    async def setup(self, websocket_port: int = 8080):
        """Set up the test environment."""
        try:
            # Start mock WebSocket server
            self.mock_websocket_server = MockWebSocketServer(port=websocket_port)
            await self.mock_websocket_server.start()
            
            # Initialize mock services
            self.mock_pdf_engine = MockPDFEngine()
            self.mock_ssl_manager = MockSSLManager()
            self.mock_database = MockDatabase()
            
            self.logger.info("Test environment setup completed")
            return True
        except Exception as e:
            self.logger.error(f"Failed to setup test environment: {e}")
            return False
    
    async def teardown(self):
        """Tear down the test environment."""
        try:
            if self.mock_websocket_server:
                await self.mock_websocket_server.stop()
            
            self.logger.info("Test environment teardown completed")
            return True
        except Exception as e:
            self.logger.error(f"Failed to teardown test environment: {e}")
            return False
    
    def get_mock_services(self) -> Dict[str, Any]:
        """Get all mock services."""
        return {
            'websocket_server': self.mock_websocket_server,
            'pdf_engine': self.mock_pdf_engine,
            'ssl_manager': self.mock_ssl_manager,
            'database': self.mock_database
        } 