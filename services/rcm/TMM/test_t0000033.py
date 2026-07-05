"""
Test T0000033: Workflow: High Priority Request Processing
Module(s) Tested: GIDVM, PBRPM, IFCM, BAAIM, AACM, SODVM, OCMIM
Description: Test high priority request processing workflow.
Success Criteria: High priority requests are processed with appropriate urgency and resource allocation.
"""

print('DEBUG: test_t0000033.py started')
import sys
import os

# Dynamically add the RCM_main/RCM_main/RCM_main directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
print(f'DEBUG: sys.path = {sys.path}')
print(f'DEBUG: cwd = {os.getcwd()}')

print('DEBUG: about to import asyncio')
import asyncio
print('DEBUG: about to import tempfile')
import tempfile
print('DEBUG: about to import Path from pathlib')
from pathlib import Path
print('DEBUG: about to import json')
import json

print('DEBUG: about to import ErrorManagementModule')
from EMM.emm import ErrorManagementModule
print('DEBUG: about to import api_error_handler')
from EMM.api_error_handler import api_error_handler

print('DEBUG: about to import GIDVM')
from GIDVM.gidvm import GIDVM
print('DEBUG: about to import PBRPM')
from PBRPM.pbrpm import PBRPM
print('DEBUG: about to import IFCM')
from IFCM.ifcm import IFCM
print('DEBUG: about to import BAAIM')
from BAAIM.baaim import BAAIM
print('DEBUG: about to import AACM')
from AACM.aacm import AACM
print('DEBUG: about to import SODVM')
from SODVM.sodvm import SODVM
print('DEBUG: about to import OCMIM')
from OCMIM.ocmim import OCMIM
print('DEBUG: imports complete')

async def test_workflow_high_priority_request_processing():
    """Test high priority request processing workflow."""
    test_code = "T0000033"
    test_name = "Workflow: High Priority Request Processing"
    try:
        # Use global instances if available, else instantiate
        gidvm = GIDVM if isinstance(GIDVM, object) and not isinstance(GIDVM, type) else GIDVM()
        pbrpm = PBRPM if isinstance(PBRPM, object) and not isinstance(PBRPM, type) else PBRPM()
        ifcm = IFCM if isinstance(IFCM, object) and not isinstance(IFCM, type) else IFCM()
        baaim = BAAIM if isinstance(BAAIM, object) and not isinstance(BAAIM, type) else BAAIM()
        aacm = AACM if isinstance(AACM, object) and not isinstance(AACM, type) else AACM()
        sodvm = SODVM if isinstance(SODVM, object) and not isinstance(SODVM, type) else SODVM()
        ocmim = OCMIM if isinstance(OCMIM, object) and not isinstance(OCMIM, type) else OCMIM()
        
        # Test high priority data ingestion by writing to a temp file
        test_request = {
            "priority_flag": "A",
            "model": "gpt-4.1-nano",  # Use a valid model name
            "messages": ["Urgent request"],  # GIDVM expects a list of strings
            "urgent": True
        }
        import tempfile, json
        from PBRPM.pbrpm import PriorityRequest
        from pathlib import Path
        import time
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as tmp:
            json.dump(test_request, tmp)
            tmp_path = Path(tmp.name)
        try:
            ingestion_result = await gidvm.process_file(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)
        ingestion_success = ingestion_result is not None
        
        # For the rest of the workflow, create a PriorityRequest and await process_request
        if ingestion_success:
            file_path, priority = ingestion_result
            priority_request = PriorityRequest(file_path, priority, time.time())
            priority_success = await pbrpm.process_request(priority_request)
        else:
            priority_request = None
            priority_success = False
        
        # Test flow control with high priority
        if priority_success:
            # Use IFCM's process_request to start the workflow
            request_id = await ifcm.process_request(test_request, "A")
            flow_success = isinstance(request_id, str) and len(request_id) > 0
        else:
            request_id = None
            flow_success = False
        
        # Test API communication with high priority
        if flow_success:
            # Convert messages to OpenAI format for BAAIM
            baaim_request = dict(test_request)
            baaim_request["messages"] = [{"role": "user", "content": msg} for msg in test_request["messages"]]
            api_result = await baaim.process_request(baaim_request)
            api_success = isinstance(api_result, object) and hasattr(api_result, 'success') and api_result.success
        else:
            api_result = None
            api_success = False
        
        # Test response verification
        if api_success:
            verification_result = sodvm.verify_json(api_result)
            verification_success = verification_result is True
        else:
            verification_result = None
            verification_success = False
        
        # Test high priority output handoff
        if verification_success:
            # Convert api_result to dict if it's a BasicAPIResponse object
            if hasattr(api_result, 'success') and hasattr(api_result, 'response'):
                handoff_data = {
                    "success": api_result.success,
                    "response": api_result.response,
                    "model_used": api_result.model_used,
                    "tokens_used": api_result.tokens_used
                }
            else:
                handoff_data = api_result
            
            handoff_result = await ocmim.handoff_response("test_123", handoff_data, "success")
            handoff_success = isinstance(handoff_result, dict)
        else:
            handoff_result = None
            handoff_success = False
        
        test_success = (ingestion_success and priority_success and flow_success and 
                       api_success and verification_success and handoff_success)
        
        return {
            "success": test_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": f"High priority request processing successful",
            "details": {
                "ingestion_success": ingestion_success,
                "priority_success": priority_success,
                "flow_success": flow_success,
                "api_success": api_success,
                "verification_success": verification_success,
                "handoff_success": handoff_success
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
    print("Test T0000033: Workflow: High Priority Request Processing")
    print("=" * 60)
    result = await test_workflow_high_priority_request_processing()
    print(f"\nTest Result: {'PASSED' if result['success'] else 'FAILED'}")
    print(f"Test Code: {result['test_code']}")
    print(f"Test Name: {result['test_name']}")
    if result['success']:
        print(f"Message: {result['message']}")
        print("\nDetails:")
        for key, value in result['details'].items():
            print(f"  {key}: {value}")
    else:
        # Always provide an error message, even if it's a default one
        error_msg = result.get('error', 'Unknown error occurred')
        print(f"Error: {error_msg}")
        # Also print any additional details that might be available
        if 'details' in result:
            print("\nDetails:")
            for key, value in result['details'].items():
                print(f"  {key}: {value}")
    print("\n" + "=" * 60)
    return result

if __name__ == "__main__":
    asyncio.run(main())