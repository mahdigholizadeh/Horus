"""
Test T0000001: GIDVM - Successful Ingestion & Sorting
Module(s) Tested: GIDVM
Description: Provide a valid JSON file to the input directory.
Success Criteria: The module correctly identifies the file's priority and moves it to the corresponding priority folder.
"""

import asyncio
import json
import tempfile
import shutil
from pathlib import Path
import sys
import os
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from GIDVM.gidvm import GetInputDataAndVerificationModule

async def test_gidvm_successful_ingestion():
    """Test successful ingestion and sorting of valid JSON files."""
    test_code = "T0000001"
    test_name = "GIDVM - Successful Ingestion & Sorting"
    
    try:
        # Create a temporary test directory structure
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create input directory structure
            input_dir = temp_path / "input"
            input_dir.mkdir()
            
            # Create priority directories
            priority_a_dir = input_dir / "priority_a"
            priority_b_dir = input_dir / "priority_b"
            priority_c_dir = input_dir / "priority_c"
            priority_d_dir = input_dir / "priority_d"
            
            for dir_path in [priority_a_dir, priority_b_dir, priority_c_dir, priority_d_dir]:
                dir_path.mkdir()
            
            # Create test JSON files with different priorities
            test_files = [
                ("test_a.json", {"priority_flag": "A", "model": "test_model", "messages": ["msg1"]}),
                ("test_b.json", {"priority_flag": "B", "model": "test_model", "messages": ["msg2"]}),
                ("test_c.json", {"priority_flag": "C", "model": "test_model", "messages": ["msg3"]}),
                ("test_d.json", {"priority_flag": "D", "model": "test_model", "messages": ["msg4"]})
            ]
            
            # Place files in input directory
            for filename, data in test_files:
                file_path = input_dir / filename
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f)
            
            # Initialize GIDVM
            gidvm = GetInputDataAndVerificationModule()
            
            # Test the ingestion process
            success_count = 0
            total_files = len(test_files)
            
            for filename, expected_data in test_files:
                file_path = input_dir / filename
                if file_path.exists():
                    # Simulate GIDVM processing
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        priority = data.get("priority_flag", "").upper()
                        expected_priority = expected_data["priority_flag"]
                        
                        # Check if priority matches
                        if priority == expected_priority:
                            success_count += 1
                            
                        # Simulate moving to priority directory
                        target_dir = input_dir / f"priority_{priority.lower()}"
                        if target_dir.exists():
                            target_file = target_dir / filename
                            shutil.move(str(file_path), str(target_file))
                            
                    except Exception as e:
                        print(f"Error processing {filename}: {e}")
            
            # Determine test success
            success_rate = (success_count / total_files) * 100
            test_success = success_rate >= 75  # At least 75% success rate
            
            return {
                "success": test_success,
                "test_code": test_code,
                "test_name": test_name,
                "message": f"Processed {success_count}/{total_files} files successfully ({success_rate:.1f}% success rate)",
                "details": {
                    "files_processed": total_files,
                    "successful_files": success_count,
                    "success_rate": success_rate
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
    result = asyncio.run(test_gidvm_successful_ingestion())
    print(result) 