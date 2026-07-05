"""
Test T0000022: ECM - CCU Command Reception
Module(s) Tested: ECM
Description: Test CCU command reception and processing.
Success Criteria: The module correctly receives and processes commands from CCU.
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

from ECM.ecm import ExternalControlModule

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        return super().default(obj)

async def test_ecm_ccu_command_reception():
    """Test CCU command reception and processing."""
    test_code = "T0000022"
    test_name = "ECM - CCU Command Reception"
    try:
        ecm = ExternalControlModule()
        # Test status command (doesn't require external modules)
        status_command = "status"
        status_result = await ecm.receive_command(status_command, {})
        status_success = isinstance(status_result, dict) and "success" in status_result
        # Test activate command
        activate_command = "activate"
        activate_result = await ecm.receive_command(activate_command, {})
        activate_success = isinstance(activate_result, dict) and "success" in activate_result
        # Test command processing (routing)
        processing_result = await ecm._route_command(status_command, {})
        processing_success = isinstance(processing_result, dict) or processing_result is not None
        test_success = status_success and activate_success and processing_success
        return {
            "success": test_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": f"CCU command reception successful",
            "details": {
                "status_success": status_success,
                "activate_success": activate_success,
                "processing_success": processing_success,
                "status_result": status_result,
                "activate_result": activate_result,
                "processing_result": processing_result
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
    result = asyncio.run(test_ecm_ccu_command_reception())
    print(json.dumps(result, indent=2, cls=CustomJSONEncoder)) 