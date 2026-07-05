"""
Test T00000020: E2E Happy Path Scenario
Description: Tests a complete, successful request flow from activation to response.
Success Criteria: Client receives a final, successful processing acknowledgment. All logs indicate a clean run.
"""

import asyncio
from ARM.arm import ActivationReceiverModule
from LEM.lem import LimitEnforcementModule
from SVM.svm import SpamValidationModule
from OPM.opm import OutputProcessingModule

async def test_t00000020():
    test_code = "T00000020"
    test_name = "E2E Happy Path Scenario"
    results = []
    # Step 1: Successful activation
    arm = ActivationReceiverModule()
    await arm.start()
    await arm.activate_manually(source_ip="e2e_happy_path")
    results.append(arm.is_activated())
    # Step 2: Valid, well-formed request within all limits
    lem = LimitEnforcementModule()
    await lem.start()
    req = {"content": "This is a valid request for E2E happy path."}
    limit_result = await lem.check_limits(req)
    results.append(limit_result.get("within_limits", False))
    svm = SpamValidationModule()
    await svm.start()
    spam_result = await svm.check_spam(req)
    results.append(not spam_result.get("is_spam", True))
    opm = OutputProcessingModule()
    await opm.start()
    output = await opm.process_output(req, {"valid": True, "errors": []}, limit_result)
    results.append(output.get("validation_flag") == 1 and output.get("token_limit_flag") == 1)
    await arm.stop()
    await lem.stop()
    await svm.stop()
    await opm.stop()
    success = all(results)
    return {
        "success": success,
        "test_code": test_code,
        "test_name": test_name,
        "message": "E2E happy path scenario passed" if success else "E2E happy path scenario failed",
        "details": {
            "steps": results,
            "output": output
        }
    }

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(test_t00000020())
    import pprint
    pprint.pprint(result) 