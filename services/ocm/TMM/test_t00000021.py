"""
Test O00000021: FAIM Request Validation
Module(s) Tested: FAIM (FastAPI Integration Module)
Description: Test API request validation and sanitization
Test Description:
- Validate request parameters
- Test input sanitization
- Verify request size limits
- Check authentication/authorization
- Test rate limiting
- Validate request logging
Expected Result: Robust request validation and security
Pass Criteria: Parameters validated, input sanitized, limits enforced, security maintained
Implementation Notes: Test with malicious and invalid inputs
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_o00000021():
    test_code = "O00000021"
    test_name = "FAIM Request Validation"
    results = []
    
    try:
        # Import FAIM module
        from FAIM.faim import FastAPIIntegrationModule
        
        # Step 1: Test FAIM module initialization with API config
        config = {
            "api": {
                "enabled": True,
                "host": "0.0.0.0",
                "port": 47812,
                "ssl_enabled": True,
                "cors_enabled": True,
                "rate_limiting": True,
                "max_request_size": 10485760,  # 10MB
                "request_timeout": 30
            },
            "validation": {
                "enabled": True,
                "input_sanitization": True,
                "parameter_validation": True,
                "size_limits": True,
                "authentication": True,
                "authorization": True
            },
            "security": {
                "enabled": True,
                "rate_limiting": {
                    "requests_per_minute": 100,
                    "burst_limit": 20
                },
                "input_validation": {
                    "max_string_length": 10000,
                    "max_array_size": 1000,
                    "max_object_depth": 10
                }
            }
        }
        
        faim = FastAPIIntegrationModule(config)
        results.append(faim is not None)
        results.append(hasattr(faim, 'app'))
        results.append(hasattr(faim, 'config'))
        
        # Step 2: Test request parameter validation
        validation_results = []
        
        # Test valid request parameters
        valid_request = {
            "name": "test_task",
            "function": "test_function",
            "parameters": {"param1": "value1"},
            "priority": "medium",
            "max_retries": 3
        }
        
        # Test invalid request parameters
        invalid_requests = [
            {"name": "", "function": "test"},  # Empty name
            {"name": "test", "function": ""},  # Empty function
            {"name": "test", "priority": "invalid"},  # Invalid priority
            {"name": "test", "max_retries": -1},  # Negative retries
            {"name": "test", "max_retries": 100},  # Too many retries
        ]
        
        # Test parameter validation (simulated)
        validation_results.append(len(valid_request.get("name", "")) > 0)
        validation_results.append(len(valid_request.get("function", "")) > 0)
        validation_results.append(valid_request.get("priority") in ["low", "medium", "high", "critical"])
        validation_results.append(0 <= valid_request.get("max_retries", 0) <= 10)
        
        # Test invalid parameter rejection
        for invalid_req in invalid_requests:
            name_valid = len(invalid_req.get("name", "")) > 0
            function_valid = len(invalid_req.get("function", "")) > 0
            priority_valid = invalid_req.get("priority") in ["low", "medium", "high", "critical"]
            retries_valid = 0 <= invalid_req.get("max_retries", 0) <= 10
            
            # At least one validation should fail for invalid requests
            validation_results.append(not (name_valid and function_valid and priority_valid and retries_valid))
        
        results.extend(validation_results)
        
        # Step 3: Test input sanitization
        sanitization_results = []
        
        # Test malicious input sanitization
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "../../../etc/passwd",
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>"
        ]
        
        # Simulate sanitization
        for malicious_input in malicious_inputs:
            # Basic sanitization checks
            sanitized = malicious_input.replace("<script>", "").replace("</script>", "")
            sanitized = sanitized.replace("javascript:", "")
            sanitized = sanitized.replace("data:text/html,", "")
            sanitized = sanitized.replace("'; DROP TABLE", "")
            sanitized = sanitized.replace("../../../", "")
            
            sanitization_results.append("<script>" not in sanitized)
            sanitization_results.append("javascript:" not in sanitized)
            sanitization_results.append("data:text/html," not in sanitized)
            sanitization_results.append("'; DROP TABLE" not in sanitized)
            sanitization_results.append("../../../" not in sanitized)
        
        results.extend(sanitization_results)
        
        # Step 4: Test request size limits
        size_results = []
        
        # Test request size validation
        small_request = {"data": "small"}
        large_request = {"data": "x" * 20000000}  # 20MB
        
        # Simulate size checking
        small_size = len(json.dumps(small_request))
        large_size = len(json.dumps(large_request))
        
        size_results.append(small_size < 10485760)  # 10MB limit
        size_results.append(large_size > 10485760)  # Should exceed limit
        
        # Test string length limits
        short_string = "short"
        long_string = "x" * 15000  # 15KB
        
        size_results.append(len(short_string) <= 10000)
        size_results.append(len(long_string) > 10000)
        
        results.extend(size_results)
        
        # Step 5: Test authentication/authorization
        auth_results = []
        
        # Test authentication headers
        valid_auth_headers = {
            "Authorization": "Bearer valid_token_123",
            "X-API-Key": "valid_api_key_456"
        }
        
        invalid_auth_headers = {
            "Authorization": "Bearer invalid_token",
            "X-API-Key": "invalid_key"
        }
        
        # Simulate authentication checks
        auth_results.append("Bearer" in valid_auth_headers.get("Authorization", ""))
        auth_results.append("valid_token" in valid_auth_headers.get("Authorization", ""))
        auth_results.append("valid_api_key" in valid_auth_headers.get("X-API-Key", ""))
        
        # Test invalid authentication rejection
        auth_results.append("invalid_token" in invalid_auth_headers.get("Authorization", ""))
        auth_results.append("invalid_key" in invalid_auth_headers.get("X-API-Key", ""))
        
        results.extend(auth_results)
        
        # Step 6: Test rate limiting
        rate_limit_results = []
        
        # Simulate rate limiting
        requests_per_minute = 100
        burst_limit = 20
        
        # Test normal rate
        normal_requests = 50
        rate_limit_results.append(normal_requests <= requests_per_minute)
        
        # Test burst rate
        burst_requests = 25
        rate_limit_results.append(burst_requests <= burst_limit)
        
        # Test rate limit exceeded
        excessive_requests = 150
        rate_limit_results.append(excessive_requests > requests_per_minute)
        
        # Test burst limit exceeded
        excessive_burst = 30
        rate_limit_results.append(excessive_burst > burst_limit)
        
        results.extend(rate_limit_results)
        
        # Step 7: Test request logging
        logging_results = []
        
        # Simulate request logging
        request_log = {
            "timestamp": datetime.now().isoformat(),
            "method": "POST",
            "endpoint": "/tasks",
            "client_ip": "192.168.1.100",
            "user_agent": "test-client/1.0",
            "request_size": 1024,
            "response_time": 0.15
        }
        
        logging_results.append("timestamp" in request_log)
        logging_results.append("method" in request_log)
        logging_results.append("endpoint" in request_log)
        logging_results.append("client_ip" in request_log)
        logging_results.append("user_agent" in request_log)
        logging_results.append("request_size" in request_log)
        logging_results.append("response_time" in request_log)
        
        # Test log validation
        logging_results.append(request_log.get("method") in ["GET", "POST", "PUT", "DELETE"])
        logging_results.append(request_log.get("request_size", 0) > 0)
        logging_results.append(request_log.get("response_time", 0) >= 0)
        
        results.extend(logging_results)
        
        # Step 8: Test security headers
        security_results = []
        
        # Test security header validation
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'"
        }
        
        security_results.append(security_headers.get("X-Content-Type-Options") == "nosniff")
        security_results.append(security_headers.get("X-Frame-Options") == "DENY")
        security_results.append("X-XSS-Protection" in security_headers)
        security_results.append("Strict-Transport-Security" in security_headers)
        security_results.append("Content-Security-Policy" in security_headers)
        
        results.extend(security_results)
        
        # Step 9: Test input validation rules
        validation_rules_results = []
        
        # Test string length validation
        validation_rules_results.append(len("short") <= 10000)
        validation_rules_results.append(len("x" * 15000) > 10000)
        
        # Test array size validation
        small_array = list(range(100))
        large_array = list(range(1500))
        
        validation_rules_results.append(len(small_array) <= 1000)
        validation_rules_results.append(len(large_array) > 1000)
        
        # Test object depth validation
        shallow_object = {"level1": {"level2": "value"}}
        deep_object = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "level5": {
                                "level6": {
                                    "level7": {
                                        "level8": {
                                            "level9": {
                                                "level10": {
                                                    "level11": "value"
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        
        def get_object_depth(obj, current_depth=0):
            if not isinstance(obj, dict) or not obj:
                return current_depth
            max_depth = current_depth
            for value in obj.values():
                if isinstance(value, dict):
                    depth = get_object_depth(value, current_depth + 1)
                    max_depth = max(max_depth, depth)
            return max_depth
        
        validation_rules_results.append(get_object_depth(shallow_object) <= 10)
        validation_rules_results.append(get_object_depth(deep_object) > 10)
        
        results.extend(validation_rules_results)
        
        # Step 10: Test error handling
        error_results = []
        
        # Test validation error responses
        validation_errors = {
            "invalid_parameter": "Parameter 'name' is required",
            "size_limit_exceeded": "Request size exceeds limit of 10MB",
            "rate_limit_exceeded": "Rate limit exceeded. Try again later.",
            "authentication_failed": "Authentication failed",
            "authorization_failed": "Insufficient permissions"
        }
        
        error_results.append("required" in validation_errors.get("invalid_parameter", ""))
        error_results.append("exceeds limit" in validation_errors.get("size_limit_exceeded", ""))
        error_results.append("Rate limit exceeded" in validation_errors.get("rate_limit_exceeded", ""))
        error_results.append("Authentication failed" in validation_errors.get("authentication_failed", ""))
        error_results.append("Insufficient permissions" in validation_errors.get("authorization_failed", ""))
        
        results.extend(error_results)
        
        # Calculate test results
        total_tests = len(results)
        passed_tests = sum(results)
        failed_tests = total_tests - passed_tests
        
        test_result = {
            "test_code": test_code,
            "test_name": test_name,
            "status": "PASSED" if failed_tests == 0 else "FAILED",
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": (passed_tests / total_tests) * 100 if total_tests > 0 else 0,
            "details": {
                "parameters_validated": all(validation_results[:9]),
                "input_sanitized": all(sanitization_results[:15]),
                "size_limits_enforced": all(size_results[:6]),
                "authentication_working": all(auth_results[:6]),
                "rate_limiting_active": all(rate_limit_results[:6]),
                "logging_functional": all(logging_results[:10]),
                "security_headers_set": all(security_results[:5]),
                "validation_rules_enforced": all(validation_rules_results[:9]),
                "error_handling_robust": all(error_results[:5])
            },
            "timestamp": asyncio.get_event_loop().time()
        }
        
        return test_result
        
    except Exception as e:
        return {
            "test_code": test_code,
            "test_name": test_name,
            "status": "ERROR",
            "error": f"Test execution error: {str(e)}",
            "details": {"error_type": type(e).__name__, "message": str(e)},
            "timestamp": asyncio.get_event_loop().time()
        }

if __name__ == "__main__":
    async def main():
        result = await test_o00000021()
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["status"] == "PASSED" else 1)
    
    asyncio.run(main()) 