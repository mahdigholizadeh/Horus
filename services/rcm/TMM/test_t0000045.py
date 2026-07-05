"""
Test T0000045: FOM - File Output Module
Module(s) Tested: FOM
Description: Test file output and logging functionality.
Success Criteria: The module correctly saves responses and creates error logs.
"""

import asyncio
import tempfile
from pathlib import Path
import sys
import os
import json

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from FOM.fom import FOM

async def test_fom_file_output():
    """Test file output and logging functionality."""
    test_code = "T0000045"
    test_name = "FOM - File Output Module"
    try:
        # Initialize module
        fom = FOM()
        
        # Test response saving
        test_response = {"status": "success", "data": "test_data"}
        request_id = "test_request_45"
        save_result = fom.save_response(test_response, request_id, "A")
        save_success = isinstance(save_result, str) and len(save_result) > 0
        
        # Test error log creation
        error_data = {"error": "Test error message", "code": "TEST_ERROR"}
        error_result = fom.save_error_log(error_data, request_id, "test")
        error_success = isinstance(error_result, str) and len(error_result) > 0
        
        # Test debug info saving
        debug_data = {"debug": "Test debug info", "level": "info"}
        debug_result = fom.save_debug_info(debug_data, request_id, "test")
        debug_success = isinstance(debug_result, str) and len(debug_result) > 0
        
        # Test response listing
        try:
            list_result = fom.list_responses(limit=10)
            list_success = isinstance(list_result, list)
        except Exception as e:
            print(f"[DEBUG] Exception in list_responses: {e}")
            list_success = False
        
        # Test module status
        try:
            status_result = fom.get_status()
            print(f"[DEBUG] get_status output: {status_result}")
            status_success = isinstance(status_result, dict)
        except Exception as e:
            print(f"[DEBUG] Exception in get_status: {e}")
            status_success = False
        
        # Test directory info
        try:
            dir_result = fom.get_directory_info()
            dir_success = isinstance(dir_result, dict)
        except Exception as e:
            print(f"[DEBUG] Exception in get_directory_info: {e}")
            dir_success = False
        
        test_success = (save_success and error_success and debug_success and 
                       list_success and status_success and dir_success)
        
        return {
            "success": test_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": f"File output module successful",
            "details": {
                "save_success": save_success,
                "error_success": error_success,
                "debug_success": debug_success,
                "list_success": list_success,
                "status_success": status_success,
                "dir_success": dir_success
            }
        }
    except Exception as e:
        print(f"[DEBUG] Exception in test_fom_file_output: {e}")
        return {
            "success": False,
            "test_code": test_code,
            "test_name": test_name,
            "error": f"Test execution failed: {str(e)}"
        }

async def main():
    print("=" * 60)
    print("Test T0000045: FOM - File Output Module")
    print("=" * 60)
    result = await test_fom_file_output()
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