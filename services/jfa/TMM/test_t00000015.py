"""
Test T00000015: API Test - Batch Processing Endpoint
Module(s) Tested: ARM, JDPM, TVM, BDM, DAM, OPM
Description: To test the POST /process/batch endpoint for processing multiple templates in one request.
Success Criteria: A 200 OK response with a JSON array containing two corresponding result objects.
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
    """Test API server for batch processing testing."""
    
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

async def test_t00000015():
    test_code = "T00000015"
    test_name = "API Test - Batch Processing Endpoint"
    results = []
    
    # Start the JFA service
    api_server = TestAPIServer()
    api_server.start()
    
    try:
        # Give server time to fully start
        await asyncio.sleep(3)
        
        # Step 1: Create a JSON array containing two valid template objects
        batch_templates = [
            {
                "request_id": "BATCH-001",
                "template_data": {
                    "system_id": "SOLAR-001",
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
                    ],
                    "total_system_wattage": 2880,
                    "installation_date": "2024-01-15",
                    "location": {
                        "latitude": 37.7749,
                        "longitude": -122.4194
                    }
                },
                "processing_options": {
                    "analysis_type": "comprehensive",
                    "include_binary": True,
                    "validation_level": "strict"
                }
            },
            {
                "request_id": "BATCH-002",
                "template_data": {
                    "system_id": "SOLAR-002",
                    "inverter": {
                        "model": "SMA-SB5000",
                        "capacity_kw": 5.0,
                        "efficiency": 0.97
                    },
                    "panels": [
                        {
                            "model": "SunPower-X22",
                            "wattage": 360,
                            "quantity": 12,
                            "efficiency": 0.225
                        }
                    ],
                    "total_system_wattage": 4320,
                    "installation_date": "2024-01-16",
                    "location": {
                        "latitude": 34.0522,
                        "longitude": -118.2437
                    }
                },
                "processing_options": {
                    "analysis_type": "comprehensive",
                    "include_binary": True,
                    "validation_level": "strict"
                }
            }
        ]
        
        # Step 2: Send a POST request to http://localhost:8001/process/batch with the array as the payload
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"http://localhost:8001/process/batch",
                    json={"batch_data": batch_templates},
                    headers={
                        "Content-Type": "application/json",
                        "X-API-Key": "test-api-key"  # Add API key for authentication
                    }
                ) as response:
                    status_code = response.status
                    response_data = await response.json()
                    
                    # Check if response is 200 OK
                    results.append(status_code == 200)
                    
                    # Check if response is a JSON array
                    results.append(isinstance(response_data, list))
                    
                    # Check if array contains two result objects
                    results.append(len(response_data) == 2)
                    
                    # Check if each result has the expected structure
                    if len(response_data) == 2:
                        result1 = response_data[0]
                        result2 = response_data[1]
                        
                        # Check basic result structure
                        results.append("request_id" in result1)
                        results.append("request_id" in result2)
                        results.append("success" in result1)
                        results.append("success" in result2)
                        
                        # Check if request IDs match
                        results.append(result1.get("request_id") == "BATCH-001")
                        results.append(result2.get("request_id") == "BATCH-002")
                        
                        # Check if processing results are present
                        results.append("processing_result" in result1 or "analysis_result" in result1)
                        results.append("processing_result" in result2 or "analysis_result" in result2)
                        
                        # Check if JFA_flag is present in results
                        results.append("JFA_flag" in result1)
                        results.append("JFA_flag" in result2)
                        
                        # Check if timestamps are present
                        results.append("timestamp" in result1)
                        results.append("timestamp" in result2)
                    else:
                        results.extend([False, False, False, False, False, False, False, False, False, False])
                    
                    # Test with invalid batch (empty array)
                    try:
                        async with session.post(
                            f"http://localhost:8001/process/batch",
                            json={"batch_data": []},
                            headers={
                                "Content-Type": "application/json",
                                "X-API-Key": "test-api-key"
                            }
                        ) as empty_response:
                            empty_status = empty_response.status
                            empty_data = await empty_response.json()
                            
                            # Should return error for empty batch
                            results.append(empty_status in [400, 422, 500])
                            results.append(
                                "empty" in str(empty_data).lower() or 
                                "invalid" in str(empty_data).lower() or
                                "error" in str(empty_data).lower()
                            )
                    except Exception as e:
                        print(f"Empty batch test failed: {e}")
                        results.extend([False, False])
                    
                    # Test with invalid batch (too many items)
                    large_batch = batch_templates * 50  # 100 templates
                    try:
                        async with session.post(
                            f"http://localhost:8001/process/batch",
                            json={"batch_data": large_batch},
                            headers={
                                "Content-Type": "application/json",
                                "X-API-Key": "test-api-key"
                            }
                        ) as large_response:
                            large_status = large_response.status
                            large_data = await large_response.json()
                            
                            # Should return error for too large batch
                            results.append(large_status in [400, 413, 422, 500])
                            results.append(
                                "size" in str(large_data).lower() or 
                                "limit" in str(large_data).lower() or
                                "too many" in str(large_data).lower() or
                                "error" in str(large_data).lower()
                            )
                    except Exception as e:
                        print(f"Large batch test failed: {e}")
                        results.extend([False, False])
                    
            except Exception as e:
                print(f"Batch processing test failed: {e}")
                results.extend([False, False, False, False, False, False, False, False, False, False, False, False, False, False])
        
        success = all(results)
        
        return {
            "success": success,
            "test_code": test_code,
            "test_name": test_name,
            "message": "Batch processing API test passed" if success else "Batch processing API test failed",
            "details": {
                "response_status_200": results[0],
                "response_is_json_array": results[1],
                "array_has_two_results": results[2],
                "result1_has_request_id": results[3],
                "result2_has_request_id": results[4],
                "result1_has_success": results[5],
                "result2_has_success": results[6],
                "request_id1_matches": results[7],
                "request_id2_matches": results[8],
                "result1_has_processing_result": results[9],
                "result2_has_processing_result": results[10],
                "result1_has_jfa_flag": results[11],
                "result2_has_jfa_flag": results[12],
                "result1_has_timestamp": results[13],
                "result2_has_timestamp": results[14],
                "empty_batch_rejected": results[15] if len(results) > 15 else False,
                "empty_batch_error_message": results[16] if len(results) > 16 else False,
                "large_batch_rejected": results[17] if len(results) > 17 else False,
                "large_batch_error_message": results[18] if len(results) > 18 else False,
                "response_data": response_data if 'response_data' in locals() else {},
                "results": results
            }
        }
        
    finally:
        api_server.stop()