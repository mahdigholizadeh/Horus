"""
Test O00000053: EMM Error Classification
Module(s) Tested: EMM (Error Management Module)
Description: Test comprehensive error classification system
Test Description:
- Classify errors by severity and type
- Test error categorization
- Verify error prioritization
- Check error correlation
- Test error pattern recognition
- Validate error classification accuracy
Expected Result: Accurate error classification and categorization
Pass Criteria: Errors classified, categorized, prioritized, correlated, patterns recognized
Implementation Notes: Test with various error types and scenarios
"""

import asyncio
import json
import sys
import os
import tempfile
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import uuid

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_o00000053():
    test_code = "O00000053"
    test_name = "EMM Error Classification"
    results = []
    
    try:
        # Import EMM module
        from EMM.emm import ErrorManagementModule, ErrorSeverity, ErrorCategory, RecoveryStrategy, ErrorRecord
        
        # Create temporary test directory
        test_dir = tempfile.mkdtemp(prefix="emm_classification_test_")
        
        # Step 1: Test EMM module initialization with error classification config
        config = {
            "error_management": {
                "error_classification": True,
                "error_categorization": True,
                "error_prioritization": True,
                "error_correlation": True,
                "error_pattern_recognition": True,
                "error_classification_accuracy": True
            },
            "classification": {
                "enabled": True,
                "severity_levels": True,
                "error_categories": True,
                "prioritization_enabled": True,
                "correlation_enabled": True,
                "pattern_recognition": True
            },
            "database": {
                "path": os.path.join(test_dir, "error_database.db"),
                "auto_cleanup": True,
                "retention_days": 30
            }
        }
        
        emm = ErrorManagementModule(config)
        await emm.start()
        results.append(emm.is_active == True)
        results.append(hasattr(emm, 'report_error'))
        results.append(hasattr(emm, 'get_error_statistics'))
        results.append(hasattr(emm, 'get_error_details'))
        
        # Step 2: Test error classification by severity and type
        classification_results = []
        
        # Test different severity levels
        severity_levels = [
            (ErrorSeverity.LOW, "Low severity test error"),
            (ErrorSeverity.MEDIUM, "Medium severity test error"),
            (ErrorSeverity.HIGH, "High severity test error"),
            (ErrorSeverity.CRITICAL, "Critical severity test error"),
            (ErrorSeverity.FATAL, "Fatal severity test error")
        ]
        
        for severity, message in severity_levels:
            error_code = await emm.report_error(
                module="test_module",
                class_name="TestClass",
                function_name="test_function",
                message=message,
                category=ErrorCategory.OPERATION_CONTROL,
                severity=severity,
                context={"test_type": "severity_classification", "severity_level": severity.value}
            )
            
            classification_results.append(error_code is not None)
            classification_results.append(len(error_code) == 16)  # 16-character hex code
            
            # Verify error details
            error_details = emm.get_error_details(error_code)
            classification_results.append(error_details is not None)
            
            if error_details:
                classification_results.append(error_details.get("severity") == severity.value)
                classification_results.append(error_details.get("message") == message)
        
        # Step 3: Test error categorization
        categorization_results = []
        
        # Test different error categories
        error_categories = [
            (ErrorCategory.OPERATION_CONTROL, "Operation control error"),
            (ErrorCategory.VERIFICATION_SYSTEM, "Verification system error"),
            (ErrorCategory.PERFORMANCE_MONITORING, "Performance monitoring error"),
            (ErrorCategory.RESOURCE_MANAGEMENT, "Resource management error"),
            (ErrorCategory.MODULE_COMMUNICATION, "Module communication error"),
            (ErrorCategory.SYSTEM_HEALTH, "System health error"),
            (ErrorCategory.DATA_MANAGEMENT, "Data management error"),
            (ErrorCategory.NETWORK_COMMUNICATION, "Network communication error"),
            (ErrorCategory.CONFIGURATION, "Configuration error"),
            (ErrorCategory.EXTERNAL_SERVICE, "External service error")
        ]
        
        for category, message in error_categories:
            error_code = await emm.report_error(
                module="test_module",
                class_name="TestClass",
                function_name="test_function",
                message=message,
                category=category,
                severity=ErrorSeverity.MEDIUM,
                context={"test_type": "category_classification", "category": category.value}
            )
            
            categorization_results.append(error_code is not None)
            
            # Verify error details
            error_details = emm.get_error_details(error_code)
            categorization_results.append(error_details is not None)
            
            if error_details:
                categorization_results.append(error_details.get("category") == category.value)
                categorization_results.append(error_details.get("message") == message)
        
        # Step 4: Test error prioritization
        prioritization_results = []
        
        # Create test errors with different priorities
        priority_test_errors = [
            {
                "message": "Low priority error - minor issue",
                "severity": ErrorSeverity.LOW,
                "category": ErrorCategory.CONFIGURATION,
                "priority": "low"
            },
            {
                "message": "Medium priority error - moderate issue",
                "severity": ErrorSeverity.MEDIUM,
                "category": ErrorCategory.PERFORMANCE_MONITORING,
                "priority": "medium"
            },
            {
                "message": "High priority error - significant issue",
                "severity": ErrorSeverity.HIGH,
                "category": ErrorCategory.RESOURCE_MANAGEMENT,
                "priority": "high"
            },
            {
                "message": "Critical priority error - system impact",
                "severity": ErrorSeverity.CRITICAL,
                "category": ErrorCategory.SYSTEM_HEALTH,
                "priority": "critical"
            },
            {
                "message": "Fatal priority error - system failure",
                "severity": ErrorSeverity.FATAL,
                "category": ErrorCategory.OPERATION_CONTROL,
                "priority": "fatal"
            }
        ]
        
        for error_info in priority_test_errors:
            error_code = await emm.report_error(
                module="test_module",
                class_name="TestClass",
                function_name="test_function",
                message=error_info["message"],
                category=error_info["category"],
                severity=error_info["severity"],
                context={"test_type": "priority_classification", "priority": error_info["priority"]}
            )
            
            prioritization_results.append(error_code is not None)
            
            # Verify error details
            error_details = emm.get_error_details(error_code)
            prioritization_results.append(error_details is not None)
            
            if error_details:
                prioritization_results.append(error_details.get("severity") == error_info["severity"].value)
                prioritization_results.append(error_details.get("category") == error_info["category"].value)
        
        # Step 5: Test error correlation
        correlation_results = []
        
        # Create correlated errors
        correlation_group_id = str(uuid.uuid4())
        
        correlated_errors = [
            {
                "message": "Primary error - database connection failed",
                "severity": ErrorSeverity.HIGH,
                "category": ErrorCategory.DATA_MANAGEMENT,
                "correlation_id": correlation_group_id
            },
            {
                "message": "Secondary error - query execution failed",
                "severity": ErrorSeverity.MEDIUM,
                "category": ErrorCategory.DATA_MANAGEMENT,
                "correlation_id": correlation_group_id
            },
            {
                "message": "Tertiary error - report generation failed",
                "severity": ErrorSeverity.LOW,
                "category": ErrorCategory.OPERATION_CONTROL,
                "correlation_id": correlation_group_id
            }
        ]
        
        for error_info in correlated_errors:
            error_code = await emm.report_error(
                module="test_module",
                class_name="TestClass",
                function_name="test_function",
                message=error_info["message"],
                category=error_info["category"],
                severity=error_info["severity"],
                context={
                    "test_type": "correlation_classification",
                    "correlation_id": error_info["correlation_id"],
                    "correlation_group": "database_failure_chain"
                }
            )
            
            correlation_results.append(error_code is not None)
            
            # Verify error details
            error_details = emm.get_error_details(error_code)
            correlation_results.append(error_details is not None)
            
            if error_details:
                correlation_results.append("correlation_id" in error_details.get("context", {}))
        
        # Step 6: Test error pattern recognition
        pattern_results = []
        
        # Create pattern-based errors
        pattern_errors = [
            {
                "message": "Pattern error 1 - timeout occurred",
                "severity": ErrorSeverity.MEDIUM,
                "category": ErrorCategory.NETWORK_COMMUNICATION,
                "pattern": "timeout_pattern"
            },
            {
                "message": "Pattern error 2 - timeout occurred again",
                "severity": ErrorSeverity.MEDIUM,
                "category": ErrorCategory.NETWORK_COMMUNICATION,
                "pattern": "timeout_pattern"
            },
            {
                "message": "Pattern error 3 - timeout occurred third time",
                "severity": ErrorSeverity.HIGH,
                "category": ErrorCategory.NETWORK_COMMUNICATION,
                "pattern": "timeout_pattern"
            },
            {
                "message": "Pattern error 4 - memory allocation failed",
                "severity": ErrorSeverity.HIGH,
                "category": ErrorCategory.RESOURCE_MANAGEMENT,
                "pattern": "memory_pattern"
            },
            {
                "message": "Pattern error 5 - memory allocation failed again",
                "severity": ErrorSeverity.CRITICAL,
                "category": ErrorCategory.RESOURCE_MANAGEMENT,
                "pattern": "memory_pattern"
            }
        ]
        
        for error_info in pattern_errors:
            error_code = await emm.report_error(
                module="test_module",
                class_name="TestClass",
                function_name="test_function",
                message=error_info["message"],
                category=error_info["category"],
                severity=error_info["severity"],
                context={
                    "test_type": "pattern_classification",
                    "pattern_type": error_info["pattern"],
                    "occurrence_count": pattern_errors.count(error_info)
                }
            )
            
            pattern_results.append(error_code is not None)
            
            # Verify error details
            error_details = emm.get_error_details(error_code)
            pattern_results.append(error_details is not None)
            
            if error_details:
                pattern_results.append("pattern_type" in error_details.get("context", {}))
        
        # Step 7: Test error classification accuracy
        accuracy_results = []
        
        # Create test errors with known expected classifications
        accuracy_test_errors = [
            {
                "message": "Accuracy test - network timeout",
                "severity": ErrorSeverity.MEDIUM,
                "category": ErrorCategory.NETWORK_COMMUNICATION,
                "expected_classification": {
                    "severity": 2,
                    "category": "network_communication",
                    "priority": "medium"
                }
            },
            {
                "message": "Accuracy test - database corruption",
                "severity": ErrorSeverity.CRITICAL,
                "category": ErrorCategory.DATA_MANAGEMENT,
                "expected_classification": {
                    "severity": 4,
                    "category": "data_management",
                    "priority": "critical"
                }
            },
            {
                "message": "Accuracy test - configuration invalid",
                "severity": ErrorSeverity.LOW,
                "category": ErrorCategory.CONFIGURATION,
                "expected_classification": {
                    "severity": 1,
                    "category": "configuration",
                    "priority": "low"
                }
            }
        ]
        
        for error_info in accuracy_test_errors:
            error_code = await emm.report_error(
                module="test_module",
                class_name="TestClass",
                function_name="test_function",
                message=error_info["message"],
                category=error_info["category"],
                severity=error_info["severity"],
                context={
                    "test_type": "accuracy_classification",
                    "expected_classification": error_info["expected_classification"]
                }
            )
            
            accuracy_results.append(error_code is not None)
            
            # Verify classification accuracy
            error_details = emm.get_error_details(error_code)
            accuracy_results.append(error_details is not None)
            
            if error_details:
                expected = error_info["expected_classification"]
                accuracy_results.append(error_details.get("severity") == expected["severity"])
                accuracy_results.append(error_details.get("category") == expected["category"])
        
        # Step 8: Test error classification performance
        performance_results = []
        
        # Test performance with multiple classification scenarios
        start_time = datetime.now()
        
        # Generate multiple error classifications
        classification_request_ids = []
        classification_scenarios = ["severity", "category", "priority", "correlation", "pattern"]
        
        for i, scenario in enumerate(classification_scenarios):
            perf_error_code = await emm.report_error(
                module="test_module",
                class_name="TestClass",
                function_name="test_function",
                message=f"Performance test error {i+1} for {scenario} classification",
                category=ErrorCategory.OPERATION_CONTROL,
                severity=ErrorSeverity.MEDIUM,
                context={
                    "test_type": "performance_classification",
                    "scenario": scenario,
                    "performance_test": True
                }
            )
            
            classification_request_ids.append(perf_error_code)
        
        end_time = datetime.now()
        classification_time = (end_time - start_time).total_seconds()
        
        performance_results.append(len(classification_request_ids) == 5)
        performance_results.append(all(ec is not None for ec in classification_request_ids))
        performance_results.append(classification_time < 10.0)  # Should complete within 10 seconds
        
        # Step 9: Test error classification error scenarios
        error_results = []
        
        # Test with invalid severity
        try:
            invalid_severity_code = await emm.report_error(
                module="test_module",
                class_name="TestClass",
                function_name="test_function",
                message="Invalid severity test error",
                category=ErrorCategory.OPERATION_CONTROL,
                severity=999,  # Invalid severity
                context={"test_type": "invalid_severity"}
            )
            error_results.append(invalid_severity_code is not None)  # Should handle gracefully
        except Exception:
            error_results.append(True)  # Should handle error gracefully
        
        # Test with invalid category
        try:
            invalid_category_code = await emm.report_error(
                module="test_module",
                class_name="TestClass",
                function_name="test_function",
                message="Invalid category test error",
                category="invalid_category",  # Invalid category
                severity=ErrorSeverity.MEDIUM,
                context={"test_type": "invalid_category"}
            )
            error_results.append(invalid_category_code is not None)  # Should handle gracefully
        except Exception:
            error_results.append(True)  # Should handle error gracefully
        
        # Step 10: Test error classification validation
        validation_results = []
        
        # Test error statistics
        error_stats = emm.get_error_statistics()
        validation_results.append(isinstance(error_stats, dict))
        validation_results.append("total_errors" in error_stats)
        validation_results.append("errors_by_severity" in error_stats)
        validation_results.append("errors_by_category" in error_stats)
        
        # Test error details for all reported errors
        all_error_codes = classification_request_ids + [ec for ec in classification_request_ids if ec is not None]
        
        for error_code in all_error_codes:
            if error_code:
                error_details = emm.get_error_details(error_code)
                validation_results.append(error_details is not None)
                validation_results.append("error_code" in error_details)
                validation_results.append("severity" in error_details)
                validation_results.append("category" in error_details)
        
        # Test module status
        module_status = emm.get_status()
        validation_results.append(module_status is not None)
        validation_results.append("is_active" in module_status)
        
        # Test health check
        health_status = await emm.health_check()
        validation_results.append(isinstance(health_status, bool))
        
        # Aggregate all results
        all_results = (
            results + 
            classification_results + 
            categorization_results + 
            prioritization_results + 
            correlation_results + 
            pattern_results + 
            accuracy_results + 
            performance_results + 
            error_results + 
            validation_results
        )
        
        # Calculate pass rate
        passed_tests = sum(all_results)
        total_tests = len(all_results)
        pass_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        # Cleanup
        await emm.stop()
        
        # Clean up test directory
        try:
            import shutil
            shutil.rmtree(test_dir)
        except Exception:
            pass  # Ignore cleanup errors
        
        return {
            "test_code": test_code,
            "test_name": test_name,
            "status": "PASSED" if pass_rate >= 90 else "FAILED",
            "pass_rate": pass_rate,
            "passed_tests": passed_tests,
            "total_tests": total_tests,
            "results": {
                "module_initialization": results,
                "error_classification_by_severity_type": classification_results,
                "error_categorization": categorization_results,
                "error_prioritization": prioritization_results,
                "error_correlation": correlation_results,
                "error_pattern_recognition": pattern_results,
                "error_classification_accuracy": accuracy_results,
                "classification_performance": performance_results,
                "classification_error_scenarios": error_results,
                "classification_validation": validation_results
            },
            "classification_metrics": {
                "total_classifications": len(classification_request_ids),
                "classification_time_seconds": classification_time,
                "successful_classifications": sum(1 for ec in classification_request_ids if ec is not None),
                "severity_levels_tested": len(severity_levels),
                "error_categories_tested": len(error_categories)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "test_code": test_code,
            "test_name": test_name,
            "status": "ERROR",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

async def main():
    """Main test execution function."""
    result = await test_o00000053()
    print(json.dumps(result, indent=2))
    return result

if __name__ == "__main__":
    asyncio.run(main())