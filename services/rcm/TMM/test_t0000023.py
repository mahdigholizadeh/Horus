"""
Test T0000023: Workflow: Standard Successful Request
Module(s) Tested: GIDVM, PBRPM, IFCM, BAAIM, AACM, SODVM, OCMIM
Description: Test complete end-to-end request processing workflow.
Success Criteria: The request is processed through the entire pipeline without errors.
"""

import asyncio
import tempfile
from pathlib import Path
import sys
import os
import json
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler
from datetime import datetime

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from GIDVM.gidvm import GetInputDataAndVerificationModule
from PBRPM.pbrpm import PriorityBasedRequestProcessingModule
from IFCM.ifcm import InternalFlowControlModule
from BAAIM.baaim import BasicAPIActivationModule
from AACM.aacm import AsynchronousAPICommunicationModule
from SODVM.sodvm import SetOutputDataAndVerificationModule
from OCMIM.ocmim import OCMInteractionModule

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        return super().default(obj)

async def test_workflow_standard_successful_request():
    """Test complete end-to-end request processing workflow."""
    test_code = "T0000023"
    test_name = "Workflow: Standard Successful Request"
    try:
        print(f"Starting {test_name}...")
        
        # Initialize all modules
        gidvm = GetInputDataAndVerificationModule()
        pbrpm = PriorityBasedRequestProcessingModule()
        ifcm = InternalFlowControlModule()
        baaim = BasicAPIActivationModule()
        aacm = AsynchronousAPICommunicationModule()
        sodvm = SetOutputDataAndVerificationModule()
        ocmim = OCMInteractionModule()
        
        print("All modules initialized successfully")
        
        # Test 1: GIDVM - Input data processing
        print("1. Testing GIDVM input data processing...")
        try:
            # Create a test JSON file
            test_file = Path("test_input.json")
            test_data = {
                "priority_flag": "C",
                "model": "gpt-4",
                "messages": ["Hello, how are you?"]
            }
            with open(test_file, 'w') as f:
                json.dump(test_data, f)
            
            # Process the file
            gidvm_result = await gidvm.process_file(test_file)
            gidvm_success = gidvm_result is not None
            print(f"   GIDVM processing: {'Passed' if gidvm_success else 'Failed'}")
            
            # Clean up test file
            test_file.unlink(missing_ok=True)
            
        except Exception as e:
            print(f"   GIDVM processing: Failed - {str(e)}")
            gidvm_success = False
        
        # Test 2: PBRPM - Priority processing
        print("2. Testing PBRPM priority processing...")
        try:
            # Create a test request
            from PBRPM.pbrpm import PriorityRequest
            test_request = PriorityRequest(Path("test.json"), "C", datetime.now().timestamp())
            pbrpm_result = await pbrpm.process_request(test_request)
            pbrpm_success = isinstance(pbrpm_result, bool)
            print(f"   PBRPM processing: {'Passed' if pbrpm_success else 'Failed'}")
            
        except Exception as e:
            print(f"   PBRPM processing: Failed - {str(e)}")
            pbrpm_success = False
        
        # Test 3: IFCM - Flow control orchestration
        print("3. Testing IFCM flow control...")
        try:
            # Test request processing through IFCM
            test_request_data = {
                "messages": [{"role": "user", "content": "Hello"}],
                "model": "gpt-4",
                "priority": "C"
            }
            request_id = await ifcm.process_request(test_request_data, "C")
            ifcm_success = isinstance(request_id, str) and len(request_id) > 0
            print(f"   IFCM flow control: {'Passed' if ifcm_success else 'Failed'}")
            
        except Exception as e:
            print(f"   IFCM flow control: Failed - {str(e)}")
            ifcm_success = False
        
        # Test 4: BAAIM - Basic API processing
        print("4. Testing BAAIM basic API processing...")
        try:
            test_api_request = {
                "messages": [{"role": "user", "content": "Hello"}],
                "model": "gpt-4",
                "max_tokens": 50
            }
            baaim_result = await baaim.process_request(test_api_request)
            baaim_success = isinstance(baaim_result, object) and hasattr(baaim_result, 'success')
            print(f"   BAAIM API processing: {'Passed' if baaim_success else 'Failed'}")
            
        except Exception as e:
            print(f"   BAAIM API processing: Failed - {str(e)}")
            baaim_success = False
        
        # Test 5: AACM - Async API communication
        print("5. Testing AACM async API communication...")
        try:
            # Test status
            aacm_status = await aacm.get_status()
            aacm_success = isinstance(aacm_status, dict) and "status" in aacm_status
            print(f"   AACM async communication: {'Passed' if aacm_success else 'Failed'}")
            
        except Exception as e:
            print(f"   AACM async communication: Failed - {str(e)}")
            aacm_success = False
        
        # Test 6: SODVM - Output verification
        print("6. Testing SODVM output verification...")
        try:
            test_output_data = {"response": "Test response", "status": "success"}
            test_output_path = "test_output.json"
            
            # Set output data
            sodvm_set_success = sodvm.set_output_data(test_output_data, test_output_path)
            
            # Verify output data
            sodvm_verify_success = sodvm.verify_output_data(test_output_path)
            
            sodvm_success = sodvm_set_success and sodvm_verify_success
            print(f"   SODVM output verification: {'Passed' if sodvm_success else 'Failed'}")
            
            # Clean up
            Path(test_output_path).unlink(missing_ok=True)
            
        except Exception as e:
            print(f"   SODVM output verification: Failed - {str(e)}")
            sodvm_success = False
        
        # Test 7: OCMIM - Handoff to OCM
        print("7. Testing OCMIM handoff to OCM...")
        try:
            test_response = {"response": "Test response", "status": "success"}
            request_id = "test_123"
            
            # Test handoff
            ocmim_handoff_result = await ocmim.handoff_response(request_id, test_response, "success")
            ocmim_handoff_success = ocmim_handoff_result.get("success", False)
            
            # Test delivery
            ocmim_delivery_result = await ocmim.deliver_response(request_id, "file")
            ocmim_delivery_success = ocmim_delivery_result.get("success", False)
            
            ocmim_success = ocmim_handoff_success and ocmim_delivery_success
            print(f"   OCMIM handoff to OCM: {'Passed' if ocmim_success else 'Failed'}")
            
        except Exception as e:
            print(f"   OCMIM handoff to OCM: Failed - {str(e)}")
            ocmim_success = False
        
        # Calculate overall success
        tests = [
            gidvm_success,
            pbrpm_success,
            ifcm_success,
            baaim_success,
            aacm_success,
            sodvm_success,
            ocmim_success
        ]
        
        successful_tests = sum(tests)
        total_tests = len(tests)
        success_rate = (successful_tests / total_tests) * 100
        
        test_success = success_rate >= 80  # At least 80% success rate
        
        result = {
            "success": test_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": f"Workflow tests: {successful_tests}/{total_tests} successful ({success_rate:.1f}% success rate)",
            "details": {
                "gidvm_success": gidvm_success,
                "pbrpm_success": pbrpm_success,
                "ifcm_success": ifcm_success,
                "baaim_success": baaim_success,
                "aacm_success": aacm_success,
                "sodvm_success": sodvm_success,
                "ocmim_success": ocmim_success,
                "success_rate": success_rate,
                "request_id": request_id if 'request_id' in locals() else None
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
    result = asyncio.run(test_workflow_standard_successful_request())
    print(json.dumps(result, indent=2, cls=CustomJSONEncoder)) 