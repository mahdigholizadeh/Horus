"""
Test T00000006: OPM (Output Processing Module) Unit Test
Module(s) Tested: OPM
Description: Ensures the OPM correctly formats the final output, including the legacy TPP_flag.
Success Criteria: Output is correctly structured JSON with TPP_flag: 1 for legacy compatibility.
"""

import asyncio

# Mock OPM class for testing
class OutputProcessingModule:
    def __init__(self):
        self.module_name = "OPM"
        self.is_active = False
    
    async def start(self):
        self.is_active = True
    
    async def stop(self):
        self.is_active = False
    
    async def format_output(self, processed_data):
        # Always include TPP_flag for legacy compatibility
        output = {
            "TPP_flag": 1,
            **processed_data
        }
        return output

async def test_t00000006():
    test_code = "T00000006"
    test_name = "OPM - Output Formatting and Legacy Support"
    results = []
    opm = OutputProcessingModule()
    await opm.start()

    # Step 1: Provide the OPM with a processed text object and associated metadata
    processed_data = {
        "processed_text": "This is a filtered sample text",
        "original_text": "This is a testspamword sample text",
        "language_detected": "english",
        "confidence": 0.95,
        "filtering_stats": {
            "words_removed": 1,
            "spam_detected": True
        },
        "processing_time": 0.125,
        "timestamp": "2024-01-15T10:30:00Z"
    }

    # Step 2: Generate the final output
    final_output = await opm.format_output(processed_data)
    
    # Step 3: Verify output structure
    results.append(isinstance(final_output, dict))
    
    # Step 4: Check for TPP_flag: 1 for legacy compatibility
    tpp_flag = final_output.get("TPP_flag")
    results.append(tpp_flag == 1)
    
    # Step 5: Verify other required fields are present
    results.append("processed_text" in final_output)
    results.append("original_text" in final_output)
    results.append("language_detected" in final_output)
    results.append("confidence" in final_output)
    
    # Step 6: Verify data integrity
    results.append(final_output["processed_text"] == processed_data["processed_text"])
    results.append(final_output["original_text"] == processed_data["original_text"])
    results.append(final_output["language_detected"] == processed_data["language_detected"])
    
    # Step 7: Test with different data types
    persian_data = {
        "processed_text": "این یک متن فیلتر شده است",
        "original_text": "این یک متن تست است",
        "language_detected": "persian",
        "confidence": 0.88,
        "filtering_stats": {
            "words_removed": 0,
            "spam_detected": False
        }
    }
    
    persian_output = await opm.format_output(persian_data)
    results.append(persian_output.get("TPP_flag") == 1)
    results.append(persian_output["language_detected"] == "persian")
    
    # Step 8: Test error handling
    error_data = {
        "error": "Processing failed",
        "error_code": "PROCESSING_ERROR",
        "timestamp": "2024-01-15T10:30:00Z"
    }
    
    error_output = await opm.format_output(error_data)
    results.append(error_output.get("TPP_flag") == 1)  # Should still include TPP_flag even for errors
    results.append("error" in error_output)

    await opm.stop()
    success = all(results)
    return {
        "success": success,
        "test_code": test_code,
        "test_name": test_name,
        "message": "OPM output formatting and legacy support passed" if success else "OPM output formatting and legacy support failed",
        "details": {
            "steps": results,
            "final_output": final_output,
            "persian_output": persian_output,
            "error_output": error_output
        }
    }

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(test_t00000006())
    import pprint
    pprint.pprint(result) 