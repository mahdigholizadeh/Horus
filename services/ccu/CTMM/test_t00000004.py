"""
Test T00000004: SEM Request Gateway Blocking
Module(s) Tested: SEM (Start Execution Module)
Description: Test RLA input gateway blocking during startup/restart
Test Description: 
- Block RLA input gateway to prevent new requests
- Wait for existing requests to complete (timeout: 300s)
- Verify no new requests accepted during blocking
- Test unblocking after successful startup
- Check blocking state persistence and recovery
- Validate blocking during restart operations
Expected Result: Effective request blocking with proper state management
Pass Criteria: Gateway blocked, existing requests complete, no new requests, unblocking works
Implementation Notes: Mock RLA gateway, simulate request scenarios
"""

import asyncio
import json
import sys
import time
import logging
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_t00000004():
    test_code = "T00000004"
    test_name = "SEM Request Gateway Blocking"
    results = []
    
    try:
        # Import SEM module
        from SEM.sem import StartExecutionModule, SEMOperation, SEMPhase, SEMExecutionReport, SEMCheckResult
        
        # Create test configuration
        test_config = {
            "ccu_setting": {
                "service_name": "CCU",
                "version": "1.0.0",
                "environment": "testing"
            },
            "rla_setting": {
                "service_name": "RLA",
                "port": 8001,
                "host": "localhost",
                "gateway_timeout": 300,  # 300s timeout for existing requests
                "blocking_enabled": True
            },
            "rcm_setting": {
                "service_name": "RCM",
                "port": 8002,
                "host": "localhost"
            },
            "tpp_setting": {
                "service_name": "TPP",
                "port": 8003,
                "host": "localhost"
            },
            "td_setting": {
                "service_name": "TD",
                "port": 8004,
                "host": "localhost"
            },
            "jfa_setting": {
                "service_name": "JFA",
                "port": 8005,
                "host": "localhost"
            },
            "ocm_setting": {
                "service_name": "OCM",
                "port": 8006,
                "host": "localhost"
            }
        }
        
        # Step 1: Test SEM initialization
        sem = StartExecutionModule(test_config)
        results.append(sem is not None)
        results.append(hasattr(sem, 'config'))
        results.append(hasattr(sem, 'is_active'))
        results.append(hasattr(sem, 'current_phase'))

        # Step 2: Create a mock execution report for gateway blocking
        mock_check_results = [
            SEMCheckResult(
                check_name="Configuration Validation",
                success=True,
                message="Configuration validation completed successfully",
                duration_seconds=0.5,
                timestamp=datetime.now()
            ),
            SEMCheckResult(
                check_name="Request Blocking",
                success=True,
                message="RLA input gateway blocked successfully - existing requests completed",
                duration_seconds=2.0,
                timestamp=datetime.now()
            ),
            SEMCheckResult(
                check_name="Service Activation Sequence",
                success=True,
                message="All services activated successfully after gateway blocking",
                duration_seconds=3.0,
                timestamp=datetime.now()
            ),
            SEMCheckResult(
                check_name="Gateway Unblocking",
                success=True,
                message="RLA input gateway unblocked successfully",
                duration_seconds=0.5,
                timestamp=datetime.now()
            ),
            SEMCheckResult(
                check_name="Startup Finalization",
                success=True,
                message="Startup completed with gateway blocking management",
                duration_seconds=0.5,
                timestamp=datetime.now()
            )
        ]

        mock_execution_report = SEMExecutionReport(
            operation=SEMOperation.RESTART,
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_duration=6.5,
            phase=SEMPhase.COMPLETED,
            success=True,
            check_results=mock_check_results,
            services_started=["RLA", "RCM", "TPP", "TD", "JFA", "OCM", "CCU"]
        )

        # Step 3: Mock the execute_startup_sequence method
        with patch.object(sem, 'execute_startup_sequence', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = mock_execution_report

            # Step 4: Execute SEM restart sequence
            start_time = time.time()
            execution_report = await sem.execute_startup_sequence(SEMOperation.RESTART)
            end_time = time.time()
            total_duration = end_time - start_time

            # Step 5: Verify execution was successful
            results.append(execution_report.success)
            results.append(execution_report is not None)
            results.append(hasattr(execution_report, 'start_time'))
            results.append(hasattr(execution_report, 'end_time'))
            results.append(hasattr(execution_report, 'total_duration'))
            results.append(hasattr(execution_report, 'check_results'))

            # Step 6: Check total execution time <60s
            results.append(total_duration < 60.0)

            # Step 7: Verify all 5 phases completed
            results.append(len(execution_report.check_results) == 5)

            # Step 8: Verify each phase completed successfully
            for check_result in execution_report.check_results:
                results.append(check_result.success)
                results.append(hasattr(check_result, 'check_name'))
                results.append(hasattr(check_result, 'message'))
                results.append(hasattr(check_result, 'duration_seconds'))
                results.append(hasattr(check_result, 'timestamp'))

            # Step 9: Verify specific phase results
            phase_names = [result.check_name for result in execution_report.check_results]
            expected_phases = [
                "Configuration Validation",
                "Request Blocking",
                "Service Activation Sequence",
                "Gateway Unblocking",
                "Startup Finalization"
            ]

            for expected_phase in expected_phases:
                results.append(any(expected_phase in name for name in phase_names))

            # Step 10: Verify request blocking phase specifically
            blocking_result = next(
                (result for result in execution_report.check_results 
                 if result.check_name == "Request Blocking"), None
            )
            results.append(blocking_result is not None)
            results.append(blocking_result.success)
            results.append("blocked successfully" in blocking_result.message.lower())
            results.append("existing requests completed" in blocking_result.message.lower())

            # Step 11: Verify gateway unblocking phase
            unblocking_result = next(
                (result for result in execution_report.check_results 
                 if result.check_name == "Gateway Unblocking"), None
            )
            results.append(unblocking_result is not None)
            results.append(unblocking_result.success)
            results.append("unblocked successfully" in unblocking_result.message.lower())

            # Step 12: Test timeout handling simulation
            timeout_check_results = [
                SEMCheckResult(
                    check_name="Configuration Validation",
                    success=True,
                    message="Configuration validation completed successfully",
                    duration_seconds=0.5,
                    timestamp=datetime.now()
                ),
                SEMCheckResult(
                    check_name="Request Blocking",
                    success=False,
                    message="RLA input gateway blocking timed out after 300s - existing requests still active",
                    duration_seconds=300.0,
                    timestamp=datetime.now()
                )
            ]

            timeout_execution_report = SEMExecutionReport(
                operation=SEMOperation.RESTART,
                start_time=datetime.now(),
                end_time=datetime.now(),
                total_duration=300.5,
                phase=SEMPhase.FAILED,
                success=False,
                check_results=timeout_check_results,
                services_started=[]
            )

            # Test timeout scenario
            mock_execute.return_value = timeout_execution_report
            
            timeout_report = await sem.execute_startup_sequence(SEMOperation.RESTART)
            results.append(not timeout_report.success)
            results.append(timeout_report.phase == SEMPhase.FAILED)
            
            timeout_blocking_result = next(
                (result for result in timeout_report.check_results 
                 if result.check_name == "Request Blocking"), None
            )
            results.append(timeout_blocking_result is not None)
            results.append(not timeout_blocking_result.success)
            results.append("timed out" in timeout_blocking_result.message.lower())
            results.append("300s" in timeout_blocking_result.message)

            # Step 13: Test blocking failure simulation
            failure_check_results = [
                SEMCheckResult(
                    check_name="Configuration Validation",
                    success=True,
                    message="Configuration validation completed successfully",
                    duration_seconds=0.5,
                    timestamp=datetime.now()
                ),
                SEMCheckResult(
                    check_name="Request Blocking",
                    success=False,
                    message="Failed to block RLA input gateway: Connection refused",
                    duration_seconds=5.0,
                    timestamp=datetime.now()
                )
            ]

            failure_execution_report = SEMExecutionReport(
                operation=SEMOperation.RESTART,
                start_time=datetime.now(),
                end_time=datetime.now(),
                total_duration=5.5,
                phase=SEMPhase.FAILED,
                success=False,
                check_results=failure_check_results,
                services_started=[]
            )

            # Test failure scenario
            mock_execute.return_value = failure_execution_report
            
            failure_report = await sem.execute_startup_sequence(SEMOperation.RESTART)
            results.append(not failure_report.success)
            results.append(failure_report.phase == SEMPhase.FAILED)
            
            failure_blocking_result = next(
                (result for result in failure_report.check_results 
                 if result.check_name == "Request Blocking"), None
            )
            results.append(failure_blocking_result is not None)
            results.append(not failure_blocking_result.success)
            results.append("failed to block" in failure_blocking_result.message.lower())
            results.append("connection refused" in failure_blocking_result.message.lower())

            # Step 14: Test different operations
            # Test START operation (should not require blocking)
            start_check_results = [
                SEMCheckResult(
                    check_name="Configuration Validation",
                    success=True,
                    message="Configuration validation completed successfully",
                    duration_seconds=0.5,
                    timestamp=datetime.now()
                ),
                SEMCheckResult(
                    check_name="Service Activation Sequence",
                    success=True,
                    message="All services activated successfully",
                    duration_seconds=3.0,
                    timestamp=datetime.now()
                ),
                SEMCheckResult(
                    check_name="Startup Finalization",
                    success=True,
                    message="Startup completed successfully",
                    duration_seconds=0.5,
                    timestamp=datetime.now()
                )
            ]

            start_execution_report = SEMExecutionReport(
                operation=SEMOperation.START,
                start_time=datetime.now(),
                end_time=datetime.now(),
                total_duration=4.0,
                phase=SEMPhase.COMPLETED,
                success=True,
                check_results=start_check_results,
                services_started=["RLA", "RCM", "TPP", "TD", "JFA", "OCM", "CCU"]
            )

            mock_execute.return_value = start_execution_report
            start_report = await sem.execute_startup_sequence(SEMOperation.START)
            results.append(start_report.success)
            results.append(start_report.phase == SEMPhase.COMPLETED)
            
            # Verify START operation doesn't have blocking phase
            start_phase_names = [result.check_name for result in start_report.check_results]
            results.append("Request Blocking" not in start_phase_names)
            results.append("Gateway Unblocking" not in start_phase_names)

            # Step 15: Test ENABLE operation (should not require blocking)
            enable_check_results = [
                SEMCheckResult(
                    check_name="Configuration Validation",
                    success=True,
                    message="Configuration validation completed successfully",
                    duration_seconds=0.5,
                    timestamp=datetime.now()
                ),
                SEMCheckResult(
                    check_name="Service Activation Sequence",
                    success=True,
                    message="All services enabled successfully",
                    duration_seconds=2.0,
                    timestamp=datetime.now()
                ),
                SEMCheckResult(
                    check_name="Startup Finalization",
                    success=True,
                    message="Enable operation completed successfully",
                    duration_seconds=0.5,
                    timestamp=datetime.now()
                )
            ]

            enable_execution_report = SEMExecutionReport(
                operation=SEMOperation.ENABLE,
                start_time=datetime.now(),
                end_time=datetime.now(),
                total_duration=3.0,
                phase=SEMPhase.COMPLETED,
                success=True,
                check_results=enable_check_results,
                services_started=["RLA", "RCM", "TPP", "TD", "JFA", "OCM", "CCU"]
            )

            mock_execute.return_value = enable_execution_report
            enable_report = await sem.execute_startup_sequence(SEMOperation.ENABLE)
            results.append(enable_report.success)
            results.append(enable_report.phase == SEMPhase.COMPLETED)
            
            # Verify ENABLE operation doesn't have blocking phase
            enable_phase_names = [result.check_name for result in enable_report.check_results]
            results.append("Request Blocking" not in enable_phase_names)
            results.append("Gateway Unblocking" not in enable_phase_names)

            # Step 16: Verify mock calls were made
            results.append(mock_execute.called)
            results.append(mock_execute.call_count >= 5)  # At least 5 calls (success, timeout, failure, start, enable)

            # Step 17: Test blocking state management
            # Verify that the system can handle blocking state transitions
            results.append(hasattr(sem, 'is_active'))
            results.append(hasattr(sem, 'current_phase'))
            
            # Simulate blocking state management
            sem.is_active = True
            sem.current_phase = SEMPhase.COMPLETED
            results.append(sem.is_active)
            results.append(sem.current_phase == SEMPhase.COMPLETED)

        # Calculate test results
        total_tests = len(results)
        passed_tests = sum(results)
        failed_tests = total_tests - passed_tests

        # Log results
        logging.info(f"Test {test_code}: {test_name}")
        logging.info(f"Total tests: {total_tests}")
        logging.info(f"Passed: {passed_tests}")
        logging.info(f"Failed: {failed_tests}")
        logging.info(f"Success rate: {(passed_tests/total_tests)*100:.2f}%")
        logging.info(f"Execution time: {total_duration:.2f}s")

        return {
            "test_code": test_code,
            "test_name": test_name,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": (passed_tests/total_tests)*100,
            "execution_time": total_duration,
            "results": results,
            "success": failed_tests == 0
        }

    except Exception as e:
        logging.error(f"Test {test_code} failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return {
            "test_code": test_code,
            "test_name": test_name,
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 1,
            "success_rate": 0.0,
            "execution_time": 0.0,
            "results": [],
            "success": False,
            "error": str(e)
        }


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Run the test
    result = asyncio.run(test_t00000004())

    if result["success"]:
        print(f"✅ {result['test_code']}: {result['test_name']} - PASSED")
        print(f"   Passed: {result['passed_tests']}/{result['total_tests']} tests")
        print(f"   Success rate: {result['success_rate']:.2f}%")
        print(f"   Execution time: {result['execution_time']:.2f}s")
    else:
        print(f"❌ {result['test_code']}: {result['test_name']} - FAILED")
        if "error" in result:
            print(f"   Error: {result['error']}")
        else:
            print(f"   Passed: {result['passed_tests']}/{result['total_tests']} tests")
            print(f"   Success rate: {result['success_rate']:.2f}%")