"""
Test T0000043: FBWM - File-based Workflow Module
Module(s) Tested: FBWM
Description: Test file-based workflow processing and routing.
Success Criteria: The module correctly processes JSON files and routes them to appropriate workflows.
"""

import asyncio
import tempfile
from pathlib import Path
import sys
import os
import json

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from FBWM.fbwm import FBWM

async def test_fbwm_file_based_workflow():
    """Test file-based workflow processing and routing."""
    test_code = "T0000043"
    test_name = "FBWM - File-based Workflow Module"
    try:
        # Initialize module
        fbwm = FBWM()
        
        # Create a temp JSON file for processing
        request_id = "test_request_43"
        test_file_data = {
            "type": "workflow", 
            "data": "test_data", 
            "request_ID": request_id,
            "priority_flag": "normal",
            "messages": [
                {"role": "user", "content": "Test message for workflow processing"}
            ]
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(test_file_data, temp_file)
            temp_file_path = Path(temp_file.name)
        print(f"[DEBUG] Temp file created at: {temp_file_path}")
        print(f"[DEBUG] Temp file exists before processing: {temp_file_path.exists()}")
        print(f"[DEBUG] Request ID used: {request_id}")
        
        # Test JSON file processing
        try:
            processing_result = await fbwm.process_file(temp_file_path)
            print(f"[DEBUG] process_file output: {processing_result}")
            processing_success = isinstance(processing_result, dict)
        except Exception as e:
            print(f"[DEBUG] Exception in process_file: {e}")
            processing_success = False
        print(f"[DEBUG] Temp file exists after processing: {temp_file_path.exists()}")
        
        # Test workflow status
        try:
            workflow_key = temp_file_path.stem
            workflow_status = await fbwm.get_workflow_status(workflow_key)
            print(f"[DEBUG] get_workflow_status output: {workflow_status}")
            if workflow_status is None:
                print(f"[DEBUG] fbwm.active_workflows: {fbwm.active_workflows}")
                print(f"[DEBUG] fbwm.completed_workflows: {fbwm.completed_workflows}")
            workflow_status_success = isinstance(workflow_status, dict)
        except Exception as e:
            print(f"[DEBUG] Exception in get_workflow_status: {e}")
            workflow_status_success = False
        
        # Test module status
        try:
            status_result = await fbwm.get_status()
            print(f"[DEBUG] get_status output: {status_result}")
            status_success = isinstance(status_result, dict)
        except Exception as e:
            print(f"[DEBUG] Exception in get_status: {e}")
            status_success = False
        
        # Test cleanup of old files
        try:
            await fbwm.cleanup_old_files()
            print(f"[DEBUG] cleanup_old_files completed successfully.")
            cleanup_success = True
        except Exception as e:
            print(f"[DEBUG] Exception in cleanup_old_files: {e}")
            cleanup_success = False
        
        # Clean up temp file if it still exists
        if temp_file_path.exists():
            temp_file_path.unlink()
            print(f"[DEBUG] Temp file cleaned up.")
        
        test_success = (processing_success and workflow_status_success and status_success and cleanup_success)
        
        return {
            "success": test_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": f"File-based workflow module successful",
            "details": {
                "processing_success": processing_success,
                "workflow_status_success": workflow_status_success,
                "status_success": status_success,
                "cleanup_success": cleanup_success
            }
        }
    except Exception as e:
        print(f"[DEBUG] Exception in test_fbwm_file_based_workflow: {e}")
        return {
            "success": False,
            "test_code": test_code,
            "test_name": test_name,
            "error": f"Test execution failed: {str(e)}"
        }

async def main():
    print("=" * 60)
    print("Test T0000043: FBWM - File-based Workflow Module")
    print("=" * 60)
    result = await test_fbwm_file_based_workflow()
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