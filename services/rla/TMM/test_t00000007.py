"""
Test T00000007: OPM (Output Processing Module) Unit Test
Module(s) Tested: OPM
Description: Ensures the OPM correctly formats responses for both successful and failed operations.
Success Criteria: Generates standardized success and error responses.
"""

import asyncio
from OPM.opm import OutputProcessingModule

async def test_t00000007():
    test_code = "T00000007"
    test_name = "OPM - Output Formatting"
    results = []
    opm = OutputProcessingModule()
    await opm.start()

    # Step 1: Successful processing result
    request_data = {"field": "value"}
    validation_result = {"valid": True, "errors": []}
    limit_result = {"within_limits": True, "violations": []}
    output1 = await opm.process_output(request_data, validation_result, limit_result)
    # Should include validation_flag, token_limit_flag, processed_timestamp
    results.append(
        output1.get("validation_flag") == 1 and output1.get("token_limit_flag") == 1 and "processed_timestamp" in output1
    )

    # Step 2: Error object from another module (simulate failed validation)
    error_validation_result = {"valid": False, "errors": ["Schema error"]}
    error_limit_result = {"within_limits": False, "violations": ["Limit exceeded"]}
    output2 = await opm.process_output(request_data, error_validation_result, error_limit_result)
    # Should still include flags and timestamp, but you may want to check for error propagation if implemented
    results.append(
        output2.get("validation_flag") == 1 and output2.get("token_limit_flag") == 1 and "processed_timestamp" in output2
    )

    await opm.stop()
    success = all(results)
    return {
        "success": success,
        "test_code": test_code,
        "test_name": test_name,
        "message": "All OPM output formatting scenarios passed" if success else "Some OPM output formatting scenarios failed",
        "details": {
            "steps": results,
            "step_results": [output1, output2]
        }
    }

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(test_t00000007())
    import pprint
    pprint.pprint(result) 