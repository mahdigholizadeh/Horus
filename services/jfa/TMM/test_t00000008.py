"""
Test T00000008: ECM (External Control Module) Unit Test
Module(s) Tested: ECM
Description: To verify that the ECM correctly establishes WebSocket connections with the CCU and handles service registration.
Success Criteria: Connection established, service registration sent, auto-reconnect works.
"""

import asyncio
import json
import sys
import time
import websockets
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ECM.ecm import ExternalControlModule

class MockCCUServer:
    """Mock CCU WebSocket server for testing."""
    
    def __init__(self, host="localhost", port=11491):
        self.host = host
        self.port = port
        self.server = None
        self.clients = set()
        self.messages_received = []
        self.registration_received = False
        
    async def start(self):
        """Start the mock CCU server."""
        try:
            self.server = await websockets.serve(
                self.handle_client, self.host, self.port
            )
            # Suppress print statement to avoid output pollution
            # print(f"Mock CCU server started on ws://{self.host}:{self.port}")
            return True
        except Exception as e:
            # Suppress print statement to avoid output pollution
            # print(f"Failed to start mock server: {e}")
            return False
        
    async def stop(self):
        """Stop the mock CCU server."""
        if self.server:
            try:
                self.server.close()
                await self.server.wait_closed()
            except Exception as e:
                print(f"Error stopping mock server: {e}")
            
    async def handle_client(self, websocket):
        """Handle client connections."""
        self.clients.add(websocket)
        try:
            async for message in websocket:
                try:
                    self.messages_received.append(json.loads(message))
                    
                    # Check if this is a registration message
                    if isinstance(self.messages_received[-1], dict):
                        msg = self.messages_received[-1]
                        if msg.get("type") == "service_registration" and msg.get("service") == "JFA":
                            self.registration_received = True
                            
                    # Send acknowledgment
                    await websocket.send(json.dumps({
                        "type": "acknowledgment",
                        "status": "received",
                        "timestamp": time.time()
                    }))
                except json.JSONDecodeError:
                    pass
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.discard(websocket)

async def test_t00000008():
    test_code = "T00000008"
    test_name = "ECM - External Control Module Unit Test"
    results = []
    
    # Step 1: Start a mock CCU WebSocket server on ws://localhost:11491
    mock_server = MockCCUServer()
    server_started = await mock_server.start()
    
    if not server_started:
        # If server couldn't start, try alternative port
        mock_server = MockCCUServer(port=11492)
        server_started = await mock_server.start()
    
    if not server_started:
        # If still can't start, skip the test
        return {
            "success": False,
            "test_code": test_code,
            "test_name": test_name,
            "message": "ECM unit test failed - could not start mock server",
            "details": {
                "error": "Port conflict - mock server could not start",
                "results": [False, False, False, False, False, False]
            }
        }
    
    try:
        # Step 2: Initialize the ECM
        ecm = ExternalControlModule()
        await ecm.start()
        
        # Give some time for connection to establish
        await asyncio.sleep(2)
        
        # Step 3: Verify that the ECM automatically attempts to connect and sends a service registration message
        results.append(ecm.connection_status == "connected")
        results.append(mock_server.registration_received)
        
        # Check if registration message was received
        if mock_server.messages_received:
            registration_msg = next(
                (msg for msg in mock_server.messages_received 
                 if msg.get("type") == "service_registration"), 
                None
            )
            results.append(registration_msg is not None)
            
            if registration_msg:
                # Verify registration message structure
                results.append(registration_msg.get("service") == "JFA")
                results.append("capabilities" in registration_msg)
                results.append("status" in registration_msg)
            else:
                results.extend([False, False, False])
        else:
            results.extend([False, False, False, False, False])
        
        # Step 4: Test the auto-reconnect logic by shutting down and restarting the mock server
        await mock_server.stop()
        await asyncio.sleep(1)
        
        # Check if ECM detected disconnection
        results.append(ecm.connection_status == "disconnected")
        
        # Restart mock server
        await mock_server.start()
        await asyncio.sleep(3)  # Give time for reconnection
        
        # Check if ECM reconnected
        results.append(ecm.connection_status == "connected")
        
        success = all(results)
        
        return {
            "success": success,
            "test_code": test_code,
            "test_name": test_name,
            "message": "ECM unit test passed" if success else "ECM unit test failed",
            "details": {
                "connection_established": results[0] if len(results) > 0 else False,
                "registration_sent": results[1] if len(results) > 1 else False,
                "registration_message_received": results[2] if len(results) > 2 else False,
                "service_name_correct": results[3] if len(results) > 3 else False,
                "capabilities_included": results[4] if len(results) > 4 else False,
                "status_included": results[5] if len(results) > 5 else False,
                "disconnection_detected": results[6] if len(results) > 6 else False,
                "reconnection_successful": results[7] if len(results) > 7 else False,
                "results": results
            }
        }
        
    finally:
        await mock_server.stop()
        await ecm.stop()