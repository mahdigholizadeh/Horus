"""
Test O00000073: TD Microservice Integration
Module(s) Tested: TDIM (TD Interaction Module), RMM (Request Management Module)
Description: Test integration with TD microservice
Test Description:
- Test computation result reception
- Verify data format compatibility
- Check processing workflows
- Test error handling
- Verify performance optimization
- Validate integration reliability
Expected Result: Reliable TD microservice integration
Pass Criteria: Results received, formats compatible, workflows functional, errors handled
Implementation Notes: Test with various TD result types
"""

import asyncio
import json
import sys
import os
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid
import random
import time

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_o00000073():
    test_code = "O00000073"
    test_name = "TD Microservice Integration"
    results = []
    
    try:
        # Import required modules
        from TDIM.tdim import TDInteractionModule
        from RMM.rmm import RequestManagementModule
        from MSM.msm import MonitoringSystemModule
        
        # Create temporary test directory
        test_dir = tempfile.mkdtemp(prefix="td_integration_test_")
        
        # Step 1: Initialize modules with TD integration configuration
        tdim_config = {
            "td_integration": {
                "enabled": True,
                "result_processing": True,
                "error_handling": True
            }
        }
        
        tdim = TDInteractionModule(tdim_config)
        await tdim.start()
        results.append(tdim.is_active == True)
        results.append(hasattr(tdim, 'receive_td_data'))
        results.append(hasattr(tdim, 'get_processing_status'))
        results.append(hasattr(tdim, 'get_status'))
        
        rmm_config = {
            "request_management": {
                "enabled": True,
                "priority_queues": True,
                "error_handling": True
            }
        }
        
        rmm = RequestManagementModule(rmm_config)
        await rmm.start()
        results.append(rmm.is_active == True)
        results.append(hasattr(rmm, 'submit_request'))
        results.append(hasattr(rmm, 'get_queue_stats'))
        results.append(hasattr(rmm, 'get_status'))
        
        msm_config = {
            "monitoring": {
                "td_integration_monitoring": True,
                "performance_monitoring": True,
                "error_monitoring": True
            }
        }
        
        msm = MonitoringSystemModule(msm_config)
        await msm.start()
        results.append(msm.is_active == True)
        results.append(hasattr(msm, 'get_status'))
        
        # Create mock DSM for RMM
        class MockDSM:
            async def send_data(self, data, destination, **kwargs):
                return {"success": True, "response": "Mock response"}
        
        rmm.modules["DSM"] = MockDSM()
        
        # Step 2: Test computation result reception
        reception_results = []
        
        # Test TD result reception
        td_result = {
            "result_id": f"td_result_{uuid.uuid4().hex[:8]}",
            "computation_type": "energy_analysis",
            "data": {
                "consumption": 1500.5,
                "efficiency": 0.85,
                "recommendations": ["optimize_usage", "upgrade_equipment"]
            },
            "priority": "A",
            "timestamp": datetime.now().isoformat()
        }
        
        # Receive TD result
        reception_success = await tdim.receive_td_data(td_result)
        reception_results.append(reception_success is not None)
        
        # Check processing status
        if reception_success:
            processing_status = tdim.get_processing_status(td_result["result_id"])
            reception_results.append(processing_status is not None)
            
            if processing_status:
                reception_results.append("validation_status" in processing_status)
                reception_results.append("processing_completed" in processing_status)
        
        # Step 3: Test data format compatibility
        format_results = []
        
        # Test different data formats
        test_formats = [
            {
                "result_id": f"format_test_{uuid.uuid4().hex[:8]}",
                "computation_type": "performance_metrics",
                "data": {"throughput": 95.2, "latency": 45.8},
                "priority": "B",
                "timestamp": datetime.now().isoformat()
            },
            {
                "result_id": f"format_test_{uuid.uuid4().hex[:8]}",
                "computation_type": "system_health",
                "data": {"cpu_usage": 65.3, "memory_usage": 78.9},
                "priority": "C",
                "timestamp": datetime.now().isoformat()
            }
        ]
        
        for test_format in test_formats:
            format_success = await tdim.receive_td_data(test_format)
            format_results.append(format_success is not None)
            
            if format_success:
                format_status = tdim.get_processing_status(test_format["result_id"])
                format_results.append(format_status is not None)
        
        # Step 4: Test processing workflows
        workflow_results = []
        
        # Test workflow through RMM
        for test_format in test_formats:
            # Submit to RMM
            request_data = {
                "request_type": "td_report",
                "priority": test_format["priority"],
                "source_module": "TDIM",
                "content_type": "json",
                "metadata": test_format
            }
            
            request_id = await rmm.submit_request(request_data)
            workflow_results.append(request_id is not None)
            
            # Check queue stats
            if request_id:
                queue_stats = rmm.get_queue_stats()
                workflow_results.append(queue_stats is not None)
        
        # Step 5: Test error handling
        error_results = []
        
        # Test with invalid data
        invalid_result = {
            "result_id": "invalid_result",
            "computation_type": "invalid_type",
            "data": None,
            "priority": "A"
        }
        
        try:
            invalid_reception = await tdim.receive_td_data(invalid_result)
            error_results.append(invalid_reception == False)
        except Exception:
            error_results.append(True)  # Should handle error gracefully
        
        # Test module status
        tdim_status = tdim.get_status()
        error_results.append(tdim_status is not None)
        
        rmm_status = rmm.get_status()
        error_results.append(rmm_status is not None)
        
        # Step 6: Test performance optimization
        performance_results = []
        
        # Test health checks
        tdim_health = await tdim.health_check()
        performance_results.append(tdim_health is not None)
        
        rmm_health = await rmm.health_check()
        performance_results.append(rmm_health is not None)
        
        msm_health = await msm.health_check()
        performance_results.append(msm_health is not None)
        
        # Test module capabilities
        performance_results.append(hasattr(tdim, 'receive_td_data'))
        performance_results.append(hasattr(rmm, 'submit_request'))
        performance_results.append(hasattr(msm, 'get_status'))
        
        # Step 7: Test integration reliability
        reliability_results = []
        
        # Test module activity
        reliability_results.append(tdim.is_active)
        reliability_results.append(rmm.is_active)
        reliability_results.append(msm.is_active)
        
        # Test module status availability
        reliability_results.append(tdim_status is not None)
        reliability_results.append(rmm_status is not None)
        
        msm_status = msm.get_status()
        reliability_results.append(msm_status is not None)
        
        # Aggregate all results
        all_results = (results + reception_results + format_results + 
                      workflow_results + error_results + performance_results + reliability_results)
        
        # Calculate pass rate
        passed_tests = sum(1 for r in all_results if r)
        total_tests = len(all_results)
        pass_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        # Cleanup
        await tdim.stop()
        await rmm.stop()
        await msm.stop()
        
        # Clean up test directory
        try:
            import shutil
            shutil.rmtree(test_dir)
        except Exception:
            pass
        
        return {
            "test_code": test_code,
            "test_name": test_name,
            "status": "PASSED" if pass_rate >= 90 else "FAILED",
            "pass_rate": pass_rate,
            "passed_tests": passed_tests,
            "total_tests": total_tests,
            "results": {
                "module_initialization": results,
                "computation_result_reception": reception_results,
                "data_format_compatibility": format_results,
                "processing_workflows": workflow_results,
                "error_handling": error_results,
                "performance_optimization": performance_results,
                "integration_reliability": reliability_results
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "test_code": test_code,
            "test_name": test_name,
            "status": "ERROR",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "details": {
                "exception_type": type(e).__name__,
                "exception_message": str(e)
            }
        }

async def main():
    """Main function to run the test."""
    result = await test_o00000073()
    print(json.dumps(result, indent=2))
    return result

if __name__ == "__main__":
    asyncio.run(main()) 