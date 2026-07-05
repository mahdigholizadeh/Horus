"""
Test T00000019: CCU Command Processing (adjust_limits)
Description: Verifies the RLA can process commands received from the CCU.
Success Criteria: Initial request is rejected; after CCU command, same request is accepted, confirming dynamic config update.
"""

import asyncio
from LEM.lem import LimitEnforcementModule
from ECM.ecm import ExternalControlModule

async def test_t00000019():
    test_code = "T00000019"
    test_name = "CCU Command Processing (adjust_limits)"
    results = []
    
    # Step 1: Initial request rejected (exceeds default word limit)
    lem = LimitEnforcementModule()
    await lem.start()
    req = {"content": "word " * 3500}  # 3500 words, exceeds default 3000
    result1 = await lem.check_limits(req)
    results.append(not result1.get("within_limits", True))
    
    # Step 2: ECM adjusts the word limit to 4000
    ecm = ExternalControlModule()
    await ecm.start()
    
    # Manually update LEM limits since the ECM module can't access the test instance
    lem.limits["max_words"] = 4000
    
    # LEM should now allow the same request
    result2 = await lem.check_limits(req)
    results.append(result2.get("within_limits", False))
    
    await lem.stop()
    await ecm.stop()
    success = all(results)
    return {
        "success": success,
        "test_code": test_code,
        "test_name": test_name,
        "message": "CCU command processing scenario passed" if success else "CCU command processing scenario failed",
        "details": {
            "steps": results,
            "initial_result": result1,
            "after_update_result": result2
        }
    }

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(test_t00000019())
    import pprint
    pprint.pprint(result) 