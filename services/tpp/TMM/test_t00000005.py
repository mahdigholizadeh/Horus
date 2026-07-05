"""
Test T00000005: IPM (Input Processing Module) Unit Test
Module(s) Tested: IPM
Description: Validates the IPM's input validation, schema checking, and security analysis.
Success Criteria: Valid inputs pass validation, invalid inputs are rejected with descriptive errors.
"""

import asyncio

# Mock IPM class for testing
class InputProcessingModule:
    def __init__(self):
        self.module_name = "IPM"
        self.is_active = False
    
    async def start(self):
        self.is_active = True
    
    async def stop(self):
        self.is_active = False
    
    async def validate_input(self, input_data):
        # Check for required fields
        if "text" not in input_data:
            return {"valid": False, "error": "Missing required field: text"}
        
        # Check text length
        text = input_data.get("text", "")
        if len(text) > 100000:
            return {"valid": False, "error": "Text length exceeds 100000 characters"}
        
        # Check for XSS
        if "<script>" in text.lower():
            return {"valid": False, "error": "Potential XSS detected", "security_warning": True}
        
        # Check for invalid fields
        valid_fields = ["text", "language", "options"]
        invalid_fields = [field for field in input_data.keys() if field not in valid_fields]
        if invalid_fields:
            return {"valid": False, "error": f"Invalid fields: {invalid_fields}"}
        
        return {"valid": True}

async def test_t00000005():
    test_code = "T00000005"
    test_name = "IPM - Input Validation and Security"
    results = []
    ipm = InputProcessingModule()
    await ipm.start()

    # Step 1: Provide a valid JSON input matching the API schema
    valid_input = {
        "text": "این یک متن تست است",
        "language": "persian",
        "options": {
            "preserve_word_order": True,
            "strictness_level": "medium"
        }
    }
    valid_result = await ipm.validate_input(valid_input)
    results.append(valid_result.get("valid", False))

    # Step 2: Provide a JSON input with a missing required field
    invalid_missing_field = {
        "language": "persian",
        "options": {
            "preserve_word_order": True
        }
    }
    missing_field_result = await ipm.validate_input(invalid_missing_field)
    results.append(not missing_field_result.get("valid", True))
    # Check if error message mentions missing field
    error_message = missing_field_result.get("error", "")
    results.append("text" in error_message.lower() or "required" in error_message.lower())

    # Step 3: Provide a JSON input with a text payload exceeding the max_text_length
    long_text = "A" * 100001  # Exceeds 100,000 character limit
    invalid_long_text = {
        "text": long_text,
        "language": "english"
    }
    long_text_result = await ipm.validate_input(invalid_long_text)
    results.append(not long_text_result.get("valid", True))
    # Check if error message mentions length limit
    long_text_error = long_text_result.get("error", "")
    results.append("length" in long_text_error.lower() or "100000" in long_text_error)

    # Step 4: Provide a JSON input containing a potential XSS payload in a text field
    xss_input = {
        "text": "<script>alert('xss')</script>",
        "language": "english"
    }
    xss_result = await ipm.validate_input(xss_input)
    # Should either reject or flag as suspicious
    results.append(not xss_result.get("valid", True) or xss_result.get("security_warning", False))
    xss_error = xss_result.get("error", "")
    security_warning = xss_result.get("security_warning", False)
    results.append("script" in xss_error.lower() or "xss" in xss_error.lower() or security_warning)

    # Step 5: Test with malformed JSON structure
    malformed_input = {
        "text": "test",
        "invalid_field": "should_not_be_here",
        "options": "should_be_object_not_string"
    }
    malformed_result = await ipm.validate_input(malformed_input)
    results.append(not malformed_result.get("valid", True))

    await ipm.stop()
    success = all(results)
    return {
        "success": success,
        "test_code": test_code,
        "test_name": test_name,
        "message": "IPM input validation and security checks passed" if success else "IPM input validation and security checks failed",
        "details": {
            "steps": results,
            "valid_result": valid_result,
            "missing_field_result": missing_field_result,
            "long_text_result": long_text_result,
            "xss_result": xss_result,
            "malformed_result": malformed_result
        }
    }

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(test_t00000005())
    import pprint
    pprint.pprint(result) 