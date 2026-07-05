"""
Test T0000038: Workflow: End-to-End Failure, Retry, and Reporting
Module(s) Tested: RLM, EMM, ECM, IFCM
Description: Test failure handling, retry logic, and reporting.
Success Criteria: RLM retries failed requests, EMM logs failures, and ECM reports status.
"""

import asyncio
import sys
import os
import json

# Add the EMM parent directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from RLM.rlm import RateLimitingModule
from EMM.emm import ErrorManagementModule
from ECM.ecm import ExternalControlModule
from IFCM.ifcm import InternalFlowControlModule

async def test_workflow_end_to_end_failure_retry_and_reporting():
    """Test failure handling, retry logic, and reporting."""
    test_code = "T0000038"
    test_name = "Workflow: End-to-End Failure, Retry, and Reporting"
    try:
        # Create local instances
        rlm = RateLimitingModule()
        emm = ErrorManagementModule()
        ecm = ExternalControlModule()
        ifcm = InternalFlowControlModule()
        
        # Test failed request simulation using RLM's retry manager
        failed_request_id = "fail_123"
        retry_result = rlm.retry_manager.should_retry(failed_request_id, "API_FAILURE") if hasattr(rlm, 'retry_manager') else False
        failure_success = isinstance(retry_result, bool)
        
        # Test retry mechanism - increment retry count
        if hasattr(rlm, 'retry_manager'):
            rlm.retry_manager.increment_retry_count(failed_request_id)
            retry_count = rlm.retry_manager.get_status().get("retry_counts", {}).get(failed_request_id, 0)
            retry_success = retry_count > 0
        else:
            retry_success = False
        
        # Test error logging with EMM
        error_result = emm.log_error_with_generation("RLM", "RateLimitingModule", "test_function", "Request failed after retries") if hasattr(emm, 'log_error_with_generation') else False
        error_success = isinstance(error_result, str) and len(error_result) == 16  # log_error_with_generation returns error code on success
        
        # Test failure reporting via ECM status
        status_result = ecm.get_service_status() if hasattr(ecm, 'get_service_status') else {}
        report_success = isinstance(status_result, dict)
        
        # Test flow control with failure using IFCM
        flow_result = await ifcm.process_request({"request_id": failed_request_id, "status": "failed"}) if hasattr(ifcm, 'process_request') and asyncio.iscoroutinefunction(ifcm.process_request) else ifcm.process_request({"request_id": failed_request_id, "status": "failed"})
        flow_success = isinstance(flow_result, str) or isinstance(flow_result, dict)
        
        # Test error code generation with EMM
        code_result = emm.generate_error_code("RLM", "RateLimitingModule", "test_function") if hasattr(emm, 'generate_error_code') else None
        code_success = isinstance(code_result, str) and len(code_result) == 16
        
        test_success = (failure_success and retry_success and error_success and 
                       report_success and flow_success and code_success)
        
        return {
            "success": test_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": f"End-to-end failure handling successful",
            "details": {
                "failure_success": failure_success,
                "retry_success": retry_success,
                "error_success": error_success,
                "report_success": report_success,
                "flow_success": flow_success,
                "code_success": code_success
            }
        }
    except Exception as e:
        return {
            "success": False,
            "test_code": test_code,
            "test_name": test_name,
            "error": f"Test execution failed: {str(e)}"
        }

async def main():
    print("=" * 60)
    print("Test T0000038: Workflow: End-to-End Failure, Retry, and Reporting")
    print("=" * 60)
    result = await test_workflow_end_to_end_failure_retry_and_reporting()
    print(f"\nTest Result: {'PASSED' if result['success'] else 'FAILED'}")
    print(f"Test Code: {result['test_code']}")
    print(f"Test Name: {result['test_name']}")
    if result['success']:
        print(f"Message: {result['message']}")
        print("\nDetails:")
        for key, value in result['details'].items():
            print(f"  {key}: {value}")
    else:
        error_msg = result.get('error', 'Unknown error occurred')
        print(f"Error: {error_msg}")
        if 'details' in result:
            print("\nDetails:")
            for key, value in result['details'].items():
                print(f"  {key}: {value}")
    print("\n" + "=" * 60)
    return result

if __name__ == "__main__":
    asyncio.run(main()) 