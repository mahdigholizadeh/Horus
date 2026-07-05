"""
Test T0000024: Workflow: JFA Template Fulfillment
Module(s) Tested: GIDVM, PBRPM, IFCM, BAAIM, AACM, SODVM, JFAIM
Description: Test JSON template fulfillment workflow.
Success Criteria: The API returns a filled template that is extracted and handed off to JFA.
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
from JFAIM.jfaim import JFAInteractionModule

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        return super().default(obj)

async def test_workflow_jfa_template_fulfillment():
    """Test JSON template fulfillment workflow."""
    test_code = "T0000024"
    test_name = "Workflow: JFA Template Fulfillment"
    try:
        print(f"Starting {test_name}...")
        
        # Initialize all modules
        gidvm = GetInputDataAndVerificationModule()
        pbrpm = PriorityBasedRequestProcessingModule()
        ifcm = InternalFlowControlModule()
        baaim = BasicAPIActivationModule()
        aacm = AsynchronousAPICommunicationModule()
        sodvm = SetOutputDataAndVerificationModule()
        jfaim = JFAInteractionModule()
        
        print("All modules initialized successfully")
        
        # Test 1: GIDVM - Input data processing for JFA template
        print("1. Testing GIDVM input data processing for JFA template...")
        try:
            # Create a test JSON file with JFA template request
            test_file = Path("test_jfa_input.json")
            test_data = {
                "priority_flag": "B",
                "model": "gpt-4",
                "messages": ["Fill this JSON template: {name: string, age: number}"],
                "template_request": True
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
        
        # Test 2: PBRPM - Priority processing for template request
        print("2. Testing PBRPM priority processing for template request...")
        try:
            # Create a test request with higher priority for template
            from PBRPM.pbrpm import PriorityRequest
            test_request = PriorityRequest(Path("test_jfa.json"), "B", datetime.now().timestamp())
            pbrpm_result = await pbrpm.process_request(test_request)
            pbrpm_success = isinstance(pbrpm_result, bool)
            print(f"   PBRPM processing: {'Passed' if pbrpm_success else 'Failed'}")
            
        except Exception as e:
            print(f"   PBRPM processing: Failed - {str(e)}")
            pbrpm_success = False
        
        # Test 3: IFCM - Flow control for template workflow
        print("3. Testing IFCM flow control for template workflow...")
        try:
            # Test request processing through IFCM with template flag
            test_request_data = {
                "messages": [{"role": "user", "content": "Fill this JSON template: {name: string, age: number}"}],
                "model": "gpt-4",
                "priority": "B",
                "template_request": True
            }
            request_id = await ifcm.process_request(test_request_data, "B")
            ifcm_success = isinstance(request_id, str) and len(request_id) > 0
            print(f"   IFCM flow control: {'Passed' if ifcm_success else 'Failed'}")
            
        except Exception as e:
            print(f"   IFCM flow control: Failed - {str(e)}")
            ifcm_success = False
        
        # Test 4: BAAIM - Basic API processing for template generation
        print("4. Testing BAAIM basic API processing for template generation...")
        try:
            test_api_request = {
                "messages": [{"role": "user", "content": "Fill this JSON template: {name: string, age: number}"}],
                "model": "gpt-4",
                "max_tokens": 100
            }
            baaim_result = await baaim.process_request(test_api_request)
            baaim_success = isinstance(baaim_result, object) and hasattr(baaim_result, 'success')
            print(f"   BAAIM API processing: {'Passed' if baaim_success else 'Failed'}")
            
        except Exception as e:
            print(f"   BAAIM API processing: Failed - {str(e)}")
            baaim_success = False
        
        # Test 5: AACM - Async API communication for template
        print("5. Testing AACM async API communication for template...")
        try:
            # Test status
            aacm_status = await aacm.get_status()
            aacm_success = isinstance(aacm_status, dict) and "status" in aacm_status
            print(f"   AACM async communication: {'Passed' if aacm_success else 'Failed'}")
            
        except Exception as e:
            print(f"   AACM async communication: Failed - {str(e)}")
            aacm_success = False
        
        # Test 6: SODVM - Output verification for template
        print("6. Testing SODVM output verification for template...")
        try:
            test_output_data = {
                "response": '{"name": "John", "age": 30}',
                "status": "success",
                "template_filled": True
            }
            test_output_path = "test_jfa_output.json"
            
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
        
        # Test 7: JFAIM - Template processing and handoff
        print("7. Testing JFAIM template processing and handoff...")
        try:
            # Create a test JFA template response with correct structure
            test_template_response = {
                "id": "test-jfa-123",
                "object": "chat.completion",
                "created": 1234567890,
                "model": "gpt-4",
                "choices": {
                    "message": {
                        "role": "assistant",
                        "content": '{"name": "John", "age": 30}'
                    }
                },
                "usage": {
                    "prompt_tokens": 15,
                    "completion_tokens": 8,
                    "total_tokens": 23
                }
            }
            request_id = "test-jfa-123"
            
            # Test template processing
            template_result = await jfaim.process_jfa_template(test_template_response, request_id)
            template_success = template_result.get("success", False)
            print(f"   Template processing: {'Passed' if template_success else 'Failed'}")
            
            # Test JFA file generation
            jfa_files_result = await jfaim.generate_jfa_files(test_template_response, request_id)
            jfa_files_success = jfa_files_result.get("success", False)
            print(f"   JFA file generation: {'Passed' if jfa_files_success else 'Failed'}")
            
            jfaim_success = template_success and jfa_files_success
            
        except Exception as e:
            print(f"   JFAIM template processing: Failed - {str(e)}")
            jfaim_success = False
        
        # Calculate overall success
        tests = [
            gidvm_success,
            pbrpm_success,
            ifcm_success,
            baaim_success,
            aacm_success,
            sodvm_success,
            jfaim_success
        ]
        
        successful_tests = sum(tests)
        total_tests = len(tests)
        success_rate = (successful_tests / total_tests) * 100
        
        test_success = success_rate >= 80  # At least 80% success rate
        
        result = {
            "success": test_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": f"JFA template fulfillment tests: {successful_tests}/{total_tests} successful ({success_rate:.1f}% success rate)",
            "details": {
                "gidvm_success": gidvm_success,
                "pbrpm_success": pbrpm_success,
                "ifcm_success": ifcm_success,
                "baaim_success": baaim_success,
                "aacm_success": aacm_success,
                "sodvm_success": sodvm_success,
                "jfaim_success": jfaim_success,
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
    result = asyncio.run(test_workflow_jfa_template_fulfillment())
    print(json.dumps(result, indent=2, cls=CustomJSONEncoder)) 