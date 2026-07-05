"""
Test T00000005: IPM (Input Processing Module) Unit Test
Module(s) Tested: IPM
Description: To ensure the IPM correctly sanitizes inputs and performs initial security checks.
Success Criteria: Clean files pass through, malicious files are flagged and rejected.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from IPM.ipm import InputProcessingModule

async def test_t00000005():
    test_code = "T00000005"
    test_name = "IPM - Input Processing Module Unit Test"
    results = []
    
    ipm = InputProcessingModule()
    await ipm.start()
    
    try:
        # Step 1: Submit a clean, valid JSON file
        clean_data = {
            "request_id": "REQ-001",
            "template_data": {
                "system_id": "SOLAR-001",
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
            "processing_options": {
                "analysis_type": "comprehensive",
                "include_binary": True,
                "validation_level": "strict"
            }
        }
        
        result1 = await ipm.process_input(clean_data)
        results.append(result1.get("valid", False))
        
        # Step 2: Submit a file containing a potential injection attack string within a JSON value
        malicious_data = {
            "request_id": "REQ-002",
            "template_data": {
                "system_id": "SOLAR-002",
                "inverter": {
                    "model": "SMA-SB3000",
                    "capacity_kw": 3.0,
                    "efficiency": 0.96,
                    "notes": "'; DROP TABLE users; --"  # SQL injection attempt
                },
                "panels": [
                    {
                        "model": "SunPower-X22",
                        "wattage": 360,
                        "quantity": 8,
                        "efficiency": 0.225,
                        "description": "<script>alert('XSS')</script>"  # XSS attempt
                    }
                ]
            },
            "processing_options": {
                "analysis_type": "comprehensive",
                "include_binary": True,
                "validation_level": "strict"
            }
        }
        
        result2 = await ipm.process_input(malicious_data)
        # Should be flagged and rejected by security checks
        results.append(
            not result2.get("valid", True) and 
            ("security" in result2.get("error", "").lower() or 
             "injection" in result2.get("error", "").lower() or
             "malicious" in result2.get("error", "").lower() or
             "sanitize" in result2.get("error", "").lower())
        )
        
        # Additional test: Test with more sophisticated attack patterns
        sophisticated_attack_data = {
            "request_id": "REQ-003",
            "template_data": {
                "system_id": "SOLAR-003",
                "inverter": {
                    "model": "SMA-SB3000",
                    "capacity_kw": 3.0,
                    "efficiency": 0.96,
                    "config": "{\"command\": \"rm -rf /\", \"type\": \"system\"}"  # Command injection
                }
            }
        }
        
        result3 = await ipm.process_input(sophisticated_attack_data)
        # Should also be rejected
        results.append(
            not result3.get("valid", True) and 
            ("security" in result3.get("error", "").lower() or 
             "injection" in result3.get("error", "").lower() or
             "malicious" in result3.get("error", "").lower())
        )
        
        success = all(results)
        
        return {
            "success": success,
            "test_code": test_code,
            "test_name": test_name,
            "message": "IPM unit test passed" if success else "IPM unit test failed",
            "details": {
                "clean_file_passed": results[0],
                "sql_injection_detected": results[1],
                "command_injection_detected": results[2],
                "results": results
            }
        }
        
    finally:
        await ipm.stop()