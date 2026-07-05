"""
Test file for SEM (Start Execution Module) Pilot Checklist Complete Execution
Test ID: test_t00000001

This test verifies complete SEM pilot checklist execution with all phases:
- Execute SEM startup sequence with SEMOperation.START
- Verify all 6 phases complete successfully
- Check total execution time <60s
- Validate configuration freeze after successful startup
- Verify SEM auto-deactivation after completion
- Test startup report generation and persistence
"""

import asyncio
import logging
import json
import time
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import unittest
from unittest.mock import Mock, patch, AsyncMock

# Import the modules we're testing
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from SEM.sem import StartExecutionModule, SEMOperation, SEMPhase
from PMM.pmm import PathManagementModule, Environment


class TestSEMPilotChecklistCompleteExecution(unittest.TestCase):
    """Test case for SEM pilot checklist complete execution."""
    
    def setUp(self):
        """Set up test environment."""
        self.logger = logging.getLogger(__name__)
        
        # Create test configuration
        self.test_config = {
            "ccu_setting": {
                "service_name": "CCU",
                "version": "1.0.0",
                "environment": "testing"
            },
            "rla_setting": {
                "service_name": "RLA",
                "port": 8001,
                "host": "localhost"
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
        
        # Mock all dependent services
        self._setup_mocks()
    
    def _setup_mocks(self):
        """Set up mocks for dependent services."""
        # Mock service activation checker
        self.mock_service_checker = Mock()
        self.mock_service_checker.activate_service = AsyncMock(return_value=Mock(
            success=True,
            message="Service activated successfully"
        ))
        
        # Mock API connectivity checker
        self.mock_api_checker = Mock()
        self.mock_api_checker.test_all_api_connections = AsyncMock(return_value=[
            Mock(success=True, message="API connection successful")
        ])
        self.mock_api_checker.test_webserver_connectivity = AsyncMock(return_value=[
            Mock(success=True, message="Webserver connection successful")
        ])
        
        # Mock interaction module checker
        self.mock_interaction_checker = Mock()
        self.mock_interaction_checker.test_all_interaction_modules = AsyncMock(return_value=[
            Mock(success=True, message="Interaction module test successful")
        ])
        
        # Mock workflow integration checker
        self.mock_workflow_checker = Mock()
        self.mock_workflow_checker.test_end_to_end_workflow = AsyncMock(return_value=Mock(
            success=True,
            message="End-to-end workflow test successful"
        ))
        
        # Mock systemd integrator
        self.mock_systemd_integrator = Mock()
        self.mock_systemd_integrator.update_service_status = AsyncMock(return_value=True)
        
        # Mock test results reporter
        self.mock_reporter = Mock()
        self.mock_reporter.generate_final_report = AsyncMock(return_value=True)
    
    @patch('SEM.sem.ServiceActivationChecker')
    @patch('SEM.sem.APIConnectivityChecker')
    @patch('SEM.sem.InteractionModuleChecker')
    @patch('SEM.sem.WorkflowIntegrationChecker')
    @patch('SEM.sem.SystemdIntegrator')
    @patch('SEM.sem.TestResultsReporter')
    async def test_t00000001_sem_pilot_checklist_complete_execution(self, 
                                                                   mock_reporter_class,
                                                                   mock_systemd_class,
                                                                   mock_workflow_class,
                                                                   mock_interaction_class,
                                                                   mock_api_class,
                                                                   mock_service_class):
        """Test complete SEM pilot checklist execution with all phases."""
        
        # Configure mocks
        mock_service_class.return_value = self.mock_service_checker
        mock_api_class.return_value = self.mock_api_checker
        mock_interaction_class.return_value = self.mock_interaction_checker
        mock_workflow_class.return_value = self.mock_workflow_checker
        mock_systemd_class.return_value = self.mock_systemd_integrator
        mock_reporter_class.return_value = self.mock_reporter
        
        # Initialize SEM with test configuration
        sem = StartExecutionModule(self.test_config)
        
        # Record start time
        start_time = time.time()
        
        # Execute SEM startup sequence
        execution_report = await sem.execute_startup_sequence(SEMOperation.START)
        
        # Record end time
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Test assertions
        
        # 1. Verify execution was successful
        self.assertTrue(execution_report.success, 
                       f"SEM execution failed: {execution_report.error_summary}")
        
        # 2. Check total execution time <60s
        self.assertLess(total_duration, 60.0, 
                       f"SEM execution took {total_duration:.2f}s, expected <60s")
        
        # 3. Verify all 6 phases completed
        expected_phases = [
            SEMPhase.CONFIG_VALIDATION,
            SEMPhase.BLOCKING_REQUESTS,
            SEMPhase.SERVICE_ACTIVATION,
            SEMPhase.FUNCTIONALITY_TESTING,
            SEMPhase.WORKFLOW_VALIDATION,
            SEMPhase.FINALIZING
        ]
        
        completed_phases = [result.check_name for result in execution_report.check_results]
        self.assertEqual(len(execution_report.check_results), 6,
                        f"Expected 6 phases, got {len(execution_report.check_results)}")
        
        # 4. Verify configuration freeze
        self.assertTrue(sem.is_config_frozen(), 
                       "Configuration should be frozen after successful startup")
        
        frozen_config = sem.get_frozen_config()
        self.assertIsNotNone(frozen_config, "Frozen configuration should not be None")
        self.assertIn('_frozen_at', frozen_config, "Frozen config should have timestamp")
        self.assertIn('_sem_operation', frozen_config, "Frozen config should have operation")
        
        # 5. Verify SEM auto-deactivation
        self.assertFalse(sem.is_active, "SEM should be auto-deactivated after completion")
        self.assertEqual(sem.current_phase, SEMPhase.INACTIVE, 
                        "SEM should be in INACTIVE phase after completion")
        
        # 6. Verify startup report generation
        self.assertIsNotNone(execution_report, "Execution report should be generated")
        self.assertIsNotNone(execution_report.start_time, "Report should have start time")
        self.assertIsNotNone(execution_report.end_time, "Report should have end time")
        self.assertIsNotNone(execution_report.total_duration, "Report should have duration")
        
        # 7. Verify all check results are successful
        for check_result in execution_report.check_results:
            self.assertTrue(check_result.success, 
                           f"Check {check_result.check_name} failed: {check_result.message}")
        
        # 8. Verify service activation sequence
        service_activation_result = next(
            (result for result in execution_report.check_results 
             if result.check_name == "Service Activation Sequence"), None
        )
        self.assertIsNotNone(service_activation_result, "Service activation result should exist")
        self.assertTrue(service_activation_result.success, "Service activation should succeed")
        
        # 9. Verify functionality testing
        functionality_result = next(
            (result for result in execution_report.check_results 
             if result.check_name == "Quick Functionality Testing"), None
        )
        self.assertIsNotNone(functionality_result, "Functionality testing result should exist")
        self.assertTrue(functionality_result.success, "Functionality testing should succeed")
        
        # 10. Verify workflow validation
        workflow_result = next(
            (result for result in execution_report.check_results 
             if result.check_name == "End-to-End Workflow Validation"), None
        )
        self.assertIsNotNone(workflow_result, "Workflow validation result should exist")
        self.assertTrue(workflow_result.success, "Workflow validation should succeed")
        
        # Log test results
        self.logger.info(f"✅ SEM pilot checklist completed successfully in {total_duration:.2f}s")
        self.logger.info(f"✅ All {len(execution_report.check_results)} phases completed")
        self.logger.info(f"✅ Configuration frozen: {sem.is_config_frozen()}")
        self.logger.info(f"✅ SEM deactivated: {not sem.is_active}")
        
        # Verify mock calls
        self.mock_service_checker.activate_service.assert_called()
        self.mock_api_checker.test_all_api_connections.assert_called_once()
        self.mock_api_checker.test_webserver_connectivity.assert_called_once()
        self.mock_interaction_checker.test_all_interaction_modules.assert_called_once()
        self.mock_workflow_checker.test_end_to_end_workflow.assert_called_once()
        self.mock_systemd_integrator.update_service_status.assert_called()
        self.mock_reporter.generate_final_report.assert_called_once()


def run_test():
    """Run the test."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create test suite
    test_suite = unittest.TestSuite()
    test_suite.addTest(TestSEMPilotChecklistCompleteExecution('test_t00000001_sem_pilot_checklist_complete_execution'))
    
    # Run test
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    # Run the test
    success = run_test()
    if success:
        print("✅ test_t00000001: SEM Pilot Checklist Complete Execution - PASSED")
    else:
        print("❌ test_t00000001: SEM Pilot Checklist Complete Execution - FAILED")