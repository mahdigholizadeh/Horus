"""
Test T00000002: IVM (Input Validation Module) Unit Test
Module(s) Tested: IVM
Description: Ensures the IVM's comprehensive validation pipeline correctly processes and sanitizes inputs.
Success Criteria: Clean input is processed, invalid inputs are rejected with appropriate error messages.
"""

import asyncio
from IVM.ivm import InputValidationModule

async def test_t00000002():
    test_code = "T00000002"
    test_name = "IVM - Input Validation Pipeline"
    results = []
    ivm = InputValidationModule()
    await ivm.start()

    # Step 1: Clean, well-formatted input (should pass)
    clean_input = {"message": "This is a valid input string.", "timestamp": "2024-01-01T00:00:00Z"}
    result1 = await ivm.validate_input(clean_input, schema_name="chatbot_request")
    results.append(result1.get("valid", False))

    # Step 2: Invalid characters/formatting (should fail)
    invalid_input = {"message": "Invalid@@@Input###", "timestamp": "2024-01-01T00:00:00Z"}
    result2 = await ivm.validate_input(invalid_input, schema_name="chatbot_request")
    # Should be invalid and error should mention format or suspicious
    results.append(
        not result2.get("valid", True) and any(
            "format" in err.lower() or "suspicious" in err.lower() or "invalid" in err.lower() for err in result2.get("errors", [])
        )
    )

    # Step 3: Fails content quality (gibberish) (should fail)
    gibberish_input = {"message": "asdkjhasd!@#", "timestamp": "2024-01-01T00:00:00Z"}
    result3 = await ivm.validate_input(gibberish_input, schema_name="chatbot_request")
    # Should be invalid and error should mention content or quality
    results.append(
        not result3.get("valid", True) and any(
            "content" in err.lower() or "quality" in err.lower() or "invalid" in err.lower() for err in result3.get("errors", [])
        )
    )

    await ivm.stop()
    success = all(results)
    return {
        "success": success,
        "test_code": test_code,
        "test_name": test_name,
        "message": "All IVM validation scenarios passed" if success else "Some IVM validation scenarios failed",
        "details": {
            "steps": results,
            "step_results": [result1, result2, result3]
        }
    }

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(test_t00000002())
    import pprint
    pprint.pprint(result) 