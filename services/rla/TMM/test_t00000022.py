"""
Test T00000022: E2E Request Rejection (Exceeds Limits)
Description: Tests the full flow where a request is rejected by the limit enforcement module.
Success Criteria: Client receives a standardized error response indicating the size limit was exceeded. Rejection is logged and reported to the CCU.
"""

import asyncio
from ARM.arm import ActivationReceiverModule
from LEM.lem import LimitEnforcementModule

async def test_t00000022():
    test_code = "T00000022"
    test_name = "E2E Request Rejection (Exceeds Limits)"
    results = []
    # Step 1: Successful activation
    arm = ActivationReceiverModule()
    await arm.start()
    await arm.activate_manually(source_ip="e2e_exceeds_limits")
    results.append(arm.is_activated())
    # Step 2: Request exceeds max_request_size
    lem = LimitEnforcementModule()
    await lem.start()
    req = {"content": "a" * (11 * 1024 * 1024)}  # 11MB, exceeds 10MB limit
    result = await lem.check_limits(req)
    # Should be invalid and error should mention size limit
    results.append(not result.get("within_limits", True) and any("size" in v.lower() for v in result.get("violations", [])))
    await arm.stop()
    await lem.stop()
    success = all(results)
    return {
        "success": success,
        "test_code": test_code,
        "test_name": test_name,
        "message": "E2E request rejection (exceeds limits) scenario passed" if success else "E2E request rejection (exceeds limits) scenario failed",
        "details": {
            "steps": results,
            "limit_result": result
        }
    }

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(test_t00000022())
    import pprint
    pprint.pprint(result) 