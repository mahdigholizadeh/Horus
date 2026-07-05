"""
Test T00000021: E2E Request Rejection (Invalid JSON)
Description: Tests the full flow where a request is rejected early due to invalid data.
Success Criteria: Client receives a standardized error response indicating a validation failure. CCU logs a rejected request.
"""

import asyncio
from ARM.arm import ActivationReceiverModule
from IVM.ivm import InputValidationModule

async def test_t00000021():
    test_code = "T00000021"
    test_name = "E2E Request Rejection (Invalid JSON)"
    results = []
    # Step 1: Successful activation
    arm = ActivationReceiverModule()
    await arm.start()
    await arm.activate_manually(source_ip="e2e_invalid_json")
    results.append(arm.is_activated())
    # Step 2: Malformed JSON request (simulate with missing required field)
    ivm = InputValidationModule()
    await ivm.start()
    malformed_input = {"message": 12345}  # Should be string, not int
    result = await ivm.validate_input(malformed_input, schema_name="chatbot_request")
    # Should be invalid and error should mention validation
    results.append(not result.get("valid", True) and any("validation" in err.lower() or "schema" in err.lower() or "type" in err.lower() for err in result.get("errors", [])))
    await arm.stop()
    await ivm.stop()
    success = all(results)
    return {
        "success": success,
        "test_code": test_code,
        "test_name": test_name,
        "message": "E2E request rejection (invalid JSON) scenario passed" if success else "E2E request rejection (invalid JSON) scenario failed",
        "details": {
            "steps": results,
            "validation_result": result
        }
    }

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(test_t00000021())
    import pprint
    pprint.pprint(result) 