"""
Test Management Module (TMM) for JFA Microservice

This module handles testing:
- Test execution and management
- Test result collection
- Performance testing
- Integration testing
- Integration with JFATestSuite for comprehensive testing
"""

import logging
import asyncio
import importlib
import os
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

# Import the test suite
try:
    from .test_suite import JFATestSuite
except ImportError:
    # Fallback for direct execution
    sys.path.insert(0, str(Path(__file__).parent))
    from test_suite import JFATestSuite


class TestManagementModule:
    """Test Management Module for JFA"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.module_name = "TMM"
        self.is_active = False
        
        # Initialize test suite
        self.test_suite = JFATestSuite()
        
        self.test_results = []
        self.test_suites = {
            "unit": self.test_suite.unit_tests,
            "integration": self.test_suite.integration_tests,
            "all": self.test_suite.test_scripts
        }
        
        self.stats = {
            "tests_executed": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "last_test_run": None,
            "total_test_files": len(self.test_suite.test_scripts),
            "unit_test_files": len(self.test_suite.unit_tests),
            "integration_test_files": len(self.test_suite.integration_tests)
        }
        
        # Test execution tracking
        self.current_execution = None
        self.execution_history = []
    
    async def start(self):
        """Start the Test Management Module."""
        self.is_active = True
        self.logger.info(f"{self.module_name} started successfully")
        self.logger.info(f"Discovered {self.stats['total_test_files']} test files")
        self.logger.info(f"Unit tests: {self.stats['unit_test_files']}, Integration tests: {self.stats['integration_test_files']}")
    
    async def stop(self):
        """Stop the Test Management Module."""
        self.is_active = False
        self.logger.info(f"{self.module_name} stopped successfully")
    
    async def run_test_suite(self, suite_name: str) -> Dict[str, Any]:
        """Run a specific test suite."""
        try:
            self.logger.info(f"Running test suite: {suite_name}")
            start_time = datetime.now()
            
            if suite_name == "unit":
                result = await self.test_suite.run_unit_tests()
            elif suite_name == "integration":
                result = await self.test_suite.run_integration_tests()
            elif suite_name == "all":
                result = await self.test_suite.run_all_tests()
            else:
                # Try to run a specific test by name
                result = await self.test_suite.run_specific_test(suite_name)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            test_result = {
                "suite": suite_name,
                "timestamp": start_time.isoformat(),
                "duration": duration,
                "success": result.get("success", False),
                "total_tests": result.get("total_tests", 0),
                "passed_tests": result.get("passed_tests", 0),
                "failed_tests": result.get("failed_tests", 0),
                "success_rate": result.get("success_rate", 0.0),
                "results": result.get("test_results", {}),
                "summary": result.get("summary", "")
            }
            
            # Update statistics
            self.test_results.append(test_result)
            self.stats["tests_executed"] += test_result["total_tests"]
            self.stats["tests_passed"] += test_result["passed_tests"]
            self.stats["tests_failed"] += test_result["failed_tests"]
            self.stats["last_test_run"] = start_time
            
            self.logger.info(f"Test suite {suite_name} completed: {test_result['passed_tests']}/{test_result['total_tests']} passed")
            
            return test_result
            
        except Exception as e:
            self.logger.error(f"Error running test suite {suite_name}: {e}")
            return {
                "suite": suite_name,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "success": False
            }
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all test suites."""
        try:
            self.logger.info("Running all test suites")
            start_time = datetime.now()
            
            # Use the test suite to run all tests
            result = await self.test_suite.run_all_tests()
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Update statistics
            self.stats["tests_executed"] += result.get("total_tests", 0)
            self.stats["tests_passed"] += result.get("passed_tests", 0)
            self.stats["tests_failed"] += result.get("failed_tests", 0)
            self.stats["last_test_run"] = start_time
            
            return {
                "success": result.get("success", False),
                "results": result.get("test_results", {}),
                "summary": result.get("summary", ""),
                "total_tests": result.get("total_tests", 0),
                "passed_tests": result.get("passed_tests", 0),
                "failed_tests": result.get("failed_tests", 0),
                "success_rate": result.get("success_rate", 0.0),
                "duration": duration,
                "timestamp": start_time.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error running all tests: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def run_specific_test(self, test_name: str) -> Dict[str, Any]:
        """Run a specific test by name."""
        try:
            self.logger.info(f"Running specific test: {test_name}")
            result = await self.test_suite.run_specific_test(test_name)
            
            # Update statistics
            if result.get("success", False):
                self.stats["tests_executed"] += 1
                self.stats["tests_passed"] += 1
            else:
                self.stats["tests_executed"] += 1
                self.stats["tests_failed"] += 1
            
            self.stats["last_test_run"] = datetime.now()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error running test {test_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "test_name": test_name,
                "timestamp": datetime.now().isoformat()
            }
    
    async def run_unit_tests(self) -> Dict[str, Any]:
        """Run only unit tests."""
        return await self.run_test_suite("unit")
    
    async def run_integration_tests(self) -> Dict[str, Any]:
        """Run only integration tests."""
        return await self.run_test_suite("integration")
    
    def get_available_tests(self) -> Dict[str, Any]:
        """Get list of available tests."""
        return {
            "total_tests": len(self.test_suite.test_scripts),
            "unit_tests": self.test_suite.unit_tests,
            "integration_tests": self.test_suite.integration_tests,
            "all_tests": self.test_suite.test_scripts,
            "test_metadata": self.test_suite.test_metadata
        }
    
    def get_test_metadata(self, test_name: str) -> Dict[str, Any]:
        """Get metadata for a specific test."""
        return self.test_suite.get_test_metadata(test_name)
    
    def export_test_results(self, filename: str = None) -> str:
        """Export test results to a file."""
        return self.test_suite.export_results(filename)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the TMM."""
        return {
            "module": self.module_name,
            "is_active": self.is_active,
            "statistics": self.stats,
            "test_suites": list(self.test_suites.keys()),
            "available_tests": self.get_available_tests(),
            "recent_results": self.test_results[-5:] if self.test_results else [],
            "current_execution": self.current_execution,
            "timestamp": datetime.now().isoformat()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check of the TMM."""
        try:
            # Check if test suite is properly initialized
            test_suite_healthy = (
                hasattr(self, 'test_suite') and 
                self.test_suite is not None and
                len(self.test_suite.test_scripts) > 0
            )
            
            # Run a simple test to verify functionality
            if test_suite_healthy:
                # Try to run a simple test (T00000001 - JDPM test)
                test_result = await self.run_specific_test("test_t00000001")
                test_healthy = test_result.get("success", False)
            else:
                test_healthy = False
            
            return {
                "healthy": self.is_active and test_suite_healthy and test_healthy,
                "module": self.module_name,
                "test_suite_healthy": test_suite_healthy,
                "test_execution_healthy": test_healthy,
                "available_tests_count": len(self.test_suite.test_scripts) if test_suite_healthy else 0,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "module": self.module_name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_test_coverage(self) -> Dict[str, Any]:
        """Get test coverage information."""
        try:
            coverage = {
                "total_modules": 14,  # JFA has 14 modules
                "modules_with_tests": 0,
                "test_coverage_percentage": 0.0,
                "module_coverage": {}
            }
            
            # Check which modules have tests
            module_test_mapping = {
                "JDPM": ["test_t00000001"],
                "TVM": ["test_t00000002"],
                "BDM": ["test_t00000003"],
                "DAM": ["test_t00000004"],
                "IPM": ["test_t00000005"],
                "OPM": ["test_t00000006"],
                "FIM": ["test_t00000007"],
                "ECM": ["test_t00000008"],
                "ARM": ["test_t00000009"],
                "CIM": ["test_t00000010"],
                "EMM": ["test_t00000011"],
                "MSM": ["test_t00000012"],
                "BTM": ["test_t00000013"],
                "TMM": ["test_t00000014"]
            }
            
            for module, test_files in module_test_mapping.items():
                tests_exist = all(
                    test_file in self.test_suite.test_scripts 
                    for test_file in test_files
                )
                coverage["module_coverage"][module] = tests_exist
                if tests_exist:
                    coverage["modules_with_tests"] += 1
            
            coverage["test_coverage_percentage"] = (
                coverage["modules_with_tests"] / coverage["total_modules"] * 100
            )
            
            return coverage
            
        except Exception as e:
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def cleanup_test_results(self, days: int = 30) -> Dict[str, Any]:
        """Clean up old test results."""
        try:
            cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
            
            original_count = len(self.test_results)
            self.test_results = [
                result for result in self.test_results
                if datetime.fromisoformat(result["timestamp"]).timestamp() > cutoff_date
            ]
            removed_count = original_count - len(self.test_results)
            
            return {
                "success": True,
                "removed_results": removed_count,
                "remaining_results": len(self.test_results),
                "cutoff_days": days,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            } 