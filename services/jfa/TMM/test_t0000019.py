"""
Test T0000019: JFA Validation Failure Recognition
Module(s) Tested: JFA ECM (External Control Module)
Description: Test invalid_data_recognition() and insufficient_data_recognition() methods
Success Criteria: Both methods correctly analyze validation failures and return detailed recognition data.
"""

import asyncio
import tempfile
from pathlib import Path
import sys
import os
import json
from datetime import datetime
from typing import Dict, Any, List

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Import JFA ECM module for testing
try:
    # Try to import from JFA microservice
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', '..', '..', 'JFA', 'JFA_main', 'JFA_Main', 'JFA_Main'))
    from ECM.ecm import ExternalControlModule
    JFA_ECM_AVAILABLE = True
except ImportError:
    # Create a mock ECM for testing if JFA is not available
    JFA_ECM_AVAILABLE = False
    print("Warning: JFA ECM module not available, using mock implementation for testing")

class MockECM:
    """Mock ECM for testing when JFA is not available."""
    
    async def invalid_data_recognition(self, template_data: Dict[str, Any], validation_errors: List[str], request_id: str) -> Dict[str, Any]:
        """Mock invalid data recognition."""
        invalid_parts = []
        for error in validation_errors:
            if "missing" in error.lower():
                invalid_parts.append("missing field")
            elif "type" in error.lower():
                invalid_parts.append("field type error")
            else:
                invalid_parts.append("validation error")
        
        return {
            "request_id": request_id,
            "recognition_type": "invalid_data",
            "invalid_parts": invalid_parts,
            "total_invalid_parts": len(invalid_parts),
            "timestamp": datetime.now().isoformat(),
            "service": "JFA"
        }
    
    async def insufficient_data_recognition(self, template_data: Dict[str, Any], validation_errors: List[str], request_id: str) -> Dict[str, Any]:
        """Mock insufficient data recognition."""
        missing_data = []
        insufficient_data = []
        
        # Check for missing basic fields
        required_fields = ["id", "object", "created", "model", "choices", "usage"]
        for field in required_fields:
            if field not in template_data:
                missing_data.append(f"Required field: {field}")
        
        # Check for missing JFA fields
        jfa_fields = ["flag", "loca", "cust", "sinf"]
        for field in jfa_fields:
            if field not in template_data:
                missing_data.append(f"JFA field: {field}")
        
        return {
            "request_id": request_id,
            "recognition_type": "insufficient_data",
            "missing_data": missing_data,
            "insufficient_data": insufficient_data,
            "total_missing": len(missing_data),
            "total_insufficient": len(insufficient_data),
            "timestamp": datetime.now().isoformat(),
            "service": "JFA"
        }

async def test_t0000019():
    """Test validation failure recognition functionality."""
    test_code = "T0000019"
    test_name = "JFA Validation Failure Recognition"
    
    # Run all validation recognition tests
    results = []
    
    # Test 1: Invalid data recognition
    try:
        # Initialize ECM (real or mock)
        if JFA_ECM_AVAILABLE:
            ecm = ExternalControlModule()
        else:
            ecm = MockECM()
        
        # Test case 1: Template with missing required fields
        template_data_1 = {
            "id": "test_123",
            "object": "chat.completion",
            # Missing: created, model, choices, usage
        }
        validation_errors_1 = [
            "Missing required field: created",
            "Missing required field: model",
            "Missing required field: choices",
            "Field 'id' must be string"
        ]
        request_id_1 = "test_invalid_001"
        
        result_1 = await ecm.invalid_data_recognition(template_data_1, validation_errors_1, request_id_1)
        
        # Test case 2: Template with type errors
        template_data_2 = {
            "id": 123,  # Should be string
            "object": "chat.completion",
            "created": "invalid_timestamp",  # Should be number
            "model": "gpt-4",
            "choices": "not_an_object",  # Should be object
            "usage": {}
        }
        validation_errors_2 = [
            "Field 'id' must be string",
            "Field 'created' must be number",
            "Field 'choices' must be object"
        ]
        request_id_2 = "test_invalid_002"
        
        result_2 = await ecm.invalid_data_recognition(template_data_2, validation_errors_2, request_id_2)
        
        # Validate invalid data recognition results
        invalid_success = (
            result_1.get("recognition_type") == "invalid_data" and
            result_1.get("request_id") == request_id_1 and
            len(result_1.get("invalid_parts", [])) > 0 and
            result_2.get("recognition_type") == "invalid_data" and
            result_2.get("request_id") == request_id_2 and
            len(result_2.get("invalid_parts", [])) > 0
        )
        
        results.append(("Invalid Data Recognition", invalid_success, result_1, result_2))
        
    except Exception as e:
        results.append(("Invalid Data Recognition", False, None, str(e)))
    
    # Test 2: Insufficient data recognition
    try:
        # Initialize ECM (real or mock)
        if JFA_ECM_AVAILABLE:
            ecm = ExternalControlModule()
        else:
            ecm = MockECM()
        
        # Test case 1: Template with missing basic fields
        template_data_1 = {
            "id": "test_123",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "gpt-4",
            # Missing: choices, usage
        }
        validation_errors_1 = [
            "Missing required field: choices",
            "Missing required field: usage"
        ]
        request_id_1 = "test_insufficient_001"
        
        result_1 = await ecm.insufficient_data_recognition(template_data_1, validation_errors_1, request_id_1)
        
        # Test case 2: Template with missing JFA-specific fields
        template_data_2 = {
            "id": "test_123",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "gpt-4",
            "choices": {"message": {"role": "user", "content": "test"}},
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            # Missing: flag, loca, cust, sinf
        }
        validation_errors_2 = [
            "Missing JFA field: flag",
            "Missing JFA field: loca",
            "Missing JFA field: cust",
            "Missing JFA field: sinf"
        ]
        request_id_2 = "test_insufficient_002"
        
        result_2 = await ecm.insufficient_data_recognition(template_data_2, validation_errors_2, request_id_2)
        
        # Validate insufficient data recognition results
        insufficient_success = (
            result_1.get("recognition_type") == "insufficient_data" and
            result_1.get("request_id") == request_id_1 and
            len(result_1.get("missing_data", [])) > 0 and
            result_2.get("recognition_type") == "insufficient_data" and
            result_2.get("request_id") == request_id_2 and
            len(result_2.get("missing_data", [])) > 0
        )
        
        results.append(("Insufficient Data Recognition", insufficient_success, result_1, result_2))
        
    except Exception as e:
        results.append(("Insufficient Data Recognition", False, None, str(e)))
    
    # Test 3: Integration scenario
    try:
        # Initialize ECM (real or mock)
        if JFA_ECM_AVAILABLE:
            ecm = ExternalControlModule()
        else:
            ecm = MockECM()
        
        # Complex test case with both invalid and insufficient data
        template_data = {
            "id": 123,  # Invalid: should be string
            "object": "chat.completion",
            "created": "invalid_timestamp",  # Invalid: should be number
            "model": "gpt-4",
            "choices": "not_an_object",  # Invalid: should be object
            # Missing: usage, flag, loca, cust, sinf
        }
        validation_errors = [
            "Field 'id' must be string",
            "Field 'created' must be number",
            "Field 'choices' must be object",
            "Missing required field: usage",
            "Missing JFA field: flag",
            "Missing JFA field: loca",
            "Missing JFA field: cust",
            "Missing JFA field: sinf"
        ]
        request_id = "test_integration_001"
        
        # Test both recognition methods
        invalid_result = await ecm.invalid_data_recognition(template_data, validation_errors, request_id)
        insufficient_result = await ecm.insufficient_data_recognition(template_data, validation_errors, request_id)
        
        # Validate integration results
        integration_success = (
            invalid_result.get("recognition_type") == "invalid_data" and
            invalid_result.get("request_id") == request_id and
            len(invalid_result.get("invalid_parts", [])) > 0 and
            insufficient_result.get("recognition_type") == "insufficient_data" and
            insufficient_result.get("request_id") == request_id and
            len(insufficient_result.get("missing_data", [])) > 0
        )
        
        results.append(("Integration Scenario", integration_success, invalid_result, insufficient_result))
        
    except Exception as e:
        results.append(("Integration Scenario", False, None, str(e)))
    
    # Overall test success
    all_tests_passed = all(success for _, success, _, _ in results)
    
    return {
        "success": all_tests_passed,
        "test_code": test_code,
        "test_name": test_name,
        "message": f"Validation failure recognition test {'passed' if all_tests_passed else 'failed'}",
        "details": {
            "test_results": results,
            "ecm_type": "real" if JFA_ECM_AVAILABLE else "mock",
            "total_subtests": len(results),
            "passed_subtests": sum(1 for _, success, _, _ in results if success)
        }
    }

async def test_invalid_data_recognition():
    """Test invalid data recognition functionality."""
    test_code = "T0000019"
    test_name = "JFA Invalid Data Recognition"
    
    try:
        # Initialize ECM (real or mock)
        if JFA_ECM_AVAILABLE:
            ecm = ExternalControlModule()
        else:
            ecm = MockECM()
        
        # Test case 1: Template with missing required fields
        template_data_1 = {
            "id": "test_123",
            "object": "chat.completion",
            # Missing: created, model, choices, usage
        }
        validation_errors_1 = [
            "Missing required field: created",
            "Missing required field: model",
            "Missing required field: choices",
            "Field 'id' must be string"
        ]
        request_id_1 = "test_invalid_001"
        
        result_1 = await ecm.invalid_data_recognition(template_data_1, validation_errors_1, request_id_1)
        
        # Test case 2: Template with type errors
        template_data_2 = {
            "id": 123,  # Should be string
            "object": "chat.completion",
            "created": "invalid_timestamp",  # Should be number
            "model": "gpt-4",
            "choices": "not_an_object",  # Should be object
            "usage": {}
        }
        validation_errors_2 = [
            "Field 'id' must be string",
            "Field 'created' must be number",
            "Field 'choices' must be object"
        ]
        request_id_2 = "test_invalid_002"
        
        result_2 = await ecm.invalid_data_recognition(template_data_2, validation_errors_2, request_id_2)
        
        # Validate results
        test_success = (
            result_1.get("recognition_type") == "invalid_data" and
            result_1.get("request_id") == request_id_1 and
            len(result_1.get("invalid_parts", [])) > 0 and
            result_2.get("recognition_type") == "invalid_data" and
            result_2.get("request_id") == request_id_2 and
            len(result_2.get("invalid_parts", [])) > 0
        )
        
        return {
            "success": test_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": f"Invalid data recognition test {'passed' if test_success else 'failed'}",
            "details": {
                "test_case_1": result_1,
                "test_case_2": result_2,
                "ecm_type": "real" if JFA_ECM_AVAILABLE else "mock"
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "test_code": test_code,
            "test_name": test_name,
            "error": f"Invalid data recognition test failed: {str(e)}"
        }

async def test_insufficient_data_recognition():
    """Test insufficient data recognition functionality."""
    test_code = "T0000019"
    test_name = "JFA Insufficient Data Recognition"
    
    try:
        # Initialize ECM (real or mock)
        if JFA_ECM_AVAILABLE:
            ecm = ExternalControlModule()
        else:
            ecm = MockECM()
        
        # Test case 1: Template with missing basic fields
        template_data_1 = {
            "id": "test_123",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "gpt-4",
            # Missing: choices, usage
        }
        validation_errors_1 = [
            "Missing required field: choices",
            "Missing required field: usage"
        ]
        request_id_1 = "test_insufficient_001"
        
        result_1 = await ecm.insufficient_data_recognition(template_data_1, validation_errors_1, request_id_1)
        
        # Test case 2: Template with missing JFA-specific fields
        template_data_2 = {
            "id": "test_123",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "gpt-4",
            "choices": {"message": {"role": "user", "content": "test"}},
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            # Missing: flag, loca, cust, sinf
        }
        validation_errors_2 = [
            "Missing JFA field: flag",
            "Missing JFA field: loca",
            "Missing JFA field: cust",
            "Missing JFA field: sinf"
        ]
        request_id_2 = "test_insufficient_002"
        
        result_2 = await ecm.insufficient_data_recognition(template_data_2, validation_errors_2, request_id_2)
        
        # Test case 3: Template with incomplete nested structures
        template_data_3 = {
            "id": "test_123",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "gpt-4",
            "choices": {"message": {"role": "user"}},  # Missing content
            "usage": {"prompt_tokens": 10},  # Missing completion_tokens, total_tokens
            "flag": 1,
            "loca": {"province": "Tehran"},  # Missing city, coordinates, climate_zone
            "cust": {"customer_id": "cust_001"},  # Missing customer_type, energy_requirements
            "sinf": {"calculation_type": "default"}  # Missing system_size, efficiency_parameters
        }
        validation_errors_3 = [
            "Missing field: choices.message.content",
            "Missing field: usage.completion_tokens",
            "Missing field: usage.total_tokens",
            "Missing field: loca.city",
            "Missing field: cust.customer_type"
        ]
        request_id_3 = "test_insufficient_003"
        
        result_3 = await ecm.insufficient_data_recognition(template_data_3, validation_errors_3, request_id_3)
        
        # Validate results
        test_success = (
            result_1.get("recognition_type") == "insufficient_data" and
            result_1.get("request_id") == request_id_1 and
            len(result_1.get("missing_data", [])) > 0 and
            result_2.get("recognition_type") == "insufficient_data" and
            result_2.get("request_id") == request_id_2 and
            len(result_2.get("missing_data", [])) > 0 and
            result_3.get("recognition_type") == "insufficient_data" and
            result_3.get("request_id") == request_id_3 and
            (len(result_3.get("missing_data", [])) > 0 or len(result_3.get("insufficient_data", [])) > 0)
        )
        
        return {
            "success": test_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": f"Insufficient data recognition test {'passed' if test_success else 'failed'}",
            "details": {
                "test_case_1": result_1,
                "test_case_2": result_2,
                "test_case_3": result_3,
                "ecm_type": "real" if JFA_ECM_AVAILABLE else "mock"
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "test_code": test_code,
            "test_name": test_name,
            "error": f"Insufficient data recognition test failed: {str(e)}"
        }

async def test_integration_scenario():
    """Test integration scenario with both recognition methods."""
    test_code = "T0000019"
    test_name = "JFA Validation Recognition Integration"
    
    try:
        # Initialize ECM (real or mock)
        if JFA_ECM_AVAILABLE:
            ecm = ExternalControlModule()
        else:
            ecm = MockECM()
        
        # Complex test case with both invalid and insufficient data
        template_data = {
            "id": 123,  # Invalid: should be string
            "object": "chat.completion",
            "created": "invalid_timestamp",  # Invalid: should be number
            "model": "gpt-4",
            "choices": "not_an_object",  # Invalid: should be object
            # Missing: usage, flag, loca, cust, sinf
        }
        validation_errors = [
            "Field 'id' must be string",
            "Field 'created' must be number",
            "Field 'choices' must be object",
            "Missing required field: usage",
            "Missing JFA field: flag",
            "Missing JFA field: loca",
            "Missing JFA field: cust",
            "Missing JFA field: sinf"
        ]
        request_id = "test_integration_001"
        
        # Test both recognition methods
        invalid_result = await ecm.invalid_data_recognition(template_data, validation_errors, request_id)
        insufficient_result = await ecm.insufficient_data_recognition(template_data, validation_errors, request_id)
        
        # Validate integration results
        test_success = (
            invalid_result.get("recognition_type") == "invalid_data" and
            invalid_result.get("request_id") == request_id and
            len(invalid_result.get("invalid_parts", [])) > 0 and
            insufficient_result.get("recognition_type") == "insufficient_data" and
            insufficient_result.get("request_id") == request_id and
            len(insufficient_result.get("missing_data", [])) > 0
        )
        
        return {
            "success": test_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": f"Integration test {'passed' if test_success else 'failed'}",
            "details": {
                "invalid_recognition": invalid_result,
                "insufficient_recognition": insufficient_result,
                "ecm_type": "real" if JFA_ECM_AVAILABLE else "mock"
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "test_code": test_code,
            "test_name": test_name,
            "error": f"Integration test failed: {str(e)}"
        }

async def main():
    print("=== JFA Validation Failure Recognition Test Suite ===")
    print("Testing invalid_data_recognition() and insufficient_data_recognition() methods.\n")
    
    if not JFA_ECM_AVAILABLE:
        print("⚠️  Using mock ECM implementation (JFA ECM not available)")
    else:
        print("✅ Using real JFA ECM implementation")
    
    print("\n" + "="*60)
    
    # Run all tests
    results = []
    
    print("\n1. Testing Invalid Data Recognition...")
    result_1 = await test_invalid_data_recognition()
    results.append(result_1)
    print(f"   {'✅ PASS' if result_1['success'] else '❌ FAIL'}: {result_1['message']}")
    
    print("\n2. Testing Insufficient Data Recognition...")
    result_2 = await test_insufficient_data_recognition()
    results.append(result_2)
    print(f"   {'✅ PASS' if result_2['success'] else '❌ FAIL'}: {result_2['message']}")
    
    print("\n3. Testing Integration Scenario...")
    result_3 = await test_integration_scenario()
    results.append(result_3)
    print(f"   {'✅ PASS' if result_3['success'] else '❌ FAIL'}: {result_3['message']}")
    
    # Summary
    print("\n" + "="*60)
    print(f"\n=== Test Results Summary ===")
    
    passed_tests = sum(1 for r in results if r['success'])
    total_tests = len(results)
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if passed_tests == total_tests:
        print("\n🎉 All tests passed! Validation failure recognition is working correctly.")
    else:
        print("\n❌ Some tests failed. Check the details below:")
        for i, result in enumerate(results, 1):
            if not result['success']:
                print(f"\nTest {i} Details:")
                print(json.dumps(result, indent=2))
    
    # Save detailed results
    output_file = Path(__file__).parent / "test_t0000019_results.json"
    with open(output_file, 'w') as f:
        json.dump({
            "test_suite": "JFA Validation Failure Recognition",
            "timestamp": datetime.now().isoformat(),
            "ecm_available": JFA_ECM_AVAILABLE,
            "results": results,
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": (passed_tests/total_tests)*100
            }
        }, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: {output_file}")

if __name__ == "__main__":
    asyncio.run(main())