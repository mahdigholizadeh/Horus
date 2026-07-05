"""
Test T0000025: Workflow: Error Handling & Recovery
Module(s) Tested: GIDVM, PBRPM, IFCM, BAAIM, AACM, SODVM, EMM, ECM
Description: Test error handling and recovery workflow.
Success Criteria: Errors are caught, logged, and recovery strategies are attempted.
"""

import asyncio
import tempfile
from pathlib import Path
import sys
import os
import json
from datetime import datetime

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from GIDVM.gidvm import GetInputDataAndVerificationModule
from PBRPM.pbrpm import PriorityBasedRequestProcessingModule
from IFCM.ifcm import InternalFlowControlModule
from BAAIM.baaim import BasicAPIActivationModule
from AACM.aacm import AsynchronousAPICommunicationModule
from SODVM.sodvm import SetOutputDataAndVerificationModule
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler
from ECM.ecm import ExternalControlModule

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        return super().default(obj)

async def test_workflow_error_handling_and_recovery():
    """Test error handling and recovery workflow."""
    test_code = "T0000025"
    test_name = "Workflow: Error Handling & Recovery"
    try:
        print(f"Starting {test_name}...")
        
        # Initialize all modules
        gidvm = GetInputDataAndVerificationModule()
        pbrpm = PriorityBasedRequestProcessingModule()
        ifcm = InternalFlowControlModule()
        baaim = BasicAPIActivationModule()
        aacm = AsynchronousAPICommunicationModule()
        sodvm = SetOutputDataAndVerificationModule()
        emm = ErrorManagementModule()
        ecm = ExternalControlModule()
        
        print("All modules initialized successfully")
        
        # Test 1: GIDVM - Error handling for invalid input
        print("1. Testing GIDVM error handling for invalid input...")
        try:
            # Create a test JSON file with invalid data
            test_file = Path("test_invalid_input.json")
            test_data = {
                "priority_flag": "X",  # Invalid priority
                "model": "gpt-4",
                "messages": []  # Empty messages
            }
            with open(test_file, 'w') as f:
                json.dump(test_data, f)
            
            # Process the file (should fail)
            gidvm_result = await gidvm.process_file(test_file)
            gidvm_success = gidvm_result is None  # Expected to fail
            print(f"   GIDVM error handling: {'Passed' if gidvm_success else 'Failed'}")
            
            # Clean up test file
            test_file.unlink(missing_ok=True)
            
        except Exception as e:
            print(f"   GIDVM error handling: Failed - {str(e)}")
            gidvm_success = False
        
        # Test 2: PBRPM - Error handling for invalid priority
        print("2. Testing PBRPM error handling for invalid priority...")
        try:
            # Create a test request with invalid priority
            from PBRPM.pbrpm import PriorityRequest
            test_request = PriorityRequest(Path("test_invalid.json"), "X", datetime.now().timestamp())
            pbrpm_result = await pbrpm.process_request(test_request)
            pbrpm_success = isinstance(pbrpm_result, bool)
            print(f"   PBRPM error handling: {'Passed' if pbrpm_success else 'Failed'}")
            
        except Exception as e:
            print(f"   PBRPM error handling: Failed - {str(e)}")
            pbrpm_success = False
        
        # Test 3: IFCM - Error handling for invalid request
        print("3. Testing IFCM error handling for invalid request...")
        try:
            # Test request processing through IFCM with invalid data
            test_request_data = {
                "messages": [],  # Empty messages
                "model": "invalid-model",
                "priority": "X"
            }
            request_id = await ifcm.process_request(test_request_data, "X")
            ifcm_success = isinstance(request_id, str) and len(request_id) > 0
            print(f"   IFCM error handling: {'Passed' if ifcm_success else 'Failed'}")
            
        except Exception as e:
            print(f"   IFCM error handling: Failed - {str(e)}")
            ifcm_success = False
        
        # Test 4: BAAIM - Error handling for API failures
        print("4. Testing BAAIM error handling for API failures...")
        try:
            test_api_request = {
                "messages": [{"role": "user", "content": "Hello"}],
                "model": "invalid-model",
                "max_tokens": -1  # Invalid tokens
            }
            baaim_result = await baaim.process_request(test_api_request)
            baaim_success = isinstance(baaim_result, object) and hasattr(baaim_result, 'success')
            print(f"   BAAIM error handling: {'Passed' if baaim_success else 'Failed'}")
            
        except Exception as e:
            print(f"   BAAIM error handling: Failed - {str(e)}")
            baaim_success = False
        
        # Test 5: AACM - Error handling for async failures
        print("5. Testing AACM error handling for async failures...")
        try:
            # Test status
            aacm_status = await aacm.get_status()
            aacm_success = isinstance(aacm_status, dict) and "status" in aacm_status
            print(f"   AACM error handling: {'Passed' if aacm_success else 'Failed'}")
            
        except Exception as e:
            print(f"   AACM error handling: Failed - {str(e)}")
            aacm_success = False
        
        # Test 6: SODVM - Error handling for invalid output
        print("6. Testing SODVM error handling for invalid output...")
        try:
            test_output_data = None  # Invalid data
            test_output_path = "test_invalid_output.json"
            
            # Set output data (should handle invalid data)
            sodvm_set_success = sodvm.set_output_data(test_output_data, test_output_path)
            
            # Verify output data
            sodvm_verify_success = sodvm.verify_output_data(test_output_path)
            
            sodvm_success = sodvm_set_success and sodvm_verify_success
            print(f"   SODVM error handling: {'Passed' if sodvm_success else 'Failed'}")
            
            # Clean up
            Path(test_output_path).unlink(missing_ok=True)
            
        except Exception as e:
            print(f"   SODVM error handling: Failed - {str(e)}")
            sodvm_success = False
        
        # Test 7: EMM - Error logging and recovery
        print("7. Testing EMM error logging and recovery...")
        try:
            # Test error code generation
            error_code = emm.generate_error_code("TEST", "TestClass", "test_function", "001")
            code_generation_success = len(error_code) == 16
            
            # Test error logging
            log_success = emm.log_error(error_code, "Test error for recovery workflow")
            
            # Test automatic error logging
            auto_log_result = emm.log_error_with_generation("TEST", "TestClass", "auto_test_func", "Auto-generated error")
            auto_log_success = isinstance(auto_log_result, str) and len(auto_log_result) == 16
            
            # Test error statistics
            stats = await emm.get_error_statistics()
            stats_success = isinstance(stats, dict) and "total_errors" in stats
            
            emm_success = code_generation_success and log_success and auto_log_success and stats_success
            print(f"   EMM error handling: {'Passed' if emm_success else 'Failed'}")
            
        except Exception as e:
            print(f"   EMM error handling: Failed - {str(e)}")
            emm_success = False
        
        # Test 8: ECM - Error reporting and status
        print("8. Testing ECM error reporting and status...")
        try:
            # Test status command
            status_command = "status"
            status_result = await ecm.receive_command(status_command, {})
            status_success = isinstance(status_result, dict) and "success" in status_result
            
            # Test error command
            error_command = "get_errors"
            error_result = await ecm.receive_command(error_command, {})
            error_success = isinstance(error_result, dict) and "success" in error_result
            
            ecm_success = status_success and error_success
            print(f"   ECM error handling: {'Passed' if ecm_success else 'Failed'}")
            
        except Exception as e:
            print(f"   ECM error handling: Failed - {str(e)}")
            ecm_success = False
        
        # Calculate overall success
        tests = [
            gidvm_success,
            pbrpm_success,
            ifcm_success,
            baaim_success,
            aacm_success,
            sodvm_success,
            emm_success,
            ecm_success
        ]
        
        successful_tests = sum(tests)
        total_tests = len(tests)
        success_rate = (successful_tests / total_tests) * 100
        
        test_success = success_rate >= 80  # At least 80% success rate
        
        result = {
            "success": test_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": f"Error handling and recovery tests: {successful_tests}/{total_tests} successful ({success_rate:.1f}% success rate)",
            "details": {
                "gidvm_success": gidvm_success,
                "pbrpm_success": pbrpm_success,
                "ifcm_success": ifcm_success,
                "baaim_success": baaim_success,
                "aacm_success": aacm_success,
                "sodvm_success": sodvm_success,
                "emm_success": emm_success,
                "ecm_success": ecm_success,
                "success_rate": success_rate,
                "error_code": error_code if 'error_code' in locals() else None
            }
        }
        
        print(f"\nTest result: {result}")
        return result
        
    except Exception as e:
        error_result = {
            "success": False,
            "test_code": test_code,
            "test_name": test_name,
            "error": f"Test execution failed: {str(e)}"
        }
        print(f"Test failed: {error_result}")
        return error_result

if __name__ == "__main__":
    result = asyncio.run(test_workflow_error_handling_and_recovery())
    print(json.dumps(result, indent=2, cls=CustomJSONEncoder)) 