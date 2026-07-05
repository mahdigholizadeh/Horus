"""
Test T00000003: BDM (Binary Data Module) Unit Test
Module(s) Tested: BDM
Description: To test the BDM's ability to generate, compress, and validate binary data.
Success Criteria: Binary files are created successfully, checksums are valid, size limits are enforced.
"""

import asyncio
import json
import sys
import hashlib
import tempfile
import os
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from BDM.bdm import BinaryDataModule

async def test_t00000003():
    test_code = "T00000003"
    test_name = "BDM - Binary Data Module Unit Test"
    results = []
    
    bdm = BinaryDataModule()
    await bdm.start()
    
    try:
        # Step 1: Provide a processed JSON object to the BDM for binary generation
        processed_json = {
            "analysis_result": {
                "system_id": "SOLAR-001",
                "quality_score": 0.95,
                "recommendations": [
                    "System configuration is optimal",
                    "Consider adding battery storage for better efficiency"
                ],
                "technical_specs": {
                    "total_capacity": 2880,
                    "estimated_annual_output": 4200,
                    "efficiency_rating": "A+"
                }
            },
            "metadata": {
                "processed_at": "2024-01-15T10:30:00Z",
                "version": "1.0.0",
                "analysis_type": "comprehensive"
            }
        }
        
        result1 = await bdm.generate_binary_data(processed_json)
        results.append(result1.get("success", False))
        
        # Step 2: Configure the module to use gzip compression and generate binary data
        if result1.get("success", False):
            binary_data = result1.get("binary_data", b"")
            file_path = result1.get("file_path", "")
            
            # Check if binary data was generated
            results.append(len(binary_data) > 0)
            
            # Check if file was created
            results.append(os.path.exists(file_path) if file_path else False)
            
            # Step 3: Generate a sha256 checksum for the created binary file
            if file_path and os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                    calculated_checksum = hashlib.sha256(file_content).hexdigest()
                
                stored_checksum = result1.get("checksum", "")
                results.append(calculated_checksum == stored_checksum)
                
                # Clean up the test file
                try:
                    os.remove(file_path)
                except:
                    pass
            else:
                results.append(False)
        else:
            results.extend([False, False, False])
        
        # Step 4: Attempt to generate data that would exceed the max_binary_size of 50MB
        large_data = {
            "large_content": "x" * (51 * 1024 * 1024),  # 51MB
            "metadata": "test"
        }
        
        result4 = await bdm.generate_binary_data(large_data)
        # Should fail with size limit error
        results.append(
            not result4.get("success", True) and 
            ("size" in result4.get("error", "").lower() or 
             "limit" in result4.get("error", "").lower() or
             "exceed" in result4.get("error", "").lower())
        )
        
        success = all(results)
        
        return {
            "success": success,
            "test_code": test_code,
            "test_name": test_name,
            "message": "BDM unit test passed" if success else "BDM unit test failed",
            "details": {
                "binary_generation_successful": results[0],
                "binary_data_created": results[1] if len(results) > 1 else False,
                "file_created": results[2] if len(results) > 2 else False,
                "checksum_valid": results[3] if len(results) > 3 else False,
                "size_limit_enforced": results[4] if len(results) > 4 else False,
                "results": results
            }
        }
        
    finally:
        await bdm.stop()

