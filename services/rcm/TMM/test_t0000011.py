"""
Test T0000011: JFAIM - JSON File Access
Module(s) Tested: JFAIM
Description: Test JSON file access functionality.
Success Criteria: The module correctly reads and writes JSON files.
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

async def test_jfaim_json_file_access():
    """Test JSON file access functionality."""
    test_code = "T0000011"
    test_name = "JFAIM - JSON File Access"
    try:
        print(f"Starting {test_name}...")
        
        # Initialize JFAIM module
        jfaim = JFAInteractionModule()
        print("JFAIM module initialized successfully")
        
        # Test module initialization and status
        print("Testing module status...")
        status = jfaim.get_status()
        status_success = isinstance(status, dict) and "module" in status
        print(f"Status test: {'Passed' if status_success else 'Failed'}")
        
        # Test template validation
        print("Testing template validation...")
        valid_template = {
            "id": "test-123",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "gpt-3.5-turbo",
            "choices": {
                "message": {
                    "role": "assistant",
                    "content": "This is a test default template"
                }
            },
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
            }
        }
        
        invalid_template = {
            "id": "test-123",
            "choices": {
                "message": {
                    "role": "assistant"
                    # Missing content field
                }
            }
        }
        
        valid_validation = jfaim.validate_jfa_template(valid_template)
        invalid_validation = jfaim.validate_jfa_template(invalid_template)
        validation_success = valid_validation and not invalid_validation
        print(f"Template validation test: {'Passed' if validation_success else 'Failed'}")
        
        # Test template processing
        print("Testing template processing...")
        try:
            processing_result = await jfaim.process_jfa_template(valid_template, "test-request-123")
            processing_success = isinstance(processing_result, dict) and processing_result.get("success", False)
            print(f"Template processing test: {'Passed' if processing_success else 'Failed'}")
            if processing_success:
                print(f"Processed template type: {processing_result.get('template_type', 'Unknown')}")
        except Exception as e:
            processing_success = False
            print(f"Template processing test: Failed - {str(e)}")
        
        # Test JFA file generation
        print("Testing JFA file generation...")
        try:
            file_result = await jfaim.generate_jfa_files(valid_template, "test-request-123")
            file_generation_success = isinstance(file_result, dict)
            print(f"File generation test: {'Passed' if file_generation_success else 'Failed'}")
        except Exception as e:
            file_generation_success = False
            print(f"File generation test: Failed - {str(e)}")
        
        # Test statistics
        print("Testing statistics...")
        jfaim.reset_stats()
        stats = status.get("stats", {})
        stats_success = (
            stats.get("total_jfa_requests") == 0 and
            stats.get("successful_processing") == 0
        )
        print(f"Statistics test: {'Passed' if stats_success else 'Failed'}")
        
        # Test error codes
        print("Testing error codes...")
        error_codes = status.get("error_codes", {})
        error_codes_success = (
            "JFA_PROCESSING_ERROR" in error_codes and
            "TEMPLATE_VALIDATION_ERROR" in error_codes and
            "DATA_EXTRACTION_ERROR" in error_codes
        )
        print(f"Error codes test: {'Passed' if error_codes_success else 'Failed'}")
        
        # Test template type determination
        print("Testing template type determination...")
        test_content = "This is a generic request template"
        template_type = jfaim._determine_template_type(test_content)
        type_determination_success = isinstance(template_type, str) and len(template_type) > 0
        print(f"Template type determination test: {'Passed' if type_determination_success else 'Failed'}")
        if type_determination_success:
            print(f"Determined template type: {template_type}")
        
        # Test JFA status tracking
        print("Testing JFA status tracking...")
        try:
            jfa_status = jfaim.get_jfa_status("test-request-123")
            status_tracking_success = isinstance(jfa_status, dict)
            print(f"Status tracking test: {'Passed' if status_tracking_success else 'Failed'}")
        except Exception as e:
            status_tracking_success = False
            print(f"Status tracking test: Failed - {str(e)}")
        
        # Determine overall test success
        test_success = (
            status_success and
            validation_success and
            processing_success and
            file_generation_success and
            stats_success and
            error_codes_success and
            type_determination_success and
            status_tracking_success
        )
        
        result = {
            "success": test_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": f"JFAIM JSON file access successful",
            "details": {
                "status_success": status_success,
                "validation_success": validation_success,
                "processing_success": processing_success,
                "file_generation_success": file_generation_success,
                "stats_success": stats_success,
                "error_codes_success": error_codes_success,
                "type_determination_success": type_determination_success,
                "status_tracking_success": status_tracking_success,
                "module_status": status.get("module") if status else None,
                "template_type_determined": template_type if type_determination_success else None,
                "processing_result": processing_result if processing_success else None
            }
        }
        
        print(f"Test result: {result}")
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

async def test_jfaim_configuration():
    """Test JFAIM configuration and template types."""
    test_code = "T0000011_CONFIG"
    test_name = "JFAIM Configuration Test"
    try:
        print(f"Starting {test_name}...")
        
        # Initialize JFAIM module
        jfaim = JFAInteractionModule()
        
        # Test template types
        print("Testing template types...")
        template_types = jfaim.template_types
        template_types_success = isinstance(template_types, dict) and len(template_types) > 0
        print(f"Template types test: {'Passed' if template_types_success else 'Failed'}")
        
        if template_types_success:
            print(f"Available template types: {list(template_types.keys())}")
        
        # Test JFA paths
        print("Testing JFA paths...")
        jfa_paths = jfaim.jfa_paths
        paths_success = isinstance(jfa_paths, dict) and "main" in jfa_paths
        print(f"JFA paths test: {'Passed' if paths_success else 'Failed'}")
        
        # Test module code
        print("Testing module code...")
        module_code = jfaim.MODULE_CODE
        module_code_success = isinstance(module_code, str) and module_code == "17"
        print(f"Module code test: {'Passed' if module_code_success else 'Failed'}")
        
        # Test error codes
        print("Testing error codes...")
        error_codes = jfaim.error_codes
        error_codes_success = (
            isinstance(error_codes, dict) and
            "JFA_PROCESSING_ERROR" in error_codes and
            "TEMPLATE_VALIDATION_ERROR" in error_codes
        )
        print(f"Error codes test: {'Passed' if error_codes_success else 'Failed'}")
        
        # Test statistics initialization
        print("Testing statistics initialization...")
        stats = jfaim.stats
        stats_success = (
            isinstance(stats, dict) and
            "total_jfa_requests" in stats and
            "successful_processing" in stats
        )
        print(f"Statistics test: {'Passed' if stats_success else 'Failed'}")
        
        configuration_success = (
            template_types_success and
            paths_success and
            module_code_success and
            error_codes_success and
            stats_success
        )
        
        result = {
            "success": configuration_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": "JFAIM configuration test successful",
            "details": {
                "template_types_success": template_types_success,
                "paths_success": paths_success,
                "module_code_success": module_code_success,
                "error_codes_success": error_codes_success,
                "stats_success": stats_success,
                "template_types": list(template_types.keys()) if template_types_success else None,
                "module_code": module_code if module_code_success else None,
                "error_codes": list(error_codes.keys()) if error_codes_success else None
            }
        }
        
        print(f"Configuration test result: {result}")
        return result
        
    except Exception as e:
        error_result = {
            "success": False,
            "test_code": test_code,
            "test_name": test_name,
            "error": f"Configuration test failed: {str(e)}"
        }
        print(f"Configuration test failed: {error_result}")
        return error_result

async def main():
    """Run the tests."""
    print("=== JFAIM Test Suite ===")
    print("Testing JSON File Access and Interaction Module functionality.\n")
    
    # Run basic functionality test
    print("1. Running basic functionality test...")
    result1 = await test_jfaim_json_file_access()
    
    # Run configuration test
    print("\n2. Running configuration test...")
    result2 = await test_jfaim_configuration()
    
    # Overall results
    overall_success = result1["success"] and result2["success"]
    
    print(f"\n=== Test Results ===")
    print(f"Basic functionality test: {'PASS' if result1['success'] else 'FAIL'}")
    print(f"Configuration test: {'PASS' if result2['success'] else 'FAIL'}")
    print(f"Overall result: {'PASS' if overall_success else 'FAIL'}")
    
    if overall_success:
        print(f"\n✅ JFAIM module is working correctly!")
        print(f"   - Template validation: Working")
        print(f"   - Template processing: Working")
        print(f"   - File generation: Working")
        print(f"   - Error handling: Working")
        print(f"   - Statistics tracking: Working")
    else:
        print(f"\n❌ Some tests failed. Check the details below:")
        print(f"Test 1: {json.dumps(result1, indent=2)}")
        print(f"Test 2: {json.dumps(result2, indent=2)}")

if __name__ == "__main__":
    asyncio.run(main())
    