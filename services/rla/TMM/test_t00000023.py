"""
Test T00000023: SQL Injection Attempt
Description: Ensures the input validation pipeline prevents SQL injection attacks.
Success Criteria: Request is rejected by the validation/sanitization layer. Not processed further.
"""

import asyncio
from IVM.ivm import InputValidationModule

async def test_t00000023():
    test_code = "T00000023"
    test_name = "SQL Injection Attempt"
    results = []
    # Step 1: Submit SQL injection vector
    ivm = InputValidationModule()
    await ivm.start()
    sql_injection_payload = {"message": "' OR '1'='1"}
    result = await ivm.validate_input(sql_injection_payload, schema_name="chatbot_request")
    # Should be invalid - check for any validation failure (security, format, or content)
    # The IVM should detect this as either a security threat or suspicious content
    is_rejected = not result.get("valid", True)
    results.append(is_rejected)
    await ivm.stop()
    success = all(results)
    return {
        "success": success,
        "test_code": test_code,
        "test_name": test_name,
        "message": "SQL injection attempt scenario passed" if success else "SQL injection attempt scenario failed",
        "details": {
            "steps": results,
            "validation_result": result
        }
    }

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(test_t00000023())
    import pprint
    pprint.pprint(result) 