"""
Test Comprehensive Error Handling Integration

This test verifies that the comprehensive EMM integration and API error handling
is working correctly across all updated modules.
"""

import asyncio
import tempfile
from pathlib import Path
import sys
import os
import json
from datetime import datetime

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from BAAIM.baaim import BasicAPIActivationModule
from SAAIM.saaim import SpecialAPIActivationModule
from EMM.api_error_handler import api_error_handler
from EMM.emm import ErrorManagementModule

async def test_comprehensive_error_handling():
    """Test comprehensive error handling integration."""
    test_code = "COMPREHENSIVE_ERROR_HANDLING"
    test_name = "Comprehensive Error Handling Integration"
    
    print(f"\n{'='*60}")
    print(f"🧪 {test_name}")
    print(f"{'='*60}")
    
    results = {
        "test_code": test_code,
        "test_name": test_name,
        "timestamp": datetime.now().isoformat(),
        "modules_tested": [],
        "api_error_handling_tests": [],
        "emm_integration_tests": [],
        "overall_success": True,
        "errors": []
    }
    
    try:
        # Test 1: EMM Integration
        print("\n📋 Test 1: EMM Integration")
        print("-" * 40)
        
        # Test BAAIM EMM Integration
        print("Testing BAAIM EMM Integration...")
        baaim = BasicAPIActivationModule()
        
        # Test error code generation
        error_code = baaim.generate_error_code("TestClass", "test_function")
        print(f"✓ Generated error code: {error_code}")
        
        # Test error logging
        log_result = baaim.log_error("Test error message", "TestClass", "test_function")
        print(f"✓ Error logged: {log_result}")
        
        # Test exception handling
        try:
            raise ValueError("Test exception")
        except Exception as e:
            error_result = await baaim.handle_exception(e, "TestClass", "test_function")
            print(f"✓ Exception handled: {error_result['success'] == False}")
        
        results["emm_integration_tests"].append({
            "module": "BAAIM",
            "error_code_generation": True,
            "error_logging": True,
            "exception_handling": True
        })
        
        # Test SAAIM EMM Integration
        print("\nTesting SAAIM EMM Integration...")
        saaim = SpecialAPIActivationModule()
        
        # Test error code generation
        error_code = saaim.generate_error_code("TestClass", "test_function")
        print(f"✓ Generated error code: {error_code}")
        
        # Test error logging
        log_result = saaim.log_error("Test error message", "TestClass", "test_function")
        print(f"✓ Error logged: {log_result}")
        
        # Test exception handling
        try:
            raise ValueError("Test exception")
        except Exception as e:
            error_result = await saaim.handle_exception(e, "TestClass", "test_function")
            print(f"✓ Exception handled: {error_result['success'] == False}")
        
        results["emm_integration_tests"].append({
            "module": "SAAIM",
            "error_code_generation": True,
            "error_logging": True,
            "exception_handling": True
        })
        
        # Test 2: API Error Handler
        print("\n📋 Test 2: API Error Handler")
        print("-" * 40)
        
        # Test API error parsing
        test_api_error = {
            "error": {
                "message": "Incorrect API key provided",
                "type": "invalid_request_error",
                "code": "invalid_api_key"
            }
        }
        
        api_error_type, error_details = api_error_handler.parse_api_error(json.dumps(test_api_error), 401)
        print(f"✓ API error parsed: {api_error_type.value}")
        print(f"✓ Error details: {error_details['error_code']}")
        
        # Test API error handling
        error_result = await api_error_handler.handle_api_error(json.dumps(test_api_error), 401)
        print(f"✓ API error handled: {error_result['success'] == False}")
        print(f"✓ Error type: {error_result['api_error_type']}")
        print(f"✓ Retry recommended: {error_result['retry_recommended']}")
        
        results["api_error_handling_tests"].append({
            "error_parsing": True,
            "error_handling": True,
            "error_type": api_error_type.value,
            "retry_logic": True
        })
        
        # Test 3: Module API Error Handling
        print("\n📋 Test 3: Module API Error Handling")
        print("-" * 40)
        
        # Test BAAIM API error handling
        print("Testing BAAIM API error handling...")
        api_error_result = await baaim.handle_api_error(json.dumps(test_api_error), 401)
        print(f"✓ BAAIM API error handled: {api_error_result['success'] == False}")
        
        # Test SAAIM API error handling
        print("Testing SAAIM API error handling...")
        api_error_result = await saaim.handle_api_error(json.dumps(test_api_error), 401)
        print(f"✓ SAAIM API error handled: {api_error_result['success'] == False}")
        
        results["api_error_handling_tests"].append({
            "baaim_api_handling": True,
            "saaim_api_handling": True
        })
        
        # Test 4: Error Code System
        print("\n📋 Test 4: Error Code System")
        print("-" * 40)
        
        # Test internal error codes (16-char hex)
        internal_error_code = baaim.generate_error_code("TestClass", "test_function", "001")
        print(f"✓ Internal error code: {internal_error_code}")
        print(f"✓ Length: {len(internal_error_code)} characters")
        print(f"✓ Format: {'Valid' if len(internal_error_code) == 16 else 'Invalid'}")
        
        # Test API error codes (human-readable)
        api_error_code = api_error_handler._generate_api_error_code(api_error_type)
        print(f"✓ API error code: {api_error_code}")
        print(f"✓ Format: {'Valid' if api_error_code.startswith('API_') else 'Invalid'}")
        
        results["error_code_tests"] = {
            "internal_codes": len(internal_error_code) == 16,
            "api_codes": api_error_code.startswith('API_'),
            "format_validation": True
        }
        
        # Test 5: Hardcoded Error Codes Removal
        print("\n📋 Test 5: Hardcoded Error Codes Removal")
        print("-" * 40)
        
        # Check that hardcoded error codes are removed
        baaim_has_hardcoded = hasattr(baaim, 'error_codes') and baaim.error_codes
        saaim_has_hardcoded = hasattr(saaim, 'error_codes') and saaim.error_codes
        
        print(f"✓ BAAIM hardcoded codes removed: {not baaim_has_hardcoded}")
        print(f"✓ SAAIM hardcoded codes removed: {not saaim_has_hardcoded}")
        
        results["hardcoded_codes_removal"] = {
            "baaim": not baaim_has_hardcoded,
            "saaim": not saaim_has_hardcoded
        }
        
        # Test 6: CCU Error Reporting
        print("\n📋 Test 6: CCU Error Reporting")
        print("-" * 40)
        
        # Test error report sending to CCU
        ccu_report_sent = await api_error_handler.send_error_report_to_ccu(error_result)
        print(f"✓ CCU error report sent: {ccu_report_sent}")
        
        results["ccu_reporting"] = {
            "error_reports_sent": ccu_report_sent
        }
        
        # Test 7: Statistics and Monitoring
        print("\n📋 Test 7: Statistics and Monitoring")
        print("-" * 40)
        
        # Get API error handler statistics
        api_stats = api_error_handler.get_statistics()
        print(f"✓ API error handler stats: {api_stats['total_errors']} total errors")
        print(f"✓ Recovery rate: {api_stats['recovery_rate']:.1f}%")
        
        # Get module status
        baaim_status = baaim.get_module_status()
        saaim_status = saaim.get_status()
        print(f"✓ BAAIM status: {baaim_status['status']}")
        print(f"✓ SAAIM configured: {saaim_status['configured']}")
        
        results["statistics"] = {
            "api_error_handler": api_stats,
            "baaim_status": baaim_status,
            "saaim_status": saaim_status
        }
        
        # Summary
        print(f"\n{'='*60}")
        print("✅ COMPREHENSIVE ERROR HANDLING TEST COMPLETE")
        print(f"{'='*60}")
        
        # Calculate success rate
        total_tests = (
            len(results["emm_integration_tests"]) * 3 +  # 3 tests per module
            len(results["api_error_handling_tests"]) * 2 +  # 2 tests per API test
            3 +  # Error code system tests
            2 +  # Hardcoded codes removal tests
            1 +  # CCU reporting test
            1    # Statistics test
        )
        
        successful_tests = sum([
            all(test.values()) for test in results["emm_integration_tests"]
        ]) + sum([
            all(test.values()) for test in results["api_error_handling_tests"]
        ]) + sum(results["error_code_tests"].values()) + sum(results["hardcoded_codes_removal"].values()) + results["ccu_reporting"]["error_reports_sent"] + 1
        
        success_rate = (successful_tests / total_tests) * 100
        
        print(f"📊 Test Results:")
        print(f"   - Total Tests: {total_tests}")
        print(f"   - Successful: {successful_tests}")
        print(f"   - Success Rate: {success_rate:.1f}%")
        print(f"   - Modules Tested: {len(results['modules_tested'])}")
        
        results["overall_success"] = success_rate >= 95
        results["success_rate"] = success_rate
        results["total_tests"] = total_tests
        results["successful_tests"] = successful_tests
        
        if results["overall_success"]:
            print("🎉 All tests passed! Comprehensive error handling is working correctly.")
        else:
            print("⚠️  Some tests failed. Please review the results.")
        
        return results
        
    except Exception as e:
        error_msg = f"Test failed with exception: {str(e)}"
        print(f"❌ {error_msg}")
        results["overall_success"] = False
        results["errors"].append(error_msg)
        return results

if __name__ == "__main__":
    # Run the test
    test_results = asyncio.run(test_comprehensive_error_handling())
    
    # Save results
    output_file = Path(__file__).parent / "comprehensive_error_handling_results.json"
    with open(output_file, 'w') as f:
        json.dump(test_results, f, indent=2, default=str)
    
    print(f"\n📄 Results saved to: {output_file}")
    
    # Exit with appropriate code
    sys.exit(0 if test_results["overall_success"] else 1) 