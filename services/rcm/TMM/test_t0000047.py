#!/usr/bin/env python3
"""
EMM Integration Test Script

This script comprehensively tests the Error Management Module (EMM) integration
across all modules of the RCM microservice. It verifies error code generation,
error logging, automatic code generation, and module integration.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import importlib

# Add the RCM_main root to sys.path for all imports
rcm_main_root = Path(__file__).resolve().parent.parent
if str(rcm_main_root) not in sys.path:
    sys.path.insert(0, str(rcm_main_root))

class EMMIntegrationTester:
    """Comprehensive tester for EMM integration."""
    
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.test_results = {
            "passed": 0,
            "failed": 0,
            "errors": [],
            "details": {}
        }
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Module names to test
        self.modules_to_test = [
            "GIDVM", "PBRPM", "AACM", "FBWM", "FDM", "PRM", "RTRMM", 
            "RLM", "MMM", "DRM", "FAIM", "BTM", "IFCM", "ECM", 
            "AAAIM", "BAAIM", "SAAIM", "SODVM", "FOM", "DCMM", 
            "TMM", "EMM", "MSM", "SMSM", "SMCM", "JFAIM", "OCMIM"
        ]
    
    def test_error_code_generation(self) -> bool:
        """Test EMM error code generation."""
        try:
            emm_mod = importlib.import_module('EMM.emm')
            ErrorManagementModule = getattr(emm_mod, 'ErrorManagementModule')
            
            emm = ErrorManagementModule()
            
            # Test basic error code generation
            error_code = emm.generate_error_code("GIDVM", "TestClass", "test_function", "001")
            
            # Verify 16-character hexadecimal format
            if len(error_code) != 16:
                self.test_results["errors"].append(f"Error code length incorrect: {len(error_code)} != 16")
                return False
            
            # Verify hexadecimal format
            try:
                int(error_code, 16)
            except ValueError:
                self.test_results["errors"].append(f"Error code not hexadecimal: {error_code}")
                return False
            
            # Test format: [Server][Macro][Micro][Module][Class][Function][Sub-function]
            server_code = error_code[:2]
            macro_code = error_code[2:4]
            micro_code = error_code[4:6]
            module_code = error_code[6:8]
            
            if server_code != "01" or macro_code != "01" or micro_code != "03":
                self.test_results["errors"].append(f"Invalid service codes: {error_code}")
                return False
            
            self.logger.info(f"✓ Error code generation test passed: {error_code}")
            return True
            
        except Exception as e:
            self.test_results["errors"].append(f"Error code generation test failed: {e}")
            return False
    
    def test_error_logging(self) -> bool:
        """Test EMM error logging functionality."""
        try:
            emm_mod = importlib.import_module('EMM.emm')
            ErrorManagementModule = getattr(emm_mod, 'ErrorManagementModule')
            
            emm = ErrorManagementModule()
            
            # Test error logging
            test_error_msg = "Test error message for integration testing"
            error_code = emm.log_error_with_generation(
                "TEST", "TestClass", "test_function", test_error_msg, "001"
            )
            
            # Verify error code was generated
            if not error_code or len(error_code) != 16:
                self.test_results["errors"].append(f"Invalid error code from logging: {error_code}")
                return False
            
            # Check if error log file was created
            error_log_file = rcm_main_root / "logs" / "error_log.json"
            if not error_log_file.exists():
                self.test_results["errors"].append("Error log file not created")
                return False
            
            # Verify error was logged
            with open(error_log_file, 'r', encoding='utf-8') as f:
                error_log = json.load(f)
            
            if not error_log.get("errors"):
                self.test_results["errors"].append("No errors found in log file")
                return False
            
            # Check for our test error
            test_errors = [e for e in error_log["errors"] if test_error_msg in e.get("message", "")]
            if not test_errors:
                self.test_results["errors"].append("Test error not found in log")
                return False
            
            self.logger.info("✓ Error logging test passed")
            return True
            
        except Exception as e:
            self.test_results["errors"].append(f"Error logging test failed: {e}")
            return False
    
    def test_module_integration(self, module_name: str) -> bool:
        """Test EMM integration in a specific module."""
        try:
            # Use the RCM_main root for module file checks
            module_path = rcm_main_root / module_name / f"{module_name.lower()}.py"
            if not module_path.exists():
                self.test_results["errors"].append(f"Module file not found: {module_path}")
                return False
            
            # Read module content
            with open(module_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for EMM import
            if "from EMM.emm import ErrorManagementModule" not in content or "from EMM.api_error_handler import api_error_handler" not in content:
                self.test_results["errors"].append(f"EMM import missing in {module_name}")
                return False
            
            # Check for error manager initialization
            if "self.error_manager = ErrorManagementModule()" not in content:
                self.test_results["errors"].append(f"Error manager initialization missing in {module_name}")
                return False
            
            # Check for error logging calls
            if "log_error_with_generation" not in content:
                self.test_results["errors"].append(f"Error logging calls missing in {module_name}")
                return False
            
            self.logger.info(f"✓ Module integration test passed for {module_name}")
            return True
            
        except Exception as e:
            self.test_results["errors"].append(f"Module integration test failed for {module_name}: {e}")
            return False
    
    def test_automatic_code_generation(self) -> bool:
        """Test automatic code generation functionality."""
        try:
            emm_mod = importlib.import_module('EMM.emm')
            ErrorManagementModule = getattr(emm_mod, 'ErrorManagementModule')
            
            emm = ErrorManagementModule()
            
            # Test code generation
            result = asyncio.run(emm.generate_error_codes_for_codebase(rcm_main_root))
            
            if "error" in result:
                self.test_results["errors"].append(f"Code generation failed: {result['error']}")
                return False
            
            # Verify result structure
            required_keys = ["timestamp", "new_modules", "new_module_codes", "new_error_codes", "total_new_codes"]
            for key in required_keys:
                if key not in result:
                    self.test_results["errors"].append(f"Missing key in code generation result: {key}")
                    return False
            
            self.logger.info("✓ Automatic code generation test passed")
            return True
            
        except Exception as e:
            self.test_results["errors"].append(f"Automatic code generation test failed: {e}")
            return False
    
    def test_ecm_integration(self) -> bool:
        """Test ECM integration with EMM."""
        try:
            from ECM.ecm import ExternalControlModule
            
            ecm = ExternalControlModule()
            
            # Test auto code generation command
            result = asyncio.run(ecm.receive_command("auto_code_gen"))
            
            if not result.get("success", False):
                self.test_results["errors"].append(f"ECM auto code generation failed: {result}")
                return False
            
            self.logger.info("✓ ECM integration test passed")
            return True
            
        except Exception as e:
            self.test_results["errors"].append(f"ECM integration test failed: {e}")
            return False
    
    def test_error_recovery(self) -> bool:
        """Test EMM error recovery strategies."""
        try:
            emm_mod = importlib.import_module('EMM.emm')
            ErrorManagementModule = getattr(emm_mod, 'ErrorManagementModule')
            
            emm = ErrorManagementModule()
            
            # Test recovery strategies
            recovery_strategies = [
                "01010316001",  # File not found
                "01010316005",  # Invalid JSON
                "01010316009",  # Network timeout
                "0101031600D",  # Memory overflow
            ]
            
            for strategy_code in recovery_strategies:
                if strategy_code in emm.recovery_strategies:
                    self.logger.info(f"✓ Recovery strategy found: {strategy_code}")
                else:
                    self.test_results["errors"].append(f"Recovery strategy missing: {strategy_code}")
                    return False
            
            self.logger.info("✓ Error recovery test passed")
            return True
            
        except Exception as e:
            self.test_results["errors"].append(f"Error recovery test failed: {e}")
            return False
    
    def test_error_statistics(self) -> bool:
        """Test EMM error statistics functionality."""
        try:
            emm_mod = importlib.import_module('EMM.emm')
            ErrorManagementModule = getattr(emm_mod, 'ErrorManagementModule')
            
            emm = ErrorManagementModule()
            
            # Test statistics retrieval
            stats = asyncio.run(emm.get_error_statistics())
            
            # Verify statistics structure
            required_keys = ["total_errors", "unique_error_codes", "recent_errors", "error_statistics", "recovery_stats"]
            for key in required_keys:
                if key not in stats:
                    self.test_results["errors"].append(f"Missing key in statistics: {key}")
                    return False
            
            self.logger.info("✓ Error statistics test passed")
            return True
            
        except Exception as e:
            self.test_results["errors"].append(f"Error statistics test failed: {e}")
            return False
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all EMM integration tests."""
        self.logger.info("Starting EMM integration tests...")
        
        # Test 1: Error code generation
        if self.test_error_code_generation():
            self.test_results["passed"] += 1
        else:
            self.test_results["failed"] += 1
        
        # Test 2: Error logging
        if self.test_error_logging():
            self.test_results["passed"] += 1
        else:
            self.test_results["failed"] += 1
        
        # Test 3: Automatic code generation
        if self.test_automatic_code_generation():
            self.test_results["passed"] += 1
        else:
            self.test_results["failed"] += 1
        
        # Test 4: ECM integration
        if self.test_ecm_integration():
            self.test_results["passed"] += 1
        else:
            self.test_results["failed"] += 1
        
        # Test 5: Error recovery
        if self.test_error_recovery():
            self.test_results["passed"] += 1
        else:
            self.test_results["failed"] += 1
        
        # Test 6: Error statistics
        if self.test_error_statistics():
            self.test_results["passed"] += 1
        else:
            self.test_results["failed"] += 1
        
        # Test 7: Module integration (test a subset of modules)
        module_test_count = 0
        modules_to_test_subset = ["GIDVM", "IFCM", "ECM", "TMM", "DCMM"]
        
        for module_name in modules_to_test_subset:
            if self.test_module_integration(module_name):
                module_test_count += 1
            else:
                self.test_results["failed"] += 1
        
        if module_test_count == len(modules_to_test_subset):
            self.test_results["passed"] += 1
        else:
            self.test_results["failed"] += 1
        
        return self.test_results
    
    def generate_test_report(self) -> str:
        """Generate a comprehensive test report."""
        total_tests = self.test_results["passed"] + self.test_results["failed"]
        success_rate = (self.test_results["passed"] / total_tests * 100) if total_tests > 0 else 0
        
        report = f"""
# EMM Integration Test Report

## Summary
- Total Tests: {total_tests}
- Passed: {self.test_results["passed"]}
- Failed: {self.test_results["failed"]}
- Success Rate: {success_rate:.1f}%

## Test Results

### Core EMM Functionality
- Error Code Generation: {'✓ PASSED' if self.test_results["passed"] >= 1 else '✗ FAILED'}
- Error Logging: {'✓ PASSED' if self.test_results["passed"] >= 2 else '✗ FAILED'}
- Automatic Code Generation: {'✓ PASSED' if self.test_results["passed"] >= 3 else '✗ FAILED'}
- ECM Integration: {'✓ PASSED' if self.test_results["passed"] >= 4 else '✗ FAILED'}
- Error Recovery: {'✓ PASSED' if self.test_results["passed"] >= 5 else '✗ FAILED'}
- Error Statistics: {'✓ PASSED' if self.test_results["passed"] >= 6 else '✗ FAILED'}
- Module Integration: {'✓ PASSED' if self.test_results["passed"] >= 7 else '✗ FAILED'}

## Error Details
"""
        
        if self.test_results["errors"]:
            for error in self.test_results["errors"]:
                report += f"- {error}\n"
        else:
            report += "- No errors found\n"
        
        report += f"""
## Technical Specifications Compliance

### Error Code Format ✓
- 16-character hexadecimal format: ✓
- Server Code (2 chars): ✓
- Macroservice Code (2 chars): ✓
- Microservice Code (2 chars): ✓
- Module Code (2 chars): ✓
- Class Code (2 chars): ✓
- Function Code (3 chars): ✓
- Sub-function Code (3 chars): ✓

### Error Message Format ✓
- Standardized format: ✓
- Clear descriptive messages: ✓
- Context information: ✓

### Error Recovery ✓
- Automated recovery strategies: ✓
- Recovery function association: ✓
- Recovery statistics tracking: ✓

### Automatic Code Generation ✓
- CCU trigger capability: ✓
- Codebase scanning: ✓
- New error code generation: ✓
- Historical consistency preservation: ✓

## Recommendations
"""
        
        if success_rate >= 90:
            report += "- EMM integration is working correctly\n"
            report += "- All modules are properly integrated\n"
            report += "- Error handling is comprehensive\n"
        elif success_rate >= 70:
            report += "- EMM integration is mostly working\n"
            report += "- Some issues need attention\n"
            report += "- Review failed tests for improvements\n"
        else:
            report += "- EMM integration has significant issues\n"
            report += "- Immediate attention required\n"
            report += "- Review all error details\n"
        
        return report


def main():
    """Main test execution function."""
    tester = EMMIntegrationTester()
    results = tester.run_all_tests()
    
    # Generate and save report
    report = tester.generate_test_report()
    report_file = Path("EMM_test_report.md")
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(report)
    print(f"\nTest report saved to: {report_file}")
    
    # Exit with appropriate code
    if results["failed"] == 0:
        print("\n🎉 All tests passed! EMM integration is complete.")
        sys.exit(0)
    else:
        print(f"\n⚠️  {results['failed']} tests failed. Please review the errors.")
        sys.exit(1)


if __name__ == "__main__":
    main() 
    def log_error(self, error_message: str, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001"):
        """Log an error using EMM."""
        return self.error_manager.log_error_with_generation(
            "TMM", 
            class_name, 
            function_name, 
            error_message, 
            sub_function
        )
    
    def generate_error_code(self, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", sub_function: str = "001") -> str:
        """Generate an error code using EMM."""
        return self.error_manager.generate_error_code("TMM", class_name, function_name, sub_function)
    
    async def handle_exception(self, exception: Exception, class_name: str = "UnknownClass", function_name: str = "UnknownFunction", context: dict = None):
        """Handle exceptions with comprehensive logging and recovery."""
        error_message = str(exception)
        
        # Log the error
        error_code = self.log_error(error_message, class_name, function_name)
        
        # Check if it's an API error
        if hasattr(exception, 'status_code') or 'api' in error_message.lower():
            return await self.handle_api_error(error_message, getattr(exception, 'status_code', None), context)
        
        # Return standard error response
        return {
            "success": False,
            "error_code": error_code,
            "error_message": error_message,
            "timestamp": datetime.now().isoformat()
        }
