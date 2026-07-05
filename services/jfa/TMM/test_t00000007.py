"""
Test T00000007: FIM (File Interface Module) Unit Test
Module(s) Tested: FIM
Description: To test the FIM's file reading, writing, and persistence capabilities.
Success Criteria: Files are created successfully, data read back is identical to data written.
"""

import asyncio
import json
import sys
import tempfile
import os
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from FIM.fim import FileInterfaceModule

async def test_t00000007():
    test_code = "T00000007"
    test_name = "FIM - File Interface Module Unit Test"
    results = []
    
    fim = FileInterfaceModule()
    await fim.start()
    
    try:
        # Step 1: Use the FIM to write a processed result to a temporary file
        processed_result = {
            "analysis_id": "ANALYSIS-001",
            "system_configuration": {
                "inverter": {
                    "model": "SMA-SB3000",
                    "capacity_kw": 3.0,
                    "efficiency": 0.96
                },
                "panels": [
                    {
                        "model": "SunPower-X22",
                        "wattage": 360,
                        "quantity": 8,
                        "efficiency": 0.225
                    }
                ]
            },
            "analysis_results": {
                "quality_score": 0.92,
                "decision": "approve",
                "recommendations": [
                    "System configuration is optimal",
                    "Consider adding battery storage"
                ]
            },
            "metadata": {
                "processed_at": "2024-01-15T10:30:00Z",
                "version": "1.0.0"
            }
        }
        
        # Create a temporary file path
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            temp_file_path = temp_file.name
        
        # Write the processed result
        write_result = await fim.write_file(temp_file_path, processed_result)
        results.append(write_result.get("success", False))
        
        # Check if file was actually created
        results.append(os.path.exists(temp_file_path))
        
        # Step 2: Use the FIM to read the same file back
        if write_result.get("success", False):
            read_result = await fim.read_file(temp_file_path)
            results.append(read_result.get("success", False))
            
            if read_result.get("success", False):
                read_data = read_result.get("data", {})
                
                # Step 3: Verify data integrity - data read back must be identical to data written
                data_identical = (
                    read_data.get("analysis_id") == processed_result.get("analysis_id") and
                    read_data.get("system_configuration") == processed_result.get("system_configuration") and
                    read_data.get("analysis_results") == processed_result.get("analysis_results") and
                    read_data.get("metadata") == processed_result.get("metadata")
                )
                results.append(data_identical)
                
                # Additional test: Check file size and content
                file_size = os.path.getsize(temp_file_path)
                results.append(file_size > 0)
                
                # Test with different file formats
                # Test binary file writing and reading
                binary_data = b"test binary data for FIM module"
                binary_file_path = temp_file_path.replace('.json', '.bin')
                
                binary_write_result = await fim.write_binary_file(binary_file_path, binary_data)
                results.append(binary_write_result.get("success", False))
                
                if binary_write_result.get("success", False):
                    binary_read_result = await fim.read_binary_file(binary_file_path)
                    results.append(binary_read_result.get("success", False))
                    
                    if binary_read_result.get("success", False):
                        read_binary_data = binary_read_result.get("data", b"")
                        results.append(read_binary_data == binary_data)
                        
                        # Clean up binary test file
                        try:
                            os.remove(binary_file_path)
                        except:
                            pass
                    else:
                        results.append(False)
                else:
                    results.extend([False, False])
            else:
                results.extend([False, False, False, False, False])
        else:
            results.extend([False, False, False, False, False, False])
        
        # Clean up the main test file
        try:
            os.remove(temp_file_path)
        except:
            pass
        
        success = all(results)
        
        return {
            "success": success,
            "test_code": test_code,
            "test_name": test_name,
            "message": "FIM unit test passed" if success else "FIM unit test failed",
            "details": {
                "file_write_successful": results[0],
                "file_created": results[1] if len(results) > 1 else False,
                "file_read_successful": results[2] if len(results) > 2 else False,
                "data_integrity_maintained": results[3] if len(results) > 3 else False,
                "file_size_valid": results[4] if len(results) > 4 else False,
                "binary_write_successful": results[5] if len(results) > 5 else False,
                "binary_read_successful": results[6] if len(results) > 6 else False,
                "binary_data_integrity": results[7] if len(results) > 7 else False,
                "results": results
            }
        }
        
    finally:
        await fim.stop()