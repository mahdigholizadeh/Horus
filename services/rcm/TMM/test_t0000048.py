 #!/usr/bin/env python3
"""
T0000048: Comprehensive Error Handling System Test

This test verifies that all modules have been properly integrated with the new error handling system.
It checks for:
- Removal of hardcoded error codes
- EMM integration (imports, initialization, error logging)
- API error handler integration
- Proper global instance/alias definitions
"""

import asyncio
import importlib
import sys
import os
from pathlib import Path
from typing import Dict, List, Any

# Add parent directory to path to access modules
sys.path.insert(0, str(Path(__file__).parent.parent))

class ErrorHandlingSystemTester:
    """Test the error handling system across all modules."""
    
    def __init__(self):
        self.test_results = {
            "passed": 0,
            "failed": 0,
            "errors": []
        }
        
        # Modules that should have been updated
        self.modules_to_test = [
            "GIDVM", "FDM", "FBWM", "PRM", "FOM", "BTM", "MMM", "MSM",
            "BAAIM", "SAAIM", "AAAIM", "AACM", "OCMIM", "JFAIM",
            "SODVM", "SMSM", "SMCM", "RTRMM", "DCMM", "RLM", "DRM", 
            "FAIM", "PBRPM", "IFCM", "ECM", "TMM"
        ]
    
    def test_module_import(self, module_name: str) -> bool:
        """Test if a module can be imported successfully."""
        try:
            module = importlib.import_module(f"{module_name}.{module_name.lower()}")
            print(f"✓ {module_name} import successful")
            return True
        except Exception as e:
            self.test_results["errors"].append(f"{module_name} import failed: {e}")
            print(f"✗ {module_name} import failed: {e}")
            return False
    
    def test_hardcoded_error_codes_removed(self, module_name: str) -> bool:
        """Test that hardcoded error_codes have been removed."""
        try:
            module_path = Path(f"../{module_name}/{module_name.lower()}.py")
            if not module_path.exists():
                self.test_results["errors"].append(f"{module_name} module file not found")
                return False
            
            with open(module_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for hardcoded error_codes dictionary
            if "self.error_codes = {" in content:
                self.test_results["errors"].append(f"{module_name} still has hardcoded error_codes")
                print(f"✗ {module_name} still has hardcoded error_codes")
                return False
            
            print(f"✓ {module_name} hardcoded error_codes removed")
            return True
            
        except Exception as e:
            self.test_results["errors"].append(f"{module_name} error_codes check failed: {e}")
            print(f"✗ {module_name} error_codes check failed: {e}")
            return False
    
    def test_emm_integration(self, module_name: str) -> bool:
        """Test that EMM integration is present."""
        try:
            module_path = Path(f"../{module_name}/{module_name.lower()}.py")
            if not module_path.exists():
                return False
            
            with open(module_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for EMM imports
            if "from EMM.emm import ErrorManagementModule" not in content:
                self.test_results["errors"].append(f"{module_name} missing EMM import")
                print(f"✗ {module_name} missing EMM import")
                return False
            
            # Check for error manager initialization
            if "self.error_manager = ErrorManagementModule()" not in content:
                self.test_results["errors"].append(f"{module_name} missing error manager initialization")
                print(f"✗ {module_name} missing error manager initialization")
                return False
            
            # Check for error logging methods
            if "log_error_with_generation" not in content:
                self.test_results["errors"].append(f"{module_name} missing error logging calls")
                print(f"✗ {module_name} missing error logging calls")
                return False
            
            print(f"✓ {module_name} EMM integration present")
            return True
            
        except Exception as e:
            self.test_results["errors"].append(f"{module_name} EMM integration check failed: {e}")
            print(f"✗ {module_name} EMM integration check failed: {e}")
            return False
    
    def test_api_error_handler_integration(self, module_name: str) -> bool:
        """Test that API error handler integration is present."""
        try:
            module_path = Path(f"../{module_name}/{module_name.lower()}.py")
            if not module_path.exists():
                return False
            
            with open(module_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for API error handler import
            if "from EMM.api_error_handler import api_error_handler" not in content:
                self.test_results["errors"].append(f"{module_name} missing API error handler import")
                print(f"✗ {module_name} missing API error handler import")
                return False
            
            # Check for handle_api_error method
            if "async def handle_api_error" not in content:
                self.test_results["errors"].append(f"{module_name} missing handle_api_error method")
                print(f"✗ {module_name} missing handle_api_error method")
                return False
            
            print(f"✓ {module_name} API error handler integration present")
            return True
            
        except Exception as e:
            self.test_results["errors"].append(f"{module_name} API error handler check failed: {e}")
            print(f"✗ {module_name} API error handler check failed: {e}")
            return False
    
    def test_module_alias(self, module_name: str) -> bool:
        """Test that module has proper alias for compatibility."""
        try:
            module_path = Path(f"../{module_name}/{module_name.lower()}.py")
            if not module_path.exists():
                return False
            
            with open(module_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for global instance and alias
            if f"{module_name.lower()} = " not in content or f"{module_name} = " not in content:
                self.test_results["errors"].append(f"{module_name} missing global instance/alias")
                print(f"✗ {module_name} missing global instance/alias")
                return False
            
            print(f"✓ {module_name} has proper alias")
            return True
            
        except Exception as e:
            self.test_results["errors"].append(f"{module_name} alias check failed: {e}")
            print(f"✗ {module_name} alias check failed: {e}")
            return False
    
    def test_emm_functionality(self) -> bool:
        """Test EMM core functionality."""
        try:
            from EMM.emm import ErrorManagementModule
            from EMM.api_error_handler import api_error_handler
            
            emm = ErrorManagementModule()
            
            # Test error code generation
            error_code = emm.generate_error_code("TestModule", "TestClass", "test_function")
            if not error_code or len(error_code) != 16:
                self.test_results["errors"].append("EMM error code generation failed")
                print("✗ EMM error code generation failed")
                return False
            
            # Test error logging
            log_result = emm.log_error_with_generation("TestModule", "TestClass", "test_function", "Test error message")
            if not log_result:
                self.test_results["errors"].append("EMM error logging failed")
                print("✗ EMM error logging failed")
                return False
            
            print("✓ EMM core functionality working")
            return True
            
        except Exception as e:
            self.test_results["errors"].append(f"EMM functionality test failed: {e}")
            print(f"✗ EMM functionality test failed: {e}")
            return False
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all error handling system tests."""
        print("=" * 60)
        print("T0000048: ERROR HANDLING SYSTEM COMPREHENSIVE TEST")
        print("=" * 60)
        
        # Test EMM functionality first
        print("\n1. Testing EMM Core Functionality...")
        if self.test_emm_functionality():
            self.test_results["passed"] += 1
        else:
            self.test_results["failed"] += 1
        
        # Test each module
        print(f"\n2. Testing {len(self.modules_to_test)} Modules...")
        for module_name in self.modules_to_test:
            print(f"\n--- Testing {module_name} ---")
            
            module_tests_passed = 0
            total_module_tests = 5
            
            # Test 1: Module import
            if self.test_module_import(module_name):
                module_tests_passed += 1
            
            # Test 2: Hardcoded error codes removed
            if self.test_hardcoded_error_codes_removed(module_name):
                module_tests_passed += 1
            
            # Test 3: EMM integration
            if self.test_emm_integration(module_name):
                module_tests_passed += 1
            
            # Test 4: API error handler integration
            if self.test_api_error_handler_integration(module_name):
                module_tests_passed += 1
            
            # Test 5: Module alias
            if self.test_module_alias(module_name):
                module_tests_passed += 1
            
            # Count module as passed if all tests pass
            if module_tests_passed == total_module_tests:
                self.test_results["passed"] += 1
                print(f"✓ {module_name}: ALL TESTS PASSED")
            else:
                self.test_results["failed"] += 1
                print(f"✗ {module_name}: {module_tests_passed}/{total_module_tests} tests passed")
        
        return self.test_results
    
    def generate_report(self) -> str:
        """Generate a comprehensive test report."""
        total_tests = self.test_results["passed"] + self.test_results["failed"]
        success_rate = (self.test_results["passed"] / total_tests * 100) if total_tests > 0 else 0
        
        report = f"""
{'='*60}
T0000048: ERROR HANDLING SYSTEM TEST REPORT
{'='*60}

SUMMARY:
- Total Modules Tested: {total_tests}
- Passed: {self.test_results["passed"]}
- Failed: {self.test_results["failed"]}
- Success Rate: {success_rate:.1f}%

DETAILED RESULTS:
"""
        
        if self.test_results["errors"]:
            report += "\nERRORS FOUND:\n"
            for error in self.test_results["errors"]:
                report += f"- {error}\n"
        else:
            report += "\n✓ No errors found!\n"
        
        report += f"\n{'='*60}"
        return report


async def main():
    """Main test function."""
    tester = ErrorHandlingSystemTester()
    results = tester.run_all_tests()
    
    print(tester.generate_report())
    
    # Return test result
    if results["failed"] == 0:
        print("🎉 ALL TESTS PASSED! Error handling system is fully operational.")
        return {"success": True, "test_code": "T0000048", "test_name": "Comprehensive Error Handling System Test", "message": "All modules properly integrated with error handling system"}
    else:
        print(f"⚠️  {results['failed']} modules have issues that need attention.")
        return {"success": False, "test_code": "T0000048", "test_name": "Comprehensive Error Handling System Test", "error": f"{results['failed']} modules failed integration checks"}


if __name__ == "__main__":
    result = asyncio.run(main())
    print(f"\nTest Result: {result}")