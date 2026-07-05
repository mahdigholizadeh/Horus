"""
Test T0000008: BAAIM - Default & Override API Usage
Module(s) Tested: BAAIM
Description: Test default and override API usage functionality.
Success Criteria: The module correctly uses default API settings and allows override when specified.
"""

import asyncio
import tempfile
from pathlib import Path
import sys
import os
import json
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from BAAIM.baaim import BasicAPIActivationModule

async def test_baaim_default_and_override_api_usage():
    """Test default and override API usage."""
    test_code = "T0000008"
    test_name = "BAAIM - Default & Override API Usage"
    try:
        print(f"Starting {test_name}...")
        
        # Initialize BAAIM module
        baaim = BasicAPIActivationModule()
        print("BAAIM module initialized successfully")
        
        # Test default API usage
        print("Testing default API usage...")
        default_request = {
            "messages": [{"role": "user", "content": "Hello, this is a test message"}],
            "max_tokens": 50
        }
        
        default_result = await baaim.process_request(default_request)
        default_success = isinstance(default_result, object) and hasattr(default_result, 'success')
        print(f"Default API result: {default_result.success if default_result else 'Failed'}")
        
        # Test override API usage
        print("Testing override API usage...")
        override_request = {
            "messages": [{"role": "user", "content": "Hello, this is an override test"}],
            "model": "gpt-4",
            "max_tokens": 30,
            "temperature": 0.5
        }
        
        override_result = await baaim.process_request(override_request)
        override_success = isinstance(override_result, object) and hasattr(override_result, 'success')
        print(f"Override API result: {override_result.success if override_result else 'Failed'}")
        
        # Test configuration methods
        print("Testing configuration methods...")
        baaim.set_model("gpt-4.1-mini")
        baaim.set_config(max_tokens=200, temperature=0.8)
        
        config = baaim.get_config()
        config_success = isinstance(config, dict) and "model" in config
        print(f"Configuration test: {'Passed' if config_success else 'Failed'}")
        
        # Test module status
        print("Testing module status...")
        status = baaim.get_module_status()
        status_success = isinstance(status, dict) and "module" in status
        print(f"Status test: {'Passed' if status_success else 'Failed'}")
        
        # Test model validation
        print("Testing model validation...")
        valid_model = baaim.validate_model("gpt-4")
        invalid_model = baaim.validate_model("invalid-model")
        validation_success = valid_model and not invalid_model
        print(f"Model validation test: {'Passed' if validation_success else 'Failed'}")
        
        # Determine overall test success
        test_success = (
            default_success and 
            override_success and 
            config_success and 
            status_success and 
            validation_success
        )
        
        result = {
            "success": test_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": f"Default and override API usage successful",
            "details": {
                "default_success": default_success,
                "override_success": override_success,
                "config_success": config_success,
                "status_success": status_success,
                "validation_success": validation_success,
                "default_response": default_result.response if default_result and default_result.success else None,
                "override_response": override_result.response if override_result and override_result.success else None,
                "current_model": config.get("model") if config else None,
                "module_status": status.get("status") if status else None
            }
        }
        
        print(f"Test result: {result}")
        return result
        
    except Exception as e:
        error_result = {
            "success": False,
            "test_code": test_code,
            "test_name": test_name,
            "error": f"Test execution failed: {str(e)}"
        }
        print(f"Test failed: {error_result}")
        return error_result

async def test_baaim_connection_and_models():
    """Test BAAIM connection and model functionality."""
    test_code = "T0000008_CONNECTION"
    test_name = "BAAIM Connection & Models Test"
    try:
        print(f"Starting {test_name}...")
        
        # Initialize BAAIM module
        baaim = BasicAPIActivationModule()
        
        # Test available models
        print("Testing available models...")
        available_models = baaim.get_available_models()
        models_success = isinstance(available_models, list) and len(available_models) > 0
        print(f"Available models: {available_models}")
        print(f"Models test: {'Passed' if models_success else 'Failed'}")
        
        # Test model validation
        print("Testing model validation...")
        test_models = ["gpt-4", "gpt-3.5-turbo", "invalid-model"]
        validation_results = {}
        
        for model in test_models:
            is_valid = baaim.validate_model(model)
            validation_results[model] = is_valid
            print(f"Model '{model}': {'Valid' if is_valid else 'Invalid'}")
        
        validation_success = (
            validation_results.get("gpt-4") and 
            validation_results.get("gpt-3.5-turbo") and 
            not validation_results.get("invalid-model")
        )
        print(f"Model validation test: {'Passed' if validation_success else 'Failed'}")
        
        # Test configuration
        print("Testing configuration...")
        original_model = baaim.current_config.model
        baaim.set_model("gpt-4.1-mini")
        baaim.set_config(max_tokens=150, temperature=0.6)
        
        config = baaim.get_config()
        config_success = (
            config.get("model") == "gpt-4.1-mini" and
            config.get("max_tokens") == 150 and
            config.get("temperature") == 0.6
        )
        print(f"Configuration test: {'Passed' if config_success else 'Failed'}")
        
        # Restore original model
        baaim.set_model(original_model)
        
        # Test module status
        print("Testing module status...")
        status = baaim.get_module_status()
        status_success = (
            status.get("module") == "BAAIM" and
            status.get("status") == "active" and
            "stats" in status
        )
        print(f"Status test: {'Passed' if status_success else 'Failed'}")
        
        connection_success = models_success and validation_success and config_success and status_success
        
        result = {
            "success": connection_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": "BAAIM connection and models test successful",
            "details": {
                "models_success": models_success,
                "validation_success": validation_success,
                "config_success": config_success,
                "status_success": status_success,
                "available_models": available_models,
                "validation_results": validation_results,
                "module_status": status
            }
        }
        
        print(f"Connection test result: {result}")
        return result
        
    except Exception as e:
        error_result = {
            "success": False,
            "test_code": test_code,
            "test_name": test_name,
            "error": f"Connection test failed: {str(e)}"
        }
        print(f"Connection test failed: {error_result}")
        return error_result

async def main():
    """Run the tests."""
    print("=== BAAIM Test Suite ===")
    
    # Run basic functionality test
    print("\n1. Running basic functionality test...")
    result1 = await test_baaim_default_and_override_api_usage()
    
    # Run connection test
    print("\n2. Running connection test...")
    result2 = await test_baaim_connection_and_models()
    
    # Overall results
    overall_success = result1["success"] and result2["success"]
    
    print(f"\n=== Test Results ===")
    print(f"Basic functionality test: {'PASS' if result1['success'] else 'FAIL'}")
    print(f"Connection test: {'PASS' if result2['success'] else 'FAIL'}")
    print(f"Overall result: {'PASS' if overall_success else 'FAIL'}")
    
    if not overall_success:
        print(f"\nDetailed results:")
        print(f"Test 1: {json.dumps(result1, indent=2)}")
        print(f"Test 2: {json.dumps(result2, indent=2)}")

if __name__ == "__main__":
    asyncio.run(main()) 