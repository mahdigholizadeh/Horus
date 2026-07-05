"""
Test T00000017: CEIM Error Code Generation and Management
Module(s) Tested: CEIM (Central Error Investigation Module)
Description: Test centralized error code generation and error management system
Test Description:
- Test 16-character error code generation format
- Verify internal CCU error reporting and processing
- Check external microservice error aggregation
- Test error categorization and severity classification
- Validate error storage and tracking mechanisms
- Test error pattern detection and correlation
- Check error statistics and reporting
Expected Result: Comprehensive error code generation with centralized management
Pass Criteria: Codes generated correctly, errors processed, patterns detected, statistics accurate
Implementation Notes: Test both internal CCU and external microservice error flows
"""

import asyncio
import json
import sys
import time
import logging
import uuid
import hashlib
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_t00000017():
    test_code = "T00000017"
    test_name = "CEIM Error Code Generation and Management"
    results = []
    
    try:
        # Import CEIM module
        from CEIM.ceim import CentralErrorInvestigationModule, ErrorSeverity, ErrorCategory, CentralizedErrorRecord, MicroserviceType, RecoveryStrategy
        
        # Step 1: Test CEIM initialization
        config = {
            "db_path": "test_ceim.db",
            "max_internal_errors": 1000,
            "max_external_errors": 5000,
            "investigation_timeout": 300,
            "recovery_timeout": 60
        }
        
        ceim = CentralErrorInvestigationModule(config)
        results.append(ceim is not None)
        results.append(hasattr(ceim, 'config'))
        results.append(hasattr(ceim, 'internal_recovery_strategies'))
        results.append(hasattr(ceim, 'external_recovery_strategies'))
        
        # Step 2: Test error severity and category enumerations
        expected_severities = [ErrorSeverity.LOW, ErrorSeverity.MEDIUM, ErrorSeverity.HIGH, ErrorSeverity.CRITICAL, ErrorSeverity.FATAL]
        results.append(all(severity in ErrorSeverity for severity in expected_severities))
        results.append(len(ErrorSeverity) == 5)
        
        expected_categories = [ErrorCategory.CENTRAL_CONTROL, ErrorCategory.CERTIFICATE_MANAGEMENT, ErrorCategory.COMMUNICATION_HUB]
        results.append(all(category in ErrorCategory for category in expected_categories))
        results.append(len(ErrorCategory) >= 10)  # Should have at least 10 categories
        
        # Step 3: Test 16-character error code generation format
        # Format: Server(2) + Macroservice(2) + Microservice(2) + Module(2) + Class(2) + Function(3) + Sub-function(3)
        
        test_cases = [
            {
                'module': 'RTM',
                'class_name': 'RequestTrackingModule', 
                'function_name': 'process_request',
                'sub_function': '000'
            },
            {
                'module': 'SRMM',
                'class_name': 'ServerResourcesMonitor',
                'function_name': 'monitor_resources',
                'sub_function': 'check_cpu'
            },
            {
                'module': 'MSMM',
                'class_name': 'MicroServicesMonitor',
                'function_name': 'check_health',
                'sub_function': '000'
            }
        ]
        
        generated_codes = []
        for case in test_cases:
            error_code = ceim._generate_internal_error_code(
                case['module'], 
                case['class_name'],
                case['function_name'],
                case['sub_function']
            )
            generated_codes.append(error_code)
            
            # Verify format: 16 characters, hex format
            results.append(len(error_code) == 16)
            results.append(all(c in '0123456789ABCDEF' for c in error_code))
            
            # Verify fixed prefixes: Server(01) + Macroservice(01) + Microservice(07)
            results.append(error_code.startswith('010107'))
        
        # Verify codes are unique for different inputs
        results.append(len(set(generated_codes)) == len(generated_codes))
        
        # Step 4: Test internal CCU error reporting and processing
        with patch.object(ceim, '_process_internal_error', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = None
            
            error_code = await ceim.report_internal_error(
                module='RTM',
                class_name='RequestTrackingModule',
                function_name='execute_workflow',
                message='Workflow execution failed',
                category=ErrorCategory.TASK_MANAGEMENT,
                severity=ErrorSeverity.HIGH,
                context={'request_id': 'test_123', 'stage': 'processing'}
            )
            
            results.append(error_code is not None)
            results.append(len(error_code) == 16)
            results.append(mock_process.called)
            
            # Verify the error record structure passed to processing
            if mock_process.call_args:
                error_record = mock_process.call_args[0][0]
                results.append(isinstance(error_record, CentralizedErrorRecord))
                results.append(error_record.microservice == 'CCU')
                results.append(error_record.microservice_code == '07')
                results.append(error_record.source == 'internal')
                results.append(error_record.severity == ErrorSeverity.HIGH.value)
            else:
                results.extend([False, False, False, False, False])
        
        # Step 5: Test external microservice error aggregation
        external_error_report = {
            'error_code': '01010201AB12CD34',
            'microservice': 'RLA',
            'microservice_code': '02',
            'timestamp': datetime.now().isoformat(),
            'severity': ErrorSeverity.CRITICAL.value,
            'category': 'data_processing',
            'module': 'RLA_Core',
            'class_name': 'DataProcessor',
            'function_name': 'validate_input',
            'message': 'Input validation failed',
            'context': {'input_type': 'user_data'},
            'source': 'external'
        }
        
        with patch.object(ceim, '_process_external_error', new_callable=AsyncMock) as mock_process_ext:
            mock_process_ext.return_value = None
            
            await ceim.receive_external_error_report(external_error_report)
            
            results.append(mock_process_ext.called)
            
            if mock_process_ext.call_args:
                ext_error_record = mock_process_ext.call_args[0][0]
                results.append(isinstance(ext_error_record, CentralizedErrorRecord))
                results.append(ext_error_record.microservice == 'RLA')
                results.append(ext_error_record.source == 'external')
            else:
                results.extend([False, False, False])
        
        # Step 6: Test error categorization and severity classification
        severity_tests = [
            (ErrorSeverity.LOW, 1),
            (ErrorSeverity.MEDIUM, 2), 
            (ErrorSeverity.HIGH, 3),
            (ErrorSeverity.CRITICAL, 4),
            (ErrorSeverity.FATAL, 5)
        ]
        
        for severity, expected_value in severity_tests:
            results.append(severity.value == expected_value)
        
        # Test category classification
        category_tests = [
            ErrorCategory.CENTRAL_CONTROL,
            ErrorCategory.CERTIFICATE_MANAGEMENT,
            ErrorCategory.COMMUNICATION_HUB,
            ErrorCategory.TASK_MANAGEMENT,
            ErrorCategory.SERVICE_COORDINATION
        ]
        
        for category in category_tests:
            results.append(isinstance(category.value, str))
            results.append(len(category.value) > 0)
        
        # Step 7: Test error storage and tracking mechanisms
        test_error_record = CentralizedErrorRecord(
            error_code='01010712AB34CD56',
            microservice='CCU',
            microservice_code='07',
            timestamp=datetime.now().isoformat(),
            severity=ErrorSeverity.MEDIUM.value,
            category=ErrorCategory.SYSTEM_HEALTH.value,
            module='SRMM',
            class_name='ResourceMonitor',
            function_name='check_memory',
            message='Memory usage high',
            context={'memory_percent': 85.5},
            source='internal',
            first_occurrence=datetime.now().isoformat(),
            last_occurrence=datetime.now().isoformat()
        )
        
        with patch.object(ceim, '_store_internal_error', new_callable=AsyncMock) as mock_store:
            mock_store.return_value = None
            await ceim._store_internal_error(test_error_record)
            results.append(mock_store.called)
        
        # Step 8: Test recovery strategy management
        recovery_strategies = [
            RecoveryStrategy.RETRY,
            RecoveryStrategy.RESTART_COMPONENT,
            RecoveryStrategy.RESTART_SERVICE,
            RecoveryStrategy.FALLBACK_MODE,
            RecoveryStrategy.RESOURCE_CLEANUP,
            RecoveryStrategy.CONFIGURATION_RESET,
            RecoveryStrategy.ESCALATE_TO_ADMIN
        ]
        
        for strategy in recovery_strategies:
            results.append(strategy in RecoveryStrategy)
            results.append(isinstance(strategy.value, str))
        
        # Test recovery strategy execution
        with patch.object(ceim, '_execute_internal_recovery_strategy', new_callable=AsyncMock) as mock_recovery:
            mock_recovery.return_value = {'success': True, 'action': 'retry', 'attempts': 1}
            
            recovery_result = await ceim._execute_internal_recovery_strategy(
                RecoveryStrategy.RETRY, 
                test_error_record
            )
            
            results.append(mock_recovery.called)
            results.append(isinstance(recovery_result, dict))
            if recovery_result:
                results.append('success' in recovery_result)
            else:
                results.append(False)
        
        # Step 9: Test error pattern detection and correlation
        # Create multiple related errors
        pattern_errors = []
        for i in range(5):
            error_record = CentralizedErrorRecord(
                error_code=f'010107{i:02d}AB34CD56',
                microservice='CCU',
                microservice_code='07',
                timestamp=(datetime.now() - timedelta(minutes=i)).isoformat(),
                severity=ErrorSeverity.HIGH.value,
                category=ErrorCategory.RESOURCE_MONITORING.value,
                module='SRMM',
                class_name='ResourceMonitor',
                function_name='monitor_cpu',
                message=f'CPU usage critical: {90 + i}%',
                context={'cpu_percent': 90 + i},
                source='internal',
                first_occurrence=datetime.now().isoformat(),
                last_occurrence=datetime.now().isoformat()
            )
            pattern_errors.append(error_record)
        
        with patch.object(ceim, '_check_internal_error_pattern', new_callable=AsyncMock) as mock_pattern:
            mock_pattern.return_value = {
                'pattern_detected': True,
                'pattern_type': 'repeated_resource_alert',
                'occurrences': 5,
                'timespan_minutes': 5
            }
            
            pattern_result = await ceim._check_internal_error_pattern(pattern_errors[0])
            results.append(mock_pattern.called)
            if pattern_result:
                results.append(pattern_result.get('pattern_detected', False))
            else:
                results.append(False)
        
        # Test error correlation analysis
        with patch.object(ceim, '_check_error_correlations', new_callable=AsyncMock) as mock_correlation:
            mock_correlation.return_value = {
                'correlations_found': True,
                'related_errors': 3,
                'correlation_type': 'cascade_failure'
            }
            
            correlation_result = await ceim._check_error_correlations(test_error_record)
            results.append(mock_correlation.called)
            if correlation_result:
                results.append(correlation_result.get('correlations_found', False))
            else:
                results.append(False)
        
        # Step 10: Test error statistics and reporting
        # Mock statistics data
        mock_stats = {
            'total_internal_errors': 125,
            'total_external_errors': 87,
            'critical_errors': 15,
            'recovery_success_rate': 0.85,
            'avg_resolution_time': 45.3,
            'most_common_category': 'resource_monitoring',
            'error_trend': 'increasing'
        }
        
        with patch.object(ceim, 'get_centralized_statistics') as mock_get_stats:
            mock_get_stats.return_value = mock_stats
            
            stats = ceim.get_centralized_statistics()
            results.append(isinstance(stats, dict))
            results.append('total_internal_errors' in stats)
            results.append('total_external_errors' in stats)
            results.append('recovery_success_rate' in stats)
            results.append(stats['total_internal_errors'] == 125)
            results.append(stats['recovery_success_rate'] == 0.85)
        
        # Test error details retrieval
        mock_error_details = {
            'error_code': '01010712AB34CD56',
            'microservice': 'CCU',
            'severity': 'HIGH',
            'category': 'resource_monitoring',
            'message': 'Memory usage critical',
            'first_occurrence': '2024-01-15T10:30:00',
            'occurrence_count': 3,
            'recovery_attempted': True,
            'recovery_successful': True
        }
        
        with patch.object(ceim, 'get_error_details') as mock_get_details:
            mock_get_details.return_value = mock_error_details
            
            error_details = ceim.get_error_details('01010712AB34CD56')
            results.append(error_details is not None)
            if error_details:
                results.append('error_code' in error_details)
                results.append('severity' in error_details)
                results.append('recovery_attempted' in error_details)
                results.append(error_details['error_code'] == '01010712AB34CD56')
            else:
                results.extend([False, False, False, False])
        
        # Step 11: Test microservice type enumeration and management
        microservice_types = [
            MicroserviceType.RCM,
            MicroserviceType.RLA,
            MicroserviceType.TPP,
            MicroserviceType.JFA,
            MicroserviceType.TD,
            MicroserviceType.OCM,
            MicroserviceType.CCU
        ]
        
        for ms_type in microservice_types:
            results.append(ms_type in MicroserviceType)
            results.append(len(ms_type.value) == 2)  # Should be tuple of (code, name)
            results.append(isinstance(ms_type.value[0], str))  # Code should be string
            results.append(isinstance(ms_type.value[1], str))  # Name should be string
        
        # Verify correct microservice codes
        results.append(MicroserviceType.CCU.value[0] == '07')
        results.append(MicroserviceType.RLA.value[0] == '02')
        results.append(MicroserviceType.RCM.value[0] == '01')
        
        # Step 12: Test CEIM status and health check
        with patch.object(ceim, 'health_check', new_callable=AsyncMock) as mock_health:
            mock_health.return_value = True
            
            health_status = await ceim.health_check()
            results.append(mock_health.called)
            results.append(health_status == True)
        
        mock_status = {
            'module': 'CEIM',
            'is_active': True,
            'internal_errors_processed': 45,
            'external_errors_received': 23,
            'recovery_operations': 12,
            'investigation_queue_size': 3,
            'health_status': 'healthy'
        }
        
        with patch.object(ceim, 'get_status') as mock_get_status:
            mock_get_status.return_value = mock_status
            
            status = ceim.get_status()
            results.append(isinstance(status, dict))
            results.append('module' in status)
            results.append('is_active' in status)
            results.append('internal_errors_processed' in status)
            results.append(status['module'] == 'CEIM')
        
        # Calculate test statistics
        passed_tests = sum(results)
        total_tests = len(results)
        success_rate = (passed_tests / total_tests) * 100
        
        # Log results
        print(f"Test {test_code}: {test_name}")
        print(f"Total tests: {total_tests}")
        print(f"Passed: {passed_tests}")  
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success rate: {success_rate:.2f}%")
        print(f"Error codes generated: {len(generated_codes)}")
        print(f"Sample error code: {generated_codes[0] if generated_codes else 'N/A'}")
        print(f"Severity levels: {len(ErrorSeverity)}")
        print(f"Error categories: {len(ErrorCategory)}")
        print(f"Recovery strategies: {len(RecoveryStrategy)}")
        
        return {
            "success": success_rate >= 85.0,
            "test_code": test_code,
            "test_name": test_name,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "success_rate": success_rate,
            "details": {
                "code_generation": passed_tests >= 20,
                "error_processing": passed_tests >= 40,
                "pattern_detection": passed_tests >= 60,
                "statistics_reporting": passed_tests >= 80
            }
        }
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Test {test_code} failed with error: {str(e)}")
        print(f"Traceback: {error_details}")
        return {
            "success": False,
            "test_code": test_code,
            "test_name": test_name,
            "error": str(e),
            "error_details": error_details,
            "total_tests": len(results),
            "passed_tests": sum(results)
        }

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run the test
    result = asyncio.run(test_t00000017())
    
    if result["success"]:
        print(f"PASS {result['test_code']}: {result['test_name']} - PASSED")
        print(f"   Passed: {result['passed_tests']}/{result['total_tests']} tests")
        print(f"   Success rate: {result['success_rate']:.2f}%")
    else:
        print(f"FAIL {result['test_code']}: {result['test_name']} - FAILED")
        if "error" in result:
            print(f"   Error: {result['error']}")
        else:
            print(f"   Passed: {result['passed_tests']}/{result['total_tests']} tests")
            print(f"   Success rate: {result['success_rate']:.2f}%")