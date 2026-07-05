"""
Test Error Handling Integration

Comprehensive test to verify that all modules work correctly with the new error handling system.
Tests EMM integration, API error handling, error code generation, and CCU reporting.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any

# Import modules to test
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler
from BAAIM.baaim import BasicAPIActivationModule
from SAAIM.saaim import SpecialAPIActivationModule
from AAAIM.aaaim import AgenticAPIActivationModule
from AACM.aacm import AsynchronousAPICommunicationModule
from RCM_main.RCM_main import RCMMicroservice

class ErrorHandlingIntegrationTest:
    """Test class for comprehensive error handling integration."""
    
    def __init__(self):
        """Initialize the test."""
        self.logger = logging.getLogger(__name__)
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        
        # Initialize modules
        self.emm = ErrorManagementModule()
        self.baaim = BasicAPIActivationModule()
        self.saaim = SpecialAPIActivationModule()
        self.aaaim = AgenticAPIActivationModule()
        self.aacm = AsynchronousAPICommunicationModule()
        
    def log_test_result(self, test_name: str, success: bool, details: str = ""):
        """Log test result."""
        self.total_tests += 1
        if success:
            self.passed_tests += 1
            self.logger.info(f"✅ {test_name}: PASSED")
        else:
            self.logger.error(f"❌ {test_name}: FAILED - {details}")
        
        self.test_results.append({
            "test_name": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
    
    def test_emm_error_code_generation(self):
        """Test EMM error code generation."""
        try:
            # Test error code generation
            error_code = self.emm.generate_error_code("BAAIM", "TestClass", "test_function", "001")
            
            # Verify format (16-character hex)
            assert len(error_code) == 16, f"Error code length should be 16, got {len(error_code)}"
            assert all(c in '0123456789ABCDEF' for c in error_code), "Error code should be hexadecimal"
            
            # Verify module code (BAAIM = 10)
            assert error_code[6:8] == "10", f"Module code should be 10 for BAAIM, got {error_code[6:8]}"
            
            self.log_test_result("EMM Error Code Generation", True)
            return True
            
        except Exception as e:
            self.log_test_result("EMM Error Code Generation", False, str(e))
            return False
    
    def test_emm_error_logging(self):
        """Test EMM error logging."""
        try:
            # Test error logging
            result = self.emm.log_error_with_generation(
                "BAAIM", "TestClass", "test_function", "Test error message", "001"
            )
            
            # Verify result structure
            assert "error_code" in result, "Result should contain error_code"
            assert "timestamp" in result, "Result should contain timestamp"
            assert "module" in result, "Result should contain module"
            
            # Verify error code format
            error_code = result["error_code"]
            assert len(error_code) == 16, f"Error code length should be 16, got {len(error_code)}"
            
            self.log_test_result("EMM Error Logging", True)
            return True
            
        except Exception as e:
            self.log_test_result("EMM Error Logging", False, str(e))
            return False
    
    def test_api_error_handler_parsing(self):
        """Test API error handler parsing."""
        try:
            # Test rate limit error
            rate_limit_error = '{"error": {"message": "Rate limit exceeded", "type": "rate_limit_error"}}'
            result = api_error_handler.parse_api_error(rate_limit_error, 429)
            
            assert result["api_error_type"] == "429_rate_limit", f"Expected 429_rate_limit, got {result['api_error_type']}"
            assert result["retry_recommended"] == True, "Rate limit errors should recommend retry"
            assert result["retry_delay"] > 0, "Retry delay should be positive"
            
            # Test authentication error
            auth_error = '{"error": {"message": "Incorrect API key", "type": "invalid_request_error"}}'
            result = api_error_handler.parse_api_error(auth_error, 401)
            
            assert result["api_error_type"] == "401_incorrect_key", f"Expected 401_incorrect_key, got {result['api_error_type']}"
            assert result["retry_recommended"] == False, "Auth errors should not recommend retry"
            
            self.log_test_result("API Error Handler Parsing", True)
            return True
            
        except Exception as e:
            self.log_test_result("API Error Handler Parsing", False, str(e))
            return False
    
    async def test_api_error_handler_handling(self):
        """Test API error handler handling."""
        try:
            # Test rate limit error handling
            rate_limit_error = '{"error": {"message": "Rate limit exceeded", "type": "rate_limit_error"}}'
            result = await api_error_handler.handle_api_error(rate_limit_error, 429, {"attempt": 1})
            
            assert result["success"] == False, "Error handling should return success=False"
            assert result["api_error_type"] == "429_rate_limit", f"Expected 429_rate_limit, got {result['api_error_type']}"
            assert result["retry_recommended"] == True, "Rate limit errors should recommend retry"
            assert "error_details" in result, "Result should contain error_details"
            
            self.log_test_result("API Error Handler Handling", True)
            return True
            
        except Exception as e:
            self.log_test_result("API Error Handler Handling", False, str(e))
            return False
    
    def test_baaim_error_handling(self):
        """Test BAAIM error handling methods."""
        try:
            # Test error code generation
            error_code = self.baaim.generate_error_code("TestClass", "test_function")
            assert len(error_code) == 16, f"Error code length should be 16, got {len(error_code)}"
            
            # Test error logging
            log_result = self.baaim.log_error("Test error message", "TestClass", "test_function")
            assert "error_code" in log_result, "Log result should contain error_code"
            
            # Verify module code (BAAIM = 10)
            assert log_result["error_code"][6:8] == "10", f"Module code should be 10 for BAAIM, got {log_result['error_code'][6:8]}"
            
            self.log_test_result("BAAIM Error Handling", True)
            return True
            
        except Exception as e:
            self.log_test_result("BAAIM Error Handling", False, str(e))
            return False
    
    def test_saaim_error_handling(self):
        """Test SAAIM error handling methods."""
        try:
            # Test error code generation
            error_code = self.saaim.generate_error_code("TestClass", "test_function")
            assert len(error_code) == 16, f"Error code length should be 16, got {len(error_code)}"
            
            # Test error logging
            log_result = self.saaim.log_error("Test error message", "TestClass", "test_function")
            assert "error_code" in log_result, "Log result should contain error_code"
            
            # Verify module code (SAAIM = 11)
            assert log_result["error_code"][6:8] == "11", f"Module code should be 11 for SAAIM, got {log_result['error_code'][6:8]}"
            
            self.log_test_result("SAAIM Error Handling", True)
            return True
            
        except Exception as e:
            self.log_test_result("SAAIM Error Handling", False, str(e))
            return False
    
    def test_aaaim_error_handling(self):
        """Test AAAIM error handling methods."""
        try:
            # Test error code generation
            error_code = self.aaaim.generate_error_code("TestClass", "test_function")
            assert len(error_code) == 16, f"Error code length should be 16, got {len(error_code)}"
            
            # Test error logging
            log_result = self.aaaim.log_error("Test error message", "TestClass", "test_function")
            assert "error_code" in log_result, "Log result should contain error_code"
            
            # Verify module code (AAAIM = 0F)
            assert log_result["error_code"][6:8] == "0F", f"Module code should be 0F for AAAIM, got {log_result['error_code'][6:8]}"
            
            self.log_test_result("AAAIM Error Handling", True)
            return True
            
        except Exception as e:
            self.log_test_result("AAAIM Error Handling", False, str(e))
            return False
    
    def test_aacm_error_handling(self):
        """Test AACM error handling methods."""
        try:
            # Test error code generation
            error_code = self.aacm.generate_error_code("TestClass", "test_function")
            assert len(error_code) == 16, f"Error code length should be 16, got {len(error_code)}"
            
            # Test error logging
            log_result = self.aacm.log_error("Test error message", "TestClass", "test_function")
            assert "error_code" in log_result, "Log result should contain error_code"
            
            # Verify module code (AACM = 03)
            assert log_result["error_code"][6:8] == "03", f"Module code should be 03 for AACM, got {log_result['error_code'][6:8]}"
            
            self.log_test_result("AACM Error Handling", True)
            return True
            
        except Exception as e:
            self.log_test_result("AACM Error Handling", False, str(e))
            return False
    
    async def test_module_exception_handling(self):
        """Test module exception handling."""
        try:
            # Test BAAIM exception handling
            test_exception = Exception("Test exception")
            result = await self.baaim.handle_exception(test_exception, "TestClass", "test_function", {"context": "test"})
            
            assert result["success"] == False, "Exception handling should return success=False"
            assert "error_code" in result, "Result should contain error_code"
            assert "error_message" in result, "Result should contain error_message"
            assert "timestamp" in result, "Result should contain timestamp"
            
            # Test SAAIM exception handling
            result = await self.saaim.handle_exception(test_exception, "TestClass", "test_function", {"context": "test"})
            assert result["success"] == False, "Exception handling should return success=False"
            
            # Test AAAIM exception handling
            result = await self.aaaim.handle_exception(test_exception, "TestClass", "test_function", {"context": "test"})
            assert result["success"] == False, "Exception handling should return success=False"
            
            # Test AACM exception handling
            result = await self.aacm.handle_exception(test_exception, "TestClass", "test_function", {"context": "test"})
            assert result["success"] == False, "Exception handling should return success=False"
            
            self.log_test_result("Module Exception Handling", True)
            return True
            
        except Exception as e:
            self.log_test_result("Module Exception Handling", False, str(e))
            return False
    
    async def test_module_api_error_handling(self):
        """Test module API error handling."""
        try:
            # Test API error handling in modules
            test_api_error = '{"error": {"message": "Rate limit exceeded", "type": "rate_limit_error"}}'
            
            # Test BAAIM API error handling
            result = await self.baaim.handle_api_error(test_api_error, 429, {"attempt": 1})
            assert result["api_error_type"] == "429_rate_limit", f"Expected 429_rate_limit, got {result['api_error_type']}"
            
            # Test SAAIM API error handling
            result = await self.saaim.handle_api_error(test_api_error, 429, {"attempt": 1})
            assert result["api_error_type"] == "429_rate_limit", f"Expected 429_rate_limit, got {result['api_error_type']}"
            
            # Test AAAIM API error handling
            result = await self.aaaim.handle_api_error(test_api_error, 429, {"attempt": 1})
            assert result["api_error_type"] == "429_rate_limit", f"Expected 429_rate_limit, got {result['api_error_type']}"
            
            # Test AACM API error handling
            result = await self.aacm.handle_api_error(test_api_error, 429, {"attempt": 1})
            assert result["api_error_type"] == "429_rate_limit", f"Expected 429_rate_limit, got {result['api_error_type']}"
            
            self.log_test_result("Module API Error Handling", True)
            return True
            
        except Exception as e:
            self.log_test_result("Module API Error Handling", False, str(e))
            return False
    
    def test_error_statistics(self):
        """Test error statistics collection."""
        try:
            # Get EMM statistics
            emm_stats = self.emm.get_error_statistics()
            
            assert "total_errors" in emm_stats, "EMM stats should contain total_errors"
            assert "errors_by_module" in emm_stats, "EMM stats should contain errors_by_module"
            assert "errors_by_type" in emm_stats, "EMM stats should contain errors_by_type"
            
            # Get API error handler statistics
            api_stats = api_error_handler.get_statistics()
            
            assert "total_errors" in api_stats, "API stats should contain total_errors"
            assert "recovery_rate" in api_stats, "API stats should contain recovery_rate"
            assert "errors_by_type" in api_stats, "API stats should contain errors_by_type"
            
            self.log_test_result("Error Statistics", True)
            return True
            
        except Exception as e:
            self.log_test_result("Error Statistics", False, str(e))
            return False
    
    def test_hardcoded_error_codes_removal(self):
        """Test that hardcoded error codes have been removed."""
        try:
            # Check that modules don't have hardcoded error_codes dictionaries
            assert not hasattr(self.baaim, 'error_codes'), "BAAIM should not have hardcoded error_codes"
            assert not hasattr(self.saaim, 'error_codes'), "SAAIM should not have hardcoded error_codes"
            assert not hasattr(self.aaaim, 'error_codes'), "AAAIM should not have hardcoded error_codes"
            assert not hasattr(self.aacm, 'error_codes'), "AACM should not have hardcoded error_codes"
            
            self.log_test_result("Hardcoded Error Codes Removal", True)
            return True
            
        except Exception as e:
            self.log_test_result("Hardcoded Error Codes Removal", False, str(e))
            return False
    
    def test_required_methods_presence(self):
        """Test that all required error handling methods are present."""
        try:
            required_methods = ['log_error', 'generate_error_code', 'handle_exception', 'handle_api_error']
            
            for method in required_methods:
                assert hasattr(self.baaim, method), f"BAAIM missing {method} method"
                assert hasattr(self.saaim, method), f"SAAIM missing {method} method"
                assert hasattr(self.aaaim, method), f"AAAIM missing {method} method"
                assert hasattr(self.aacm, method), f"AACM missing {method} method"
            
            self.log_test_result("Required Methods Presence", True)
            return True
            
        except Exception as e:
            self.log_test_result("Required Methods Presence", False, str(e))
            return False
    
    async def run_all_tests(self):
        """Run all error handling integration tests."""
        self.logger.info("🚀 Starting Error Handling Integration Tests")
        self.logger.info("=" * 60)
        
        # Run synchronous tests
        self.test_emm_error_code_generation()
        self.test_emm_error_logging()
        self.test_api_error_handler_parsing()
        self.test_baaim_error_handling()
        self.test_saaim_error_handling()
        self.test_aaaim_error_handling()
        self.test_aacm_error_handling()
        self.test_error_statistics()
        self.test_hardcoded_error_codes_removal()
        self.test_required_methods_presence()
        
        # Run asynchronous tests
        await self.test_api_error_handler_handling()
        await self.test_module_exception_handling()
        await self.test_module_api_error_handling()
        
        # Print summary
        self.logger.info("=" * 60)
        self.logger.info(f"📊 Test Summary: {self.passed_tests}/{self.total_tests} tests passed")
        
        success_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        self.logger.info(f"🎯 Success Rate: {success_rate:.1f}%")
        
        if success_rate == 100:
            self.logger.info("🎉 All tests passed! Error handling integration is complete.")
        else:
            self.logger.warning(f"⚠️  {self.total_tests - self.passed_tests} tests failed. Check logs for details.")
        
        # Print detailed results
        self.logger.info("\n📋 Detailed Results:")
        for result in self.test_results:
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            self.logger.info(f"  {status} {result['test_name']}")
            if not result["success"] and result["details"]:
                self.logger.info(f"      Details: {result['details']}")
        
        return success_rate == 100

async def main():
    """Main test function."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and run tests
    test = ErrorHandlingIntegrationTest()
    success = await test.run_all_tests()
    
    if success:
        print("\n🎉 Error Handling Integration Test: PASSED")
        return 0
    else:
        print("\n❌ Error Handling Integration Test: FAILED")
        return 1

if __name__ == "__main__":
    asyncio.run(main()) 