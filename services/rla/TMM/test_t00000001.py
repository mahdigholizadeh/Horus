"""
Test T00000001: GVDM (Gateway Validation Data Module) Unit Test
Module(s) Tested: GVDM
Description: Validates JSON payloads against schema and detects basic security threats.
Success Criteria: Valid JSON passes, invalid/malicious JSON is rejected or flagged.
"""

import asyncio
from GVDM.gvdm import GatewayValidationDataModule

async def test_t00000001():
    test_code = "T00000001"
    test_name = "GVDM - JSON Schema & Security Validation"
    results = []
    gvdm = GatewayValidationDataModule()
    await gvdm.start()

    # Step 1: Valid JSON (should pass)
    valid_json = {"field1": "value", "field2": 123}
    result1 = await gvdm.validate_json_data(valid_json)
    results.append(result1.get("valid", False))

    # Step 2: Missing required field (should fail)
    gvdm.validation_rules["required_fields"] = ["field1", "field2"]
    gvdm.validation_rules["field_types"] = {"field1": str, "field2": int}
    invalid_json_missing = {"field1": "value"}
    result2 = await gvdm.validate_json_data(invalid_json_missing)
    # Should be invalid and error should mention missing field2
    results.append(
        not result2.get("valid", True) and any("field2" in err for err in result2.get("errors", []))
    )

    # Step 3: Wrong data type (should fail)
    invalid_json_type = {"field1": "value", "field2": "not_a_number"}
    result3 = await gvdm.validate_json_data(invalid_json_type)
    # Should be invalid and error should mention type
    results.append(
        not result3.get("valid", True) and any("type" in err or "Invalid type" in err for err in result3.get("errors", []))
    )

    # Step 4: XSS payload (should be flagged or rejected)
    xss_json = {"field1": "<script>alert('xss')</script>", "field2": 123}
    result4 = await gvdm.validate_json_data(xss_json)
    # Should be invalid and error should mention script injection or suspicious content
    results.append(
        not result4.get("valid", True) and any(
            "script" in err.lower() or "suspicious" in err.lower() for err in result4.get("errors", [])
        )
    )

    await gvdm.stop()
    success = all(results)
    return {
        "success": success,
        "test_code": test_code,
        "test_name": test_name,
        "message": "All GVDM validation scenarios passed" if success else "Some GVDM validation scenarios failed",
        "details": {
            "steps": results,
            "step_results": [result1, result2, result3, result4]
        }
    }

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(test_t00000001())
    import pprint
    pprint.pprint(result) 