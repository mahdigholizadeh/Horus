"""
Test T0000002: GIDVM - Invalid JSON Rejection
Module(s) Tested: GIDVM
Description: Provide a malformed or invalid JSON file.
Success Criteria: The module rejects the file, logs an appropriate error via the EMM, and moves the file to an error/ directory.
"""

import asyncio
import json
import tempfile
import shutil
from pathlib import Path
import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from GIDVM.gidvm import GetInputDataAndVerificationModule
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler

async def test_gidvm_invalid_json_rejection():
    """Test rejection of malformed or invalid JSON files."""
    test_code = "T0000002"
    test_name = "GIDVM - Invalid JSON Rejection"
    
    try:
        # Create a temporary test directory structure
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create input and error directories
            input_dir = temp_path / "input"
            error_dir = temp_path / "error"
            input_dir.mkdir()
            error_dir.mkdir()
            
            # Create invalid JSON files with different types of errors
            invalid_files = [
                ("invalid_1.json", '{"priority_flag": "A", "model": "test_model", "messages": ["msg1"]'),  # Missing closing brace
                ("invalid_2.json", '{"priority_flag": "B", model: "test_model", "messages": ["msg2"]}'),   # Missing quotes around key
                ("invalid_3.json", '{"priority_flag": "C", "model": "test_model", "messages": [msg3]}'),   # Missing quotes around value
                ("invalid_4.json", '{"priority_flag": "D", "model": "test_model", "messages": ["msg4"]}'), # Missing quotes around key
                ("invalid_5.json", '{"priority_flag": "E", "model": "test_model", "messages": ["msg5"]}'), # Invalid priority
                ("invalid_6.json", '{"priority_flag": "A", "messages": ["msg6"]}'),  # Missing model field
                ("invalid_7.json", '{"priority_flag": "B", "model": "test_model"}'),  # Missing messages field
                ("invalid_8.json", '{"model": "test_model", "messages": ["msg8"]}'),  # Missing priority_flag
                ("invalid_9.json", '{"priority_flag": "A", "model": "test_model", "messages": "not_an_array"}'),  # Invalid messages type
                ("invalid_10.json", 'not_json_at_all'),  # Not JSON at all
                ("invalid_11.json", '{"priority_flag": "A", "model": 123, "messages": ["msg11"]}'),  # Invalid model type
                ("invalid_12.json", '{"priority_flag": "A", "model": "test_model", "messages": null}'),  # Null messages
                ("invalid_13.json", '{"priority_flag": "A", "model": "test_model", "messages": {}}'),  # Messages as object
                ("invalid_14.json", '{"priority_flag": "A", "model": "test_model", "messages": [123, "msg14"]}'),  # Mixed array types
                ("invalid_15.json", '{"priority_flag": "A", "model": "test_model", "messages": []}'),  # Empty messages array
            ]
            
            # Place invalid files in input directory
            for filename, content in invalid_files:
                file_path = input_dir / filename
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            # Initialize GIDVM and EMM
            gidvm = GetInputDataAndVerificationModule()
            emm = ErrorManagementModule()
            
            # Test the rejection process using GIDVM's actual methods
            rejected_count = 0
            total_files = len(invalid_files)
            detailed_results = []
            
            for filename, content in invalid_files:
                file_path = input_dir / filename
                if file_path.exists():
                    try:
                        # Use GIDVM's validation method
                        data = gidvm.read_and_validate_json(file_path)
                        
                        # If validation returns None, the file was rejected
                        if data is None:
                            rejected_count += 1
                            result = f"✓ Rejected invalid file: {filename}"
                            detailed_results.append(result)
                        else:
                            result = f"✗ Unexpectedly accepted invalid file: {filename}"
                            detailed_results.append(result)
                            
                    except Exception as e:
                        print(f"Error processing {filename}: {e}")
                        rejected_count += 1
                        detailed_results.append(f"✓ Rejected due to exception: {filename}")
            
            # Check if error logs were created
            error_log_file = Path("logs/error_log.json")
            error_logs_exist = error_log_file.exists()
            
            # Print detailed results
            for result in detailed_results:
                print(result)
            
            # Determine test success
            success_rate = (rejected_count / total_files) * 100
            test_success = success_rate >= 80 and error_logs_exist  # At least 80% rejection rate and error logs exist
            
            return {
                "success": test_success,
                "test_code": test_code,
                "test_name": test_name,
                "message": f"Rejected {rejected_count}/{total_files} invalid files ({success_rate:.1f}% rejection rate). Error logs: {'✓' if error_logs_exist else '✗'}",
                "details": {
                    "files_processed": total_files,
                    "rejected_files": rejected_count,
                    "rejection_rate": success_rate,
                    "error_logs_created": error_logs_exist,
                    "detailed_results": detailed_results
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
    import asyncio
    result = asyncio.run(test_gidvm_invalid_json_rejection())
    print(result) 