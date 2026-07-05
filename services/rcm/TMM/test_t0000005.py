"""
Test T0000005: RTRMM - Response to Request ID Mapping
Module(s) Tested: RTRMM
Description: Map a response to its corresponding request ID.
Success Criteria: The module correctly maps a response to the request ID and retrieves it accurately.
"""

import asyncio
import tempfile
from pathlib import Path
import sys
import os
import json
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from RTRMM.rtrmm import RequestTrackingAndResponseMappingModule

async def test_rtrmm_response_to_request_id_mapping():
    """Test mapping a response to its corresponding request ID."""
    test_code = "T0000005"
    test_name = "RTRMM - Response to Request ID Mapping"
    try:
        rtrmm = RequestTrackingAndResponseMappingModule()
        
        # Test 1: Create request
        request_id = "req_12345"
        metadata = {"test": True, "module": "RTRMM"}
        tracker = await rtrmm.create_request(request_id, metadata)
        create_success = tracker is not None and tracker.request_id == request_id
        
        # Test 2: Start processing
        start_success = await rtrmm.start_request_processing(request_id)
        
        # Test 3: Complete request with response
        response_data = {"content": "This is a test response.", "status": "success"}
        complete_success = await rtrmm.complete_request(request_id, response_data)
        
        # Test 4: Retrieve response data
        retrieved = await rtrmm.get_response_data(request_id)
        retrieve_success = retrieved == response_data
        
        # Test 5: Get request status
        status = await rtrmm.get_request_status(request_id)
        status_success = status is not None and status.get("status") == "completed"
        
        test_success = create_success and start_success and complete_success and retrieve_success and status_success
        return {
            "success": test_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": f"RTRMM tests: {sum([create_success, start_success, complete_success, retrieve_success, status_success])}/5 successful",
            "details": {
                "create_success": create_success,
                "start_success": start_success,
                "complete_success": complete_success,
                "retrieve_success": retrieve_success,
                "status_success": status_success,
                "sample_response": retrieved if retrieve_success else None,
                "sample_status": status if status_success else None
            }
        }
    except Exception as e:
        return {
            "success": False,
            "test_code": test_code,
            "test_name": test_name,
            "error": f"Test execution failed: {str(e)}"
        } 

if __name__ == "__main__":
    import json
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler
    result = asyncio.run(test_rtrmm_response_to_request_id_mapping())
    print(json.dumps(result, indent=2)) 