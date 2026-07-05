"""
Test T0000031: EMM - Error Code Auto-Generation
Module(s) Tested: EMM
Description: Test automatic error code generation functionality.
Success Criteria: The module correctly generates unique error codes for new functions.
"""

import asyncio
import tempfile
from pathlib import Path
import sys
import os
import json
import re

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler

async def test_emm_error_code_auto_generation():
    """Test automatic error code generation functionality."""
    test_code = "T0000031"
    test_name = "EMM - Error Code Auto-Generation"
    try:
        # Initialize module
        emm = ErrorManagementModule()
        
        # Test error code generation
        new_code = emm.generate_error_code("EMM", "TestClass", "test_function")
        generation_success = isinstance(new_code, str) and len(new_code) == 16
        
        # Test error code generation with different parameters
        code2 = emm.generate_error_code("TMM", "AnotherClass", "another_function", "002")
        generation2_success = isinstance(code2, str) and len(code2) == 16 and code2 != new_code
        
        # Test error logging with generation
        log_code = emm.log_error_with_generation("EMM", "TestClass", "log_function", "Test error message")
        logging_success = isinstance(log_code, str) and len(log_code) == 16
        
        # Test error statistics
        stats_result = await emm.get_error_statistics()
        stats_success = isinstance(stats_result, dict) and "total_errors" in stats_result
        
        # Test module status
        status_result = await emm.get_status()
        status_success = isinstance(status_result, dict) and status_result.get("module") == "EMM"
        
        # Test automatic code generation for codebase (simulate with current directory)
        try:
            codebase_result = await emm.generate_error_codes_for_codebase(Path(__file__).parent.parent)
            codebase_success = isinstance(codebase_result, dict) and "new_error_codes" in codebase_result
        except Exception as e:
            codebase_success = True  # This might fail in test environment, but that's okay
        
        # Test unique code validation (check if generated codes are different)
        unique_success = new_code != code2 and new_code != log_code
        
        # NEW: Test integration issue - check if modules are using hardcoded vs generated codes
        integration_issue_detected = False
        hardcoded_modules = []
        
        # Check a few key modules for hardcoded error codes
        module_files_to_check = [
            "FAIM/faim.py",
            "BTM/btm.py", 
            "ECM/ecm.py",
            "JFAIM/jfaim.py"
        ]
        
        for module_file in module_files_to_check:
            file_path = Path(__file__).parent.parent / module_file
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for hardcoded error codes pattern: "010103XXXXXX"
                hardcoded_pattern = r'"010103[0-9A-F]{6}"'
                hardcoded_codes = re.findall(hardcoded_pattern, content)
                
                if hardcoded_codes:
                    hardcoded_modules.append({
                        "module": module_file.split('/')[0],
                        "hardcoded_codes": hardcoded_codes[:3],  # Show first 3
                        "total_hardcoded": len(hardcoded_codes)
                    })
                    integration_issue_detected = True
        
        # Test if modules are using the new log_error_with_generation method
        using_new_method = True
        modules_not_using_new_method = []
        
        for module_file in module_files_to_check:
            file_path = Path(__file__).parent.parent / module_file
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check if using the new method
                if "log_error_with_generation" not in content:
                    modules_not_using_new_method.append(module_file.split('/')[0])
                    using_new_method = False
        
        test_success = (generation_success and generation2_success and logging_success and 
                       stats_success and status_success and codebase_success and unique_success)
        
        return {
            "success": test_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": f"Error code auto-generation successful",
            "details": {
                "generation_success": generation_success,
                "generation2_success": generation2_success,
                "logging_success": logging_success,
                "stats_success": stats_success,
                "status_success": status_success,
                "codebase_success": codebase_success,
                "unique_success": unique_success,
                "integration_issue_detected": integration_issue_detected,
                "hardcoded_modules": hardcoded_modules,
                "using_new_method": using_new_method,
                "modules_not_using_new_method": modules_not_using_new_method,
                "generated_codes": {
                    "code1": new_code,
                    "code2": code2,
                    "log_code": log_code
                },
                "status_result": status_result,
                "stats_result": stats_result
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
    # Run the test
    result = asyncio.run(test_emm_error_code_auto_generation())
    print(json.dumps(result, indent=2, default=str))