"""
Test T00000016: E2E Happy Path Scenario
Module(s) Tested: IPM, JDPM, TVM, BDM, DAM, OPM, ARM
Description: To test a complete, successful request flow from input to a fully analyzed output.
Success Criteria: Request passes through all 5 pipeline stages successfully, final output contains high-quality score, success decision, binary data reference, and JFA_flag.
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

from JFA_main import JFAMicroservice

class TestAPIServer:
    """Test API server for E2E testing."""
    
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

async def test_t00000016():
    test_code = "T00000016"
    test_name = "E2E Happy Path Scenario"
    results = []
    
    # Start the JFA service
    api_server = TestAPIServer()
    api_server.start()
    
    try:
        # Give server time to fully start
        await asyncio.sleep(3)
        
        # Step 1: Create a valid request template JSON that passes schema and business rule checks
        valid_request_template = {
            "request_id": "E2E-HAPPY-001",
            "template_data": {
                "system_id": "SOLAR-E2E-001",
                "inverter": {
                    "model": "SMA-SB4000",
                    "capacity_kw": 4.0,
                    "efficiency": 0.97,
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
                "total_system_wattage": 3600,  # 10 * 360 = 3600W
                "installation_date": "2024-01-15",
                "location": {
                    "latitude": 37.7749,
                    "longitude": -122.4194,
                    "address": "123 Solar Street, San Francisco, CA",
                    "timezone": "America/Los_Angeles"
                },
                "system_configuration": {
                    "racking_system": "Ground Mount",
                    "tilt_angle": 30,
                    "azimuth": 180,
                    "shading_analysis": "None"
                },
                "financial_data": {
                    "total_cost": 15000,
                    "incentives": 3000,
                    "net_cost": 12000,
                    "expected_annual_savings": 1800
                }
            },
            "processing_options": {
                "analysis_type": "comprehensive",
                "include_binary": True,
                "validation_level": "strict",
                "include_financial_analysis": True,
                "include_performance_prediction": True
            }
        }
        
        # Step 2: Send a POST request to /process with the template
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"http://localhost:8001/process",
                    json=valid_request_template,
                    headers={
                        "Content-Type": "application/json",
                        "X-API-Key": "test-api-key"
                    }
                ) as response:
                    status_code = response.status
                    response_data = await response.json()
                    
                    # Check if request was successful
                    results.append(status_code == 200)
                    results.append(response_data.get("success", False))
                    
                    # Check if all 5 pipeline stages were executed
                    processing_summary = response_data.get("processing_summary", {})
                    modules_executed = processing_summary.get("modules_executed", [])
                    
                    expected_modules = ["IPM", "JDPM", "TVM", "BDM", "DAM", "OPM"]
                    all_modules_executed = all(module in modules_executed for module in expected_modules)
                    results.append(all_modules_executed)
                    
                    # Check if final output contains high-quality score
                    analysis_result = response_data.get("analysis_result", {})
                    quality_score = analysis_result.get("quality_score", 0)
                    results.append(quality_score >= 0.8)  # High quality threshold
                    
                    # Check if decision is "success"
                    decision = analysis_result.get("decision", "")
                    results.append(decision.lower() in ["success", "approve", "pass"])
                    
                    # Check if binary data reference is present
                    binary_data = response_data.get("binary_data", {})
                    results.append("file_path" in binary_data or "file_reference" in binary_data)
                    
                    # Check if JFA_flag is present and has valid value
                    jfa_flag = response_data.get("JFA_flag")
                    results.append(jfa_flag is not None)
                    results.append(jfa_flag in [0, 1, True, False])
                    
                    # Check if all required output fields are present
                    required_fields = [
                        "request_id", "timestamp", "processing_summary", 
                        "analysis_result", "JFA_flag"
                    ]
                    all_fields_present = all(field in response_data for field in required_fields)
                    results.append(all_fields_present)
                    
                    # Check processing summary details
                    if "processing_summary" in response_data:
                        summary = response_data["processing_summary"]
                        results.append("total_processing_time" in summary)
                        results.append("success" in summary)
                        results.append("modules_executed" in summary)
                        
                        # Check processing time is reasonable
                        processing_time = summary.get("total_processing_time", 0)
                        results.append(processing_time > 0)
                        results.append(processing_time < 60)  # Should complete within 60 seconds
                    else:
                        results.extend([False, False, False, False, False])
                    
                    # Check analysis result details
                    if "analysis_result" in response_data:
                        analysis = response_data["analysis_result"]
                        results.append("quality_score" in analysis)
                        results.append("decision" in analysis)
                        results.append("recommendations" in analysis)
                        results.append("technical_metrics" in analysis)
                    else:
                        results.extend([False, False, False, False])
                    
                    # Check if recommendations are provided
                    recommendations = analysis_result.get("recommendations", [])
                    results.append(isinstance(recommendations, list))
                    results.append(len(recommendations) > 0)
                    
                    # Check if technical metrics are present
                    technical_metrics = analysis_result.get("technical_metrics", {})
                    results.append(isinstance(technical_metrics, dict))
                    results.append(len(technical_metrics) > 0)
                    
                    # Test pipeline stage validation
                    stage_results = response_data.get("stage_results", {})
                    if stage_results:
                        results.append("input_processing" in stage_results)
                        results.append("json_processing" in stage_results)
                        results.append("template_validation" in stage_results)
                        results.append("binary_generation" in stage_results)
                        results.append("data_analysis" in stage_results)
                    else:
                        results.extend([False, False, False, False, False])
                    
            except Exception as e:
                print(f"E2E happy path test failed: {e}")
                results.extend([False] * 20)  # Fill with False for all expected results
        
        success = all(results)
        
        return {
            "success": success,
            "test_code": test_code,
            "test_name": test_name,
            "message": "E2E happy path scenario passed" if success else "E2E happy path scenario failed",
            "details": {
                "request_successful": results[0],
                "response_success_flag": results[1],
                "all_pipeline_stages_executed": results[2],
                "high_quality_score_achieved": results[3],
                "success_decision_made": results[4],
                "binary_data_reference_present": results[5],
                "jfa_flag_present": results[6],
                "jfa_flag_valid_value": results[7],
                "all_required_fields_present": results[8],
                "processing_summary_has_time": results[9],
                "processing_summary_has_success": results[10],
                "processing_summary_has_modules": results[11],
                "processing_time_reasonable": results[12],
                "processing_time_within_limit": results[13],
                "analysis_has_quality_score": results[14],
                "analysis_has_decision": results[15],
                "analysis_has_recommendations": results[16],
                "analysis_has_technical_metrics": results[17],
                "recommendations_provided": results[18],
                "technical_metrics_present": results[19],
                "pipeline_stages_validated": results[20] if len(results) > 20 else False,
                "input_processing_stage": results[21] if len(results) > 21 else False,
                "json_processing_stage": results[22] if len(results) > 22 else False,
                "template_validation_stage": results[23] if len(results) > 23 else False,
                "binary_generation_stage": results[24] if len(results) > 24 else False,
                "data_analysis_stage": results[25] if len(results) > 25 else False,
                "quality_score": quality_score if 'quality_score' in locals() else 0,
                "decision": decision if 'decision' in locals() else "",
                "processing_time": processing_time if 'processing_time' in locals() else 0,
                "results": results
            }
        }
        
    finally:
        api_server.stop()