"""
Test T00000011: EMM (Error Management Module) Unit Test
Module(s) Tested: EMM
Description: To ensure the EMM provides centralized, consistent error handling and logging.
Success Criteria: EMM catches exceptions, errors are logged in standardized format, graceful error responses are generated.
"""

import asyncio
import json
import sys
import logging
import os
from pathlib import Path
from typing import Dict, Any
import importlib

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from EMM.emm import ErrorManagementModule

if "EMM.emm" in sys.modules:
    importlib.reload(sys.modules["EMM.emm"])

async def test_t00000011():
    test_code = "T00000011"
    test_name = "EMM - Error Management Module Unit Test"
    results = []
    
    # Clean up error log before running the test
    error_log_path = Path("logs/error_log.json")
    if error_log_path.exists():
        try:
            error_log_path.unlink()
        except Exception:
            pass
    
    emm = ErrorManagementModule()
    await emm.start()
    
    try:
        # Step 1: Simulate a JSONDecodeError in the JDPM
        try:
            # Simulate JSON decode error
            invalid_json = "{'invalid': json, 'missing': quotes}"
            error_result1 = await emm.handle_error(
                error_type="JSONDecodeError",
                error_message="Invalid JSON format",
                module="JDPM",
                function="process_json_data",
                context={"input_data": invalid_json}
            )
            
            results.append(error_result1.get("success", False))
            results.append("error_code" in error_result1)
            results.append(len(error_result1.get("error_code", "")) == 16)  # 16-character hex code
            results.append(error_result1.get("module") == "JDPM")
            
        except Exception as e:
            print(f"JSONDecodeError simulation failed: {e}")
            results.extend([False, False, False, False])
        
        # Step 2: Simulate a TimeoutError in the DAM
        try:
            error_result2 = await emm.handle_error(
                error_type="TimeoutError",
                error_message="Analysis timeout exceeded",
                module="DAM",
                function="analyze_data",
                context={"timeout_seconds": 30, "data_size": "large"}
            )
            
            results.append(error_result2.get("success", False))
            results.append("error_code" in error_result2)
            results.append(len(error_result2.get("error_code", "")) == 16)
            results.append(error_result2.get("module") == "DAM")
            
        except Exception as e:
            print(f"TimeoutError simulation failed: {e}")
            results.extend([False, False, False, False])
        
        # Test error code generation
        error_code1 = emm.generate_error_code("JDPM", "test_function")
        results.append(len(error_code1) == 16)
        results.append(error_code1.startswith("010104"))  # Server(01) + Macroservice(01) + Microservice(04)
        
        error_code2 = emm.generate_error_code("TVM", "validate_template")
        results.append(len(error_code2) == 16)
        results.append(error_code2.startswith("010104"))
        
        # Test error logging
        log_result = await emm.log_error_with_type(
            error_code="0101040100000001",
            error_type="TestError",
            error_message="Test error message",
            module="TMM",
            function="test_function",
            severity="INFO"
        )
        results.append(log_result.get("success", False))
        
        # Test error recovery strategies
        recovery_result = await emm.execute_recovery_strategy(
            error_code="0101040E001",  # Use a valid error code from recovery_strategies
            strategy="retry"
        )
        results.append(recovery_result.get("success", False))
        
        # Test error statistics
        stats = emm.get_error_statistics()
        results.append(isinstance(stats, dict))
        results.append("total_errors" in stats)
        results.append("errors_by_module" in stats)
        results.append("errors_by_type" in stats)
        
        # Test error code lookup
        lookup_result = emm.lookup_error_code("0101040100000001")
        results.append(lookup_result.get("found", False))
        
        # Test graceful error response generation
        response = await emm.generate_error_response(
            error_code="0101040100000001",
            user_friendly=True
        )
        results.append(isinstance(response, dict))
        results.append("error_code" in response)
        results.append("message" in response)
        results.append("timestamp" in response)
        
        # Test error code validation
        valid_code = "0101040100000001"
        invalid_code = "INVALID"
        
        validation1 = emm.validate_error_code(valid_code)
        validation2 = emm.validate_error_code(invalid_code)
        
        results.append(validation1.get("valid", False))
        results.append(not validation2.get("valid", True))
        
        success = all(results)
        
        return {
            "success": success,
            "test_code": test_code,
            "test_name": test_name,
            "message": "EMM unit test passed" if success else "EMM unit test failed",
            "details": {
                "json_decode_error_handled": results[0],
                "json_error_code_generated": results[1],
                "json_error_code_length_correct": results[2],
                "json_error_module_correct": results[3],
                "timeout_error_handled": results[4],
                "timeout_error_code_generated": results[5],
                "timeout_error_code_length_correct": results[6],
                "timeout_error_module_correct": results[7],
                "error_code1_generated": results[8],
                "error_code1_format_correct": results[9],
                "error_code2_generated": results[10],
                "error_code2_format_correct": results[11],
                "error_logging_successful": results[12],
                "recovery_strategy_executed": results[13],
                "error_statistics_generated": results[14],
                "error_statistics_has_total": results[15],
                "error_statistics_has_by_module": results[16],
                "error_statistics_has_by_type": results[17],
                "error_code_lookup_works": results[18],
                "error_response_generated": results[19],
                "error_response_has_code": results[20],
                "error_response_has_message": results[21],
                "error_response_has_timestamp": results[22],
                "valid_error_code_validated": results[23],
                "invalid_error_code_rejected": results[24],
                "results": results
            }
        }
        
    finally:
        await emm.stop()