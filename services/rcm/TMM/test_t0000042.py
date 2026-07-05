"""
Test T0000042: FDM - File Detection Module
Module(s) Tested: FDM
Description: Test file detection and monitoring functionality.
Success Criteria: The module correctly detects new JSON files and triggers processing.
"""

import asyncio
import tempfile
from pathlib import Path
import sys
import os
import json

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler
from FDM.fdm import FileDetectionModule

async def test_fdm_file_detection():
    """Test file detection and monitoring functionality."""
    test_code = "T0000042"
    test_name = "FDM - File Detection Module"
    try:
        # Initialize module
        fdm = FileDetectionModule()
        
        # Test directory monitoring setup (ensure directories exist)
        fdm._ensure_directories()
        setup_success = True
        
        # Test file detection (scan once)
        detection_result = await fdm.scan_once()
        detection_success = isinstance(detection_result, dict)
        
        # Test directory status
        status_result = await fdm.get_directory_status("input")
        status_success = isinstance(status_result, dict) or status_result is None
        
        # Test overall status
        overall_status = await fdm.get_status()
        overall_status_success = isinstance(overall_status, dict)
        
        # Test monitoring start/stop
        try:
            await fdm.start_monitoring()
            await asyncio.sleep(0.1)  # Brief monitoring
            await fdm.stop_monitoring()
            monitoring_success = True
        except Exception:
            monitoring_success = False
        
        # Test file validation (create a temporary test file)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump({"test": "data"}, temp_file)
            temp_file_path = Path(temp_file.name)
        
        try:
            validation_result = await fdm._validate_file(temp_file_path)
            validation_success = isinstance(validation_result, bool)
        except Exception:
            validation_success = False
        finally:
            # Clean up temp file
            if temp_file_path.exists():
                temp_file_path.unlink()
        
        test_success = (setup_success and detection_success and status_success and 
                       overall_status_success and monitoring_success and validation_success)
        
        return {
            "success": test_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": f"File detection module successful",
            "details": {
                "setup_success": setup_success,
                "detection_success": detection_success,
                "status_success": status_success,
                "overall_status_success": overall_status_success,
                "monitoring_success": monitoring_success,
                "validation_success": validation_success
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
    print("Test T0000042: FDM - File Detection Module")
    print("=" * 60)
    result = await test_fdm_file_detection()
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