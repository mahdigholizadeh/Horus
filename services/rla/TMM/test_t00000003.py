"""
Test T00000003: LEM (Limit Enforcement Module) Unit Test
Module(s) Tested: LEM
Description: Verifies that the LEM correctly enforces word, token, and request size limits.
Success Criteria: Requests within limits are approved, those exceeding are rejected with 'Limit Exceeded' error.
"""

import asyncio
from LEM.lem import LimitEnforcementModule

async def test_t00000003():
    test_code = "T00000003"
    test_name = "LEM - Limit Enforcement"
    results = []
    lem = LimitEnforcementModule()
    await lem.start()

    # Step 1: Word count just below the 3000-word limit (should approve)
    req1 = {"content": "word " * 2999}
    result1 = await lem.check_limits(req1)
    results.append(result1.get("within_limits", False))
    print("Step 1 result:", result1)

    # Step 2: Word count just above the 3000-word limit (should reject)
    req2 = {"content": "word " * 3001}
    result2 = await lem.check_limits(req2)
    results.append(
        not result2.get("within_limits", True) and any("word count" in v.lower() for v in result2.get("violations", []))
    )
    print("Step 2 result:", result2)

    # Step 3: Token count just below the 200,000-token limit (should approve)
    # 50,000 tokens = 200,000 chars (since len(text) // 4)
    req3 = {"content": "a" * 200000}  # 200,000 chars, 50,000 tokens
    result3 = await lem.check_limits(req3)
    results.append(result3.get("within_limits", False))
    print("Step 3 result:", result3)

    # Step 4: Token count just above the 200,000-token limit (should reject)
    req4 = {"content": "a" * 200004}  # 200,004 chars, 50,001 tokens
    result4 = await lem.check_limits(req4)
    results.append(
        not result4.get("within_limits", True) and any("token count" in v.lower() for v in result4.get("violations", []))
    )
    print("Step 4 result:", result4)

    # Step 5: Size 500KB (should approve, and token count under limit)
    req5 = {"content": "b" * 512000}  # 512,000 bytes, 128,000 tokens
    result5 = await lem.check_limits(req5)
    results.append(result5.get("within_limits", False))
    print("Step 5 result:", result5)

    # Step 6: Size 1.1MB (should reject)
    req6 = {"content": "c" * 1150000}  # 1,150,000 bytes, over 1MB
    result6 = await lem.check_limits(req6)
    results.append(
        not result6.get("within_limits", True) and any("request size" in v.lower() for v in result6.get("violations", []))
    )
    print("Step 6 result:", result6)

    await lem.stop()
    success = all(results)
    return {
        "success": success,
        "test_code": test_code,
        "test_name": test_name,
        "message": "All LEM limit enforcement scenarios passed" if success else "Some LEM limit enforcement scenarios failed",
        "details": {
            "steps": results,
            "step_results": [result1, result2, result3, result4, result5, result6]
        }
    }

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(test_t00000003())
    import pprint
    pprint.pprint(result) 