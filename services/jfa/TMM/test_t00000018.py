"""
Test T00000018: Security Test - API Key Authentication
Module(s) Tested: ARM, IPM
Description: To verify that endpoints are protected by API key authentication.
Success Criteria: Request without API key is rejected with 401/403, request with valid API key is accepted.
"""

import asyncio
import json
import sys
import aiohttp
import uvicorn
import threading
import time
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

class TestAPIServer:
    """Test API server for authentication testing."""
    
    def __init__(self, port=8001):
        self.port = port
        self.server = None
        self.thread = None
        self.arm_module = None
        
    def start_server(self):
        """Start the API server in a separate thread."""
        async def run_server():
            from ARM.arm import APIRequestModule
            self.arm_module = APIRequestModule()
            await self.arm_module.start()
            await self.arm_module.start_api_server(self.port)
            # Keep the server running
            while True:
                await asyncio.sleep(1)
        
        # Run the async function in the thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_server())
        
    def start(self):
        """Start the server in background thread."""
        self.thread = threading.Thread(target=self.start_server, daemon=True)
        self.thread.start()
        time.sleep(3)  # Give server time to start
        
    def stop(self):
        """Stop the server."""
        if self.arm_module:
            # Create a new event loop for stopping
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.arm_module.stop())
                loop.close()
            except Exception as e:
                print(f"Warning: Error stopping server: {e}")
        if self.thread:
            self.thread.join(timeout=5)

async def test_t00000018():
    test_code = "T00000018"
    test_name = "Security Test - API Key Authentication"
    results = []
    
    # Start the JFA service
    api_server = TestAPIServer()
    api_server.start()
    
    try:
        # Give server time to fully start
        await asyncio.sleep(3)
        
        # Test payload
        test_template = {
            "request_id": "SECURITY-TEST-001",
            "template_data": {
                "system_id": "SOLAR-SEC-001",
                "inverter": {
                    "model": "SMA-SB3000",
                    "capacity_kw": 3.0,
                    "efficiency": 0.96
                },
                "panels": [
                    {
                        "model": "SunPower-X22",
                        "wattage": 360,
                        "quantity": 8,
                        "efficiency": 0.225
                    }
                ]
            }
        }
        
        async with aiohttp.ClientSession() as session:
            # Step 1: Send a POST request to /process without a valid API key in the header
            try:
                async with session.post(
                    f"http://localhost:8001/process",
                    json=test_template,
                    headers={"Content-Type": "application/json"}
                    # No X-API-Key header
                ) as response:
                    status_code = response.status
                    response_data = await response.json()
                    
                    # The first request should be rejected with a 401 Unauthorized or 403 Forbidden status
                    results.append(status_code in [401, 403])
                    
                    # Check if error message indicates authentication failure
                    error_message = response_data.get("error", "").lower()
                    auth_error_detected = any(keyword in error_message for keyword in [
                        "unauthorized", "forbidden", "authentication", "api key", "key", "auth"
                    ])
                    results.append(auth_error_detected)
                    
            except Exception as e:
                print(f"Request without API key failed: {e}")
                results.extend([False, False])
            
            # Step 2: Send a POST request to /process with a valid API key
            try:
                async with session.post(
                    f"http://localhost:8001/process",
                    json=test_template,
                    headers={
                        "Content-Type": "application/json",
                        "X-API-Key": "test-api-key"
                    }
                ) as response:
                    status_code = response.status
                    response_data = await response.json()
                    
                    # The second request should be accepted for processing
                    results.append(status_code in [200, 400, 422])  # Success or validation error (but not auth error)
                    
                    # Should not be an authentication error
                    error_message = response_data.get("error", "").lower()
                    auth_error_not_present = not any(keyword in error_message for keyword in [
                        "unauthorized", "forbidden", "authentication", "api key", "key", "auth"
                    ])
                    results.append(auth_error_not_present)
                    
            except Exception as e:
                print(f"Request with API key failed: {e}")
                results.extend([False, False])
            
            # Test with invalid API key
            try:
                async with session.post(
                    f"http://localhost:8001/process",
                    json=test_template,
                    headers={
                        "Content-Type": "application/json",
                        "X-API-Key": "invalid-api-key"
                    }
                ) as response:
                    status_code = response.status
                    response_data = await response.json()
                    
                    # Should be rejected
                    results.append(status_code in [401, 403])
                    
                    # Should indicate invalid API key
                    error_message = response_data.get("error", "").lower()
                    invalid_key_detected = any(keyword in error_message for keyword in [
                        "invalid", "unauthorized", "forbidden", "authentication", "api key", "key"
                    ])
                    results.append(invalid_key_detected)
                    
            except Exception as e:
                print(f"Request with invalid API key failed: {e}")
                results.extend([False, False])
            
            # Test with malformed API key header
            try:
                async with session.post(
                    f"http://localhost:8001/process",
                    json=test_template,
                    headers={
                        "Content-Type": "application/json",
                        "X-API-Key": ""  # Empty API key
                    }
                ) as response:
                    status_code = response.status
                    response_data = await response.json()
                    
                    # Should be rejected
                    results.append(status_code in [401, 403])
                    
            except Exception as e:
                print(f"Request with empty API key failed: {e}")
                results.append(False)
            
            # Test batch endpoint authentication
            batch_payload = [test_template]
            
            # Without API key
            try:
                async with session.post(
                    f"http://localhost:8001/process/batch",
                    json={"batch_data": batch_payload},
                    headers={"Content-Type": "application/json"}
                ) as response:
                    status_code = response.status
                    results.append(status_code in [401, 403])
                    
            except Exception as e:
                print(f"Batch request without API key failed: {e}")
                results.append(False)
            
            # With API key
            try:
                async with session.post(
                    f"http://localhost:8001/process/batch",
                    json={"batch_data": batch_payload},
                    headers={
                        "Content-Type": "application/json",
                        "X-API-Key": "test-api-key"
                    }
                ) as response:
                    status_code = response.status
                    results.append(status_code in [200, 400, 422])
                    
            except Exception as e:
                print(f"Batch request with API key failed: {e}")
                results.append(False)
            
            # Test health endpoint (should not require authentication)
            try:
                async with session.get(f"http://localhost:8001/health") as response:
                    status_code = response.status
                    results.append(status_code == 200)
                    
            except Exception as e:
                print(f"Health endpoint test failed: {e}")
                results.append(False)
        
        success = all(results)
        
        return {
            "success": success,
            "test_code": test_code,
            "test_name": test_name,
            "message": "API key authentication test passed" if success else "API key authentication test failed",
            "details": {
                "request_without_key_rejected": results[0],
                "auth_error_message_present": results[1],
                "request_with_key_accepted": results[2],
                "auth_error_not_present": results[3],
                "invalid_key_rejected": results[4],
                "invalid_key_error_detected": results[5],
                "empty_key_rejected": results[6],
                "batch_without_key_rejected": results[7],
                "batch_with_key_accepted": results[8],
                "health_endpoint_accessible": results[9],
                "results": results
            }
        }
        
    finally:
        api_server.stop() 