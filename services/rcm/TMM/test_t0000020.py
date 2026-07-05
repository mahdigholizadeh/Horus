"""
Test T0000020: JFAIM - Handoff to JFA
Module(s) Tested: JFAIM
Description: Test handoff to JFA functionality.
Success Criteria: The module correctly extracts JSON templates and creates handoff files.
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

from JFAIM.jfaim import JFAInteractionModule

async def test_jfaim_handoff_to_jfa():
    """Test handoff to JFA functionality."""
    test_code = "T0000020"
    test_name = "JFAIM - Handoff to JFA"
    try:
        jfaim = JFAInteractionModule()
        # Prepare a valid JFA template (simulate a real API response)
        test_template = {
            "id": "test-123",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "gpt-3.5-turbo",
            "choices": {
                "message": {
                    "role": "assistant",
                    "content": "This is a test generic template"
                }
            },
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
            }
        }
        request_id = "test-123"
        # Test JSON template extraction (processing)
        extraction_result = await jfaim.process_jfa_template(test_template, request_id)
        extraction_success = extraction_result.get("success", False)
        # Test handoff file creation
        handoff_result = await jfaim.generate_jfa_files(test_template, request_id)
        handoff_success = handoff_result.get("success", False)
        test_success = extraction_success and handoff_success
        return {
            "success": test_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": f"Handoff to JFA successful",
            "details": {
                "extraction_success": extraction_success,
                "handoff_success": handoff_success,
                "extraction_result": extraction_result,
                "handoff_result": handoff_result
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
    result = asyncio.run(test_jfaim_handoff_to_jfa())
    print(json.dumps(result, indent=2))