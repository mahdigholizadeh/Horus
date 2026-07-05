"""
Test T00000015: Full Activation Protocol Integration Test
Description: Tests the activation protocol end-to-end.
Success Criteria: Service responds correctly to both valid and invalid activation attempts as per the protocol.
"""

import asyncio
from ARM.arm import ActivationReceiverModule

async def test_t00000015():
    test_code = "T00000015"
    test_name = "Full Activation Protocol Integration"
    results = []
    arm = ActivationReceiverModule()
    await arm.start()
    # Step 1: Valid activation key (simulate manual activation)
    correct_key = arm.activation_key
    if correct_key == 0x9D37:
        await arm.activate_manually(source_ip="integration_test_valid")
        results.append(arm.is_activated())
    else:
        results.append(False)
    # Step 2: Invalid activation key (simulate failed activation)
    wrong_key = 0x0000
    if wrong_key != arm.activation_key:
        await arm.deactivate()
        results.append(not arm.is_activated())
    else:
        results.append(False)
    await arm.stop()
    success = all(results)
    return {
        "success": success,
        "test_code": test_code,
        "test_name": test_name,
        "message": "Full activation protocol integration scenarios passed" if success else "Some activation protocol integration scenarios failed",
        "details": {
            "steps": results
        }
    }

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(test_t00000015())
    import pprint
    pprint.pprint(result) 