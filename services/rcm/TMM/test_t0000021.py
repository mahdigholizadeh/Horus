"""
Test T0000021: OCMIM - Handoff to OCM
Module(s) Tested: OCMIM
Description: Test handoff to OCM functionality.
Success Criteria: The module correctly creates response files for OCM handoff.
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

from OCMIM.ocmim import OCMInteractionModule

async def test_ocmim_handoff_to_ocm():
    """Test handoff to OCM functionality."""
    test_code = "T0000021"
    test_name = "OCMIM - Handoff to OCM"
    try:
        ocmim = OCMInteractionModule()
        # Test response handoff
        test_response = {"response": "Test response", "request_id": "test_123"}
        request_id = "test_123"
        handoff_result = await ocmim.handoff_response(request_id, test_response, "success")
        handoff_success = handoff_result.get("success", False)
        # Test file creation (delivery)
        file_result = await ocmim.deliver_response(request_id, "file")
        file_success = file_result.get("success", False)
        test_success = handoff_success and file_success
        return {
            "success": test_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": f"Handoff to OCM successful",
            "details": {
                "handoff_success": handoff_success,
                "file_success": file_success,
                "handoff_result": handoff_result,
                "file_result": file_result
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
    result = asyncio.run(test_ocmim_handoff_to_ocm())
    print(json.dumps(result, indent=2))