"""
Test T00000002: TVM (Template Validation Module) Unit Test
Module(s) Tested: TVM
Description: Ensure TVM applies business rules and schema validation for Horus request templates.
Success Criteria: Valid templates pass validation, business rule violations are detected, missing required fields are caught.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from TVM.tvm import TemplateValidationModule

async def test_t00000002():
    test_code = "T00000002"
    test_name = "TVM - Template Validation Module Unit Test"
    results = []
    
    tvm = TemplateValidationModule()
    await tvm.start()
    
    try:
        # Step 1: Provide a valid request template that conforms to all business rules
        valid_request_template = {
            "id": "SOLAR-001",
            "object": "horus.request",
            "created": 1234567890,
            "model": "horus-v1.0",
            "jfa_data": {
                "flag": {
                    "vald": 1, "calc": 1, "plat": 1, "mpsz": 1,
                    "econ": 1, "rcon": 1, "mode": 1
                },
                "loca": {
                    "Ecit": "Tehran", "Fcit": "Tehran",
                    "lat": 35.6892, "lng": 51.3890
                },
                "cust": {
                    "mode": 1, "need": 1, "npsz": 5
                },
                "sinf": {
                    "mfreg": 1, "mled": 2, "mlcd": 1, "mtele": 1,
                    "mlamp": 5, "mpump": 1, "mcool": 1, "mcamd": 1,
                    "mpc": 2, "mpri": 1, "mwel": 1, "mmlo": 1,
                    "nfreg": 1, "nled": 2, "nlcd": 1, "ntele": 1,
                    "nlamp": 5, "npump": 1, "ncool": 1, "ncamd": 1,
                    "npc": 2, "npri": 1, "nwel": 1, "nmlo": 1
                }
            }
        }
        
        result1 = await tvm.validate_template(valid_request_template)
        results.append(result1.get("valid", False))
        
        # Step 2: Provide a template that violates a business rule (inverter capacity < total panel wattage)
        invalid_request_template = {
            "id": "SOLAR-002",
            "object": "horus.request",
            "created": 1234567891,
            "model": "horus-v1.0",
            "jfa_data": {
                "flag": {
                    "vald": 1, "calc": 1, "plat": 1, "mpsz": 2,  # Invalid mpsz value (should be 0 or 1)
                    "econ": 1, "rcon": 1, "mode": 1
                },
                "loca": {
                    "Ecit": "Tehran", "Fcit": "Tehran",
                    "lat": 35.6892, "lng": 51.3890
                },
                "cust": {
                    "mode": 1, "need": 1, "npsz": 5
                },
                "sinf": {
                    "mfreg": 1, "mled": 2, "mlcd": 1, "mtele": 1,
                    "mlamp": 5, "mpump": 1, "mcool": 1, "mcamd": 1,
                    "mpc": 2, "mpri": 1, "mwel": 1, "mmlo": 1,
                    "nfreg": 1, "nled": 2, "nlcd": 1, "ntele": 1,
                    "nlamp": 5, "npump": 1, "ncool": 1, "ncamd": 1,
                    "npc": 2, "npri": 1, "nwel": 1, "nmlo": 1
                }
            }
        }
        
        result2 = await tvm.validate_template(invalid_request_template)
        # Should fail with business rule violation
        results.append(
            not result2.get("valid", True) and 
            ("range" in str(result2.get("errors", [])).lower() or 
             "value" in str(result2.get("errors", [])).lower() or
             "mpsz" in str(result2.get("errors", [])).lower())
        )
        
        # Step 3: Provide a template that is missing a required field
        missing_field_template = {
            "id": "SOLAR-003",
            "object": "horus.request",
            "created": 1234567892,
            "model": "horus-v1.0",
            "jfa_data": {
                "flag": {
                    "vald": 1, "calc": 1, "plat": 1, "mpsz": 1,
                    "econ": 1, "rcon": 1
                    # Missing "mode" field
                },
                "loca": {
                    "Ecit": "Tehran", "Fcit": "Tehran",
                    "lat": 35.6892, "lng": 51.3890
                },
                "cust": {
                    "mode": 1, "need": 1, "npsz": 5
                },
                "sinf": {
                    "mfreg": 1, "mled": 2, "mlcd": 1, "mtele": 1,
                    "mlamp": 5, "mpump": 1, "mcool": 1, "mcamd": 1,
                    "mpc": 2, "mpri": 1, "mwel": 1, "mmlo": 1,
                    "nfreg": 1, "nled": 2, "nlcd": 1, "ntele": 1,
                    "nlamp": 5, "npump": 1, "ncool": 1, "ncamd": 1,
                    "npc": 2, "npri": 1, "nwel": 1, "nmlo": 1
                }
            }
        }
        
        result3 = await tvm.validate_template(missing_field_template)
        # Should fail schema validation
        results.append(
            not result3.get("valid", True) and 
            ("required" in str(result3.get("errors", [])).lower() or 
             "missing" in str(result3.get("errors", [])).lower() or
             "field" in str(result3.get("errors", [])).lower())
        )
        
        success = all(results)
        
        return {
            "success": success,
            "test_code": test_code,
            "test_name": test_name,
            "message": "TVM unit test passed" if success else "TVM unit test failed",
            "details": {
                "valid_template_passed": results[0],
                "business_rule_violation_detected": results[1],
                "missing_field_detected": results[2],
                "results": results
            }
        }
        
    finally:
        await tvm.stop()