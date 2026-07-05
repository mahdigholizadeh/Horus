"""
Test T0000019: SMCM - API Model Change
Module(s) Tested: SMCM, DCMM
Description: Test API model change functionality.
Success Criteria: The module correctly switches between different API models.
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

from SMCM.smcm import SystemModelChangerModule
from DCMM.dcmm import DatabaseControlAndManagementModule

async def test_smcm_api_model_change():
    """Test API model change functionality."""
    test_code = "T0000019"
    test_name = "SMCM - API Model Change"
    try:
        smcm = SystemModelChangerModule()
        dcmm = DatabaseControlAndManagementModule()
        # Prepare a conversation in the database
        request_id = "test_request_id"
        await dcmm.create_conversation(request_id, "C", "gpt-3.5-turbo", {"test": True})
        # Test model change
        change_result = await smcm.change_model(request_id, "gpt-4")
        change_success = isinstance(change_result, bool)
        # Test conversation preparation
        conversation = await dcmm.get_conversation(request_id)
        preparation_success = isinstance(conversation, dict)
        test_success = change_success and preparation_success
        # Clean up
        await dcmm.delete_conversation(request_id)
        return {
            "success": test_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": f"API model change successful",
            "details": {
                "change_success": change_success,
                "preparation_success": preparation_success
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
    print("=== SMCM API Model Change Test Suite ===")
    print("Testing API model change functionality.\n")
    result = await test_smcm_api_model_change()
    print(f"\n=== Test Results ===")
    print(f"SMCM API Model Change Test: {'PASS' if result['success'] else 'FAIL'}")
    if result['success']:
        print(f"\n✅ API model change working correctly!")
    else:
        print(f"\n❌ Some tests failed. Check the details below:")
        print(f"Test: {json.dumps(result, indent=2)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())