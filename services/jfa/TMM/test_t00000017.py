"""
Test T00000017: E2E Pipeline Failure (Validation Stage)
Module(s) Tested: IPM, JDPM, TVM
Description: To test how the pipeline handles a failure at an early stage (TVM).
Success Criteria: Processing halted at TVM stage, response contains clear validation error, pipeline does not proceed to BDM or DAM stages.
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
    """Test API server for pipeline failure testing."""
    
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

async def test_t00000017():
    test_code = "T00000017"
    test_name = "E2E Pipeline Failure (Validation Stage)"
    results = []
    
    # Start the JFA service
    api_server = TestAPIServer()
    api_server.start()
    
    try:
        # Give server time to fully start
        await asyncio.sleep(3)
        
        # Step 1: Create a request template with a clear business rule violation
        invalid_request_template = {
            "request_id": "E2E-FAIL-001",
            "template_data": {
                "system_id": "SOLAR-E2E-FAIL-001",
                "inverter": {
                    "model": "SMA-SB2000",
                    "capacity_kw": 2.0,  # 2000W capacity
                    "efficiency": 0.96,
                    "manufacturer": "SMA Solar Technology",
                    "warranty_years": 10
                },
                "panels": [
                    {
                        "model": "SunPower-X22",
                        "wattage": 360,
                        "quantity": 10,
                        "efficiency": 0.225,
                        "manufacturer": "SunPower",
                        "warranty_years": 25
                    }
                ],
                "total_system_wattage": 3600,  # 10 * 360 = 3600W > 2000W inverter capacity
                "installation_date": "2024-01-15",
                "location": {
                    "latitude": 37.7749,
                    "longitude": -122.4194,
                    "address": "123 Solar Street, San Francisco, CA",
                    "timezone": "America/Los_Angeles"
                }
            },
            "processing_options": {
                "analysis_type": "comprehensive",
                "include_binary": True,
                "validation_level": "strict"
            }
        }
        
        # Step 2: Send a POST request to /process with the invalid template
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"http://localhost:8001/process",
                    json=invalid_request_template,
                    headers={
                        "Content-Type": "application/json",
                        "X-API-Key": "test-api-key"
                    }
                ) as response:
                    status_code = response.status
                    response_data = await response.json()
                    
                    # Check if request was properly rejected
                    results.append(status_code in [400, 422])  # Bad Request or Unprocessable Entity
                    
                    # Check if response indicates failure
                    results.append(not response_data.get("success", True))
                    
                    # Check if error message is present
                    error_message = response_data.get("error", "")
                    results.append(len(error_message) > 0)
                    
                    # Check if error message clearly states the validation rule that failed
                    error_lower = error_message.lower()
                    validation_keywords = [
                        "inverter", "capacity", "insufficient", "mismatch", 
                        "validation", "rule", "violation", "exceed"
                    ]
                    validation_error_detected = any(keyword in error_lower for keyword in validation_keywords)
                    results.append(validation_error_detected)
                    
                    # Check if processing was halted at TVM stage
                    processing_summary = response_data.get("processing_summary", {})
                    modules_executed = processing_summary.get("modules_executed", [])
                    
                    # Should have executed IPM and JDPM, but not BDM or DAM
                    results.append("IPM" in modules_executed)
                    results.append("JDPM" in modules_executed)
                    results.append("TVM" in modules_executed)
                    results.append("BDM" not in modules_executed)
                    results.append("DAM" not in modules_executed)
                    
                    # Check if error details are provided
                    error_details = response_data.get("error_details", {})
                    results.append(isinstance(error_details, dict))
                    
                    # Check if stage where failure occurred is specified
                    failure_stage = response_data.get("failure_stage", "")
                    results.append(failure_stage == "TVM" or "validation" in failure_stage.lower())
                    
                    # Check if request ID is preserved in error response
                    results.append(response_data.get("request_id") == "E2E-FAIL-001")
                    
                    # Check if timestamp is present
                    results.append("timestamp" in response_data)
                    
                    # Test with another validation failure (missing required field)
                    missing_field_template = {
                        "request_id": "E2E-FAIL-002",
                        "template_data": {
                            "system_id": "SOLAR-E2E-FAIL-002",
                            "inverter": {
                                "model": "SMA-SB3000",
                                "capacity_kw": 3.0
                                # Missing efficiency field
                            }
                            # Missing panels, total_system_wattage, installation_date, location
                        }
                    }
                    
                    async with session.post(
                        f"http://localhost:8001/process",
                        json=missing_field_template,
                        headers={
                            "Content-Type": "application/json",
                            "X-API-Key": "test-api-key"
                        }
                    ) as missing_response:
                        missing_status = missing_response.status
                        missing_data = await missing_response.json()
                        
                        # Should also be rejected
                        results.append(missing_status in [400, 422])
                        results.append(not missing_data.get("success", True))
                        
                        # Should mention missing fields
                        missing_error = missing_data.get("error", "").lower()
                        missing_field_detected = any(keyword in missing_error for keyword in ["missing", "required", "field"])
                        results.append(missing_field_detected)
                        
                        # Should not proceed to later stages
                        missing_modules = missing_data.get("processing_summary", {}).get("modules_executed", [])
                        results.append("BDM" not in missing_modules)
                        results.append("DAM" not in missing_modules)
                    
            except Exception as e:
                print(f"E2E pipeline failure test failed: {e}")
                results.extend([False] * 15)  # Fill with False for all expected results
        
        success = all(results)
        
        return {
            "success": success,
            "test_code": test_code,
            "test_name": test_name,
            "message": "E2E pipeline failure test passed" if success else "E2E pipeline failure test failed",
            "details": {
                "request_properly_rejected": results[0],
                "response_indicates_failure": results[1],
                "error_message_present": results[2],
                "validation_error_detected": results[3],
                "ipm_stage_executed": results[4],
                "jdpm_stage_executed": results[5],
                "tvm_stage_executed": results[6],
                "bdm_stage_not_executed": results[7],
                "dam_stage_not_executed": results[8],
                "error_details_provided": results[9],
                "failure_stage_specified": results[10],
                "request_id_preserved": results[11],
                "timestamp_present": results[12],
                "missing_field_rejected": results[13],
                "missing_field_error_detected": results[14],
                "missing_field_pipeline_halted": results[15] if len(results) > 15 else False,
                "missing_field_later_stages_skipped": results[16] if len(results) > 16 else False,
                "error_message": error_message if 'error_message' in locals() else "",
                "failure_stage": failure_stage if 'failure_stage' in locals() else "",
                "results": results
            }
        }
        
    finally:
        api_server.stop()