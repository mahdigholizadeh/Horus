"""
Comprehensive Test Runner for RCM Microservice

This module executes all unit tests (T0000001-T0000046) and integration tests (T0000022-T0000039),
logs results to the DCMM database, and provides detailed reporting.
"""

import asyncio
import json
import logging
import sys
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import importlib.util

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from DCMM.dcmm import DatabaseControlAndManagementModule
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler
from TMM.tmm import TestManagementModule

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_runner.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class ComprehensiveTestRunner:
    """
    Comprehensive test runner for RCM microservice.
    
    Executes all unit tests and integration tests, logs results to DCMM database,
    and provides detailed reporting.
    """
    
    def __init__(self):
        """Initialize the test runner."""
        self.dcmm = DatabaseControlAndManagementModule()
        self.error_manager = ErrorManagementModule()
        self.tmm = TestManagementModule()
        
        # Test categories
        self.unit_tests = [
            "T0000001", "T0000002", "T0000003", "T0000004", "T0000005", "T0000006", "T0000007", "T0000008", "T0000009", "T0000010",
            "T0000011", "T0000012", "T0000013", "T0000014", "T0000015", "T0000016", "T0000017", "T0000018", "T0000019", "T0000020",
            "T0000021", "T0000027", "T0000028", "T0000029", "T0000030", "T0000031", "T0000032", "T0000033", "T0000040", "T0000041",
            "T0000042", "T0000043", "T0000044", "T0000045", "T0000046"
        ]
        
        self.integration_tests = [
            "T0000022", "T0000023", "T0000024", "T0000025", "T0000026", "T0000034", "T0000035", "T0000036", "T0000037", "T0000038", "T0000039"
        ]
        
        # Test metadata
        self.test_metadata = {
            "T0000001": {"name": "GIDVM - Successful Ingestion & Sorting", "modules": ["GIDVM"]},
            "T0000002": {"name": "GIDVM - Invalid JSON Rejection", "modules": ["GIDVM"]},
            "T0000003": {"name": "PBRPM - Priority Queue Processing", "modules": ["PBRPM"]},
            "T0000004": {"name": "AACM - Successful Async API Call", "modules": ["AACM"]},
            "T0000005": {"name": "RTRMM - Response to Request ID Mapping", "modules": ["RTRMM"]},
            "T0000006": {"name": "RLM - Rate Limit Enforcement", "modules": ["RLM"]},
            "T0000007": {"name": "MMM & DRM - Memory Spill-to-Disk & Restore", "modules": ["MMM", "DRM"]},
            "T0000008": {"name": "BAAIM - Default & Override API Usage", "modules": ["BAAIM"]},
            "T0000009": {"name": "AAAIM - Default & Override Agent Usage", "modules": ["AAAIM"]},
            "T0000010": {"name": "SAAIM - Special API Call", "modules": ["SAAIM"]},
            "T0000011": {"name": "SODVM - JSON Verification", "modules": ["SODVM"]},
            "T0000012": {"name": "DCMM - Full CRUD Operations", "modules": ["DCMM"]},
            "T0000013": {"name": "TMM - Test Execution and Logging", "modules": ["TMM"]},
            "T0000014": {"name": "EMM - Error Code Generation & Logging", "modules": ["EMM"]},
            "T0000015": {"name": "MSM - System Monitoring Report", "modules": ["MSM"]},
            "T0000016": {"name": "MSM - Token Calculation", "modules": ["MSM"]},
            "T0000017": {"name": "SMSM - System Message Injection", "modules": ["SMSM"]},
            "T0000018": {"name": "SMCM - API Model Change", "modules": ["SMCM"]},
            "T0000019": {"name": "JFAIM - Handoff to JFA", "modules": ["JFAIM"]},
            "T0000020": {"name": "OCMIM - Handoff to OCM", "modules": ["OCMIM"]},
            "T0000021": {"name": "ECM - CCU Command Reception", "modules": ["ECM"]},
            "T0000027": {"name": "RLM - Retry Mechanism on Failure", "modules": ["RLM"]},
            "T0000028": {"name": "FAIM - API Endpoint Verification", "modules": ["FAIM"]},
            "T0000029": {"name": "BTM - Automated Cleanup Task", "modules": ["BTM"]},
            "T0000030": {"name": "EMM - Error Code Auto-Generation", "modules": ["EMM"]},
            "T0000031": {"name": "ECM - Dynamic Rate Limit Update", "modules": ["ECM"]},
            "T0000032": {"name": "ECM - Module Reset Command", "modules": ["ECM"]},
            "T0000033": {"name": "ECM - Remote DB Query", "modules": ["ECM"]},
            "T0000040": {"name": "Human Interaction Benchmark", "modules": ["RCM"]},
            "T0000041": {"name": "FDM - File Detection Module", "modules": ["FDM"]},
            "T0000042": {"name": "FBWM - File-based Workflow Module", "modules": ["FBWM"]},
            "T0000043": {"name": "PRM - Priority Routing Module", "modules": ["PRM"]},
            "T0000044": {"name": "FOM - File Output Module", "modules": ["FOM"]},
            "T0000045": {"name": "BTM - Background Tasks Module Comprehensive", "modules": ["BTM"]},
            "T0000046": {"name": "FAIM - FastAPI Integration Module Comprehensive", "modules": ["FAIM"]},
            "T0000022": {"name": "Workflow: Standard Successful Request", "modules": ["RCM"]},
            "T0000023": {"name": "Workflow: JFA Template Fulfillment", "modules": ["RCM", "JFA"]},
            "T0000024": {"name": "Workflow: Error Handling & Recovery", "modules": ["RCM", "EMM"]},
            "T0000025": {"name": "Workflow: CCU Remote Control - API Key Change", "modules": ["RCM", "ECM"]},
            "T0000026": {"name": "Workflow: CCU Remote Control - Test Execution", "modules": ["RCM", "ECM", "TMM"]},
            "T0000034": {"name": "Workflow: High-Load Stress Test", "modules": ["RCM"]},
            "T0000035": {"name": "Workflow: Mid-Conversation Model Switch", "modules": ["RCM", "SMCM"]},
            "T0000036": {"name": "Workflow: Mid-Conversation System Message Injection", "modules": ["RCM", "SMSM"]},
            "T0000037": {"name": "Workflow: End-to-End Failure, Retry, and Reporting", "modules": ["RCM", "EMM", "RLM"]},
            "T0000038": {"name": "Workflow: Complex CCU Remote Control", "modules": ["RCM", "ECM"]},
            "T0000039": {"name": "Workflow: Concurrent Request Integrity", "modules": ["RCM"]}
        }
        
        # Test results storage
        self.test_results = {}
        self.execution_stats = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "skipped_tests": 0,
            "start_time": None,
            "end_time": None,
            "total_execution_time": 0
        }
    
    async def initialize_test_database(self):
        """Initialize the test database using DCMM."""
        try:
            logger.info("Initializing test database...")
            
            # Create test database tables
            await self.dcmm.start()
            
            # Log initialization
            await self.dcmm.log_test_result(
                test_code="INIT",
                test_name="Test Database Initialization",
                status="pass",
                output="Test database initialized successfully",
                execution_time=time.time()
            )
            
            logger.info("Test database initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize test database: {e}")
            return False
    
    def load_test_module(self, test_code: str) -> Optional[Any]:
        """Dynamically load a test module."""
        try:
            test_file = f"test_{test_code.lower()}.py"
            test_path = Path(__file__).parent / test_file
            
            if not test_path.exists():
                logger.warning(f"Test file not found: {test_file}")
                return None
            
            # Load the module
            spec = importlib.util.spec_from_file_location(f"test_{test_code}", test_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            return module
        except Exception as e:
            logger.error(f"Failed to load test module {test_code}: {e}")
            return None
    
    async def execute_single_test(self, test_code: str) -> Dict[str, Any]:
        """Execute a single test and log results."""
        start_time = time.time()
        
        try:
            logger.info(f"Executing test: {test_code}")
            
            # Get test metadata
            metadata = self.test_metadata.get(test_code, {"name": f"Unknown Test {test_code}", "modules": []})
            test_name = metadata["name"]
            
            # Try to load and execute the test
            test_module = self.load_test_module(test_code)
            
            if test_module is None:
                # Fallback to TMM test execution
                result = await self.tmm.run_test_by_code(test_code)
            else:
                # Execute the test function
                test_func_name = f"test_{test_code.lower()}"
                if hasattr(test_module, test_func_name):
                    test_func = getattr(test_module, test_func_name)
                    if asyncio.iscoroutinefunction(test_func):
                        result = await test_func()
                    else:
                        result = test_func()
                else:
                    # Try to find any test function
                    test_functions = [name for name in dir(test_module) if name.startswith('test_')]
                    if test_functions:
                        test_func = getattr(test_module, test_functions[0])
                        if asyncio.iscoroutinefunction(test_func):
                            result = await test_func()
                        else:
                            result = test_func()
                    else:
                        result = {"success": False, "error": "No test function found"}
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Determine test status
            if isinstance(result, dict):
                success = result.get("success", False)
                output = result.get("message", result.get("error", "No output"))
            else:
                success = bool(result)
                output = str(result)
            
            status = "pass" if success else "fail"
            
            # Log to database
            await self.dcmm.log_test_result(
                test_code=test_code,
                test_name=test_name,
                status=status,
                output=output,
                execution_time=execution_time
            )
            
            # Update statistics
            self.execution_stats["total_tests"] += 1
            if success:
                self.execution_stats["passed_tests"] += 1
            else:
                self.execution_stats["failed_tests"] += 1
            
            # Store result
            self.test_results[test_code] = {
                "success": success,
                "test_name": test_name,
                "execution_time": execution_time,
                "output": output,
                "status": status
            }
            
            logger.info(f"Test {test_code} completed: {status}")
            return self.test_results[test_code]
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Test execution failed: {e}"
            
            # Log error to database
            await self.dcmm.log_test_result(
                test_code=test_code,
                test_name=self.test_metadata.get(test_code, {}).get("name", f"Unknown Test {test_code}"),
                status="fail",
                output=error_msg,
                execution_time=execution_time
            )
            
            # Update statistics
            self.execution_stats["total_tests"] += 1
            self.execution_stats["failed_tests"] += 1
            
            # Store result
            self.test_results[test_code] = {
                "success": False,
                "test_name": self.test_metadata.get(test_code, {}).get("name", f"Unknown Test {test_code}"),
                "execution_time": execution_time,
                "output": error_msg,
                "status": "fail"
            }
            
            logger.error(f"Test {test_code} failed: {e}")
            return self.test_results[test_code]
    
    async def run_unit_tests(self) -> Dict[str, Any]:
        """Run all unit tests."""
        logger.info("Starting unit tests execution...")
        
        self.execution_stats["start_time"] = time.time()
        
        results = []
        for test_code in self.unit_tests:
            result = await self.execute_single_test(test_code)
            results.append(result)
        
        self.execution_stats["end_time"] = time.time()
        self.execution_stats["total_execution_time"] = self.execution_stats["end_time"] - self.execution_stats["start_time"]
        
        summary = {
            "test_type": "unit",
            "total_tests": len(self.unit_tests),
            "passed_tests": self.execution_stats["passed_tests"],
            "failed_tests": self.execution_stats["failed_tests"],
            "success_rate": (self.execution_stats["passed_tests"] / len(self.unit_tests)) * 100 if self.unit_tests else 0,
            "total_execution_time": self.execution_stats["total_execution_time"],
            "results": results
        }
        
        logger.info(f"Unit tests completed: {summary['passed_tests']}/{summary['total_tests']} passed")
        return summary
    
    async def run_integration_tests(self) -> Dict[str, Any]:
        """Run all integration tests."""
        logger.info("Starting integration tests execution...")
        
        # Reset stats for integration tests
        self.execution_stats["passed_tests"] = 0
        self.execution_stats["failed_tests"] = 0
        
        self.execution_stats["start_time"] = time.time()
        
        results = []
        for test_code in self.integration_tests:
            result = await self.execute_single_test(test_code)
            results.append(result)
        
        self.execution_stats["end_time"] = time.time()
        self.execution_stats["total_execution_time"] = self.execution_stats["end_time"] - self.execution_stats["start_time"]
        
        summary = {
            "test_type": "integration",
            "total_tests": len(self.integration_tests),
            "passed_tests": self.execution_stats["passed_tests"],
            "failed_tests": self.execution_stats["failed_tests"],
            "success_rate": (self.execution_stats["passed_tests"] / len(self.integration_tests)) * 100 if self.integration_tests else 0,
            "total_execution_time": self.execution_stats["total_execution_time"],
            "results": results
        }
        
        logger.info(f"Integration tests completed: {summary['passed_tests']}/{summary['total_tests']} passed")
        return summary
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests (unit and integration)."""
        logger.info("Starting comprehensive test execution...")
        
        # Initialize test database
        if not await self.initialize_test_database():
            return {"success": False, "error": "Failed to initialize test database"}
        
        # Run unit tests
        unit_results = await self.run_unit_tests()
        
        # Run integration tests
        integration_results = await self.run_integration_tests()
        
        # Calculate overall statistics
        total_tests = unit_results["total_tests"] + integration_results["total_tests"]
        total_passed = unit_results["passed_tests"] + integration_results["passed_tests"]
        total_failed = unit_results["failed_tests"] + integration_results["failed_tests"]
        
        overall_summary = {
            "success": total_failed == 0,
            "total_tests": total_tests,
            "passed_tests": total_passed,
            "failed_tests": total_failed,
            "success_rate": (total_passed / total_tests) * 100 if total_tests > 0 else 0,
            "unit_tests": unit_results,
            "integration_tests": integration_results,
            "execution_time": unit_results["total_execution_time"] + integration_results["total_execution_time"]
        }
        
        logger.info(f"All tests completed: {total_passed}/{total_tests} passed")
        return overall_summary
    
    async def generate_test_report(self, results: Dict[str, Any]) -> str:
        """Generate a detailed test report."""
        report = []
        report.append("=" * 80)
        report.append("COMPREHENSIVE TEST REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Overall summary
        report.append("OVERALL SUMMARY")
        report.append("-" * 40)
        report.append(f"Total Tests: {results['total_tests']}")
        report.append(f"Passed: {results['passed_tests']}")
        report.append(f"Failed: {results['failed_tests']}")
        report.append(f"Success Rate: {results['success_rate']:.2f}%")
        report.append(f"Total Execution Time: {results['execution_time']:.2f} seconds")
        report.append("")
        
        # Unit tests summary
        unit_results = results["unit_tests"]
        report.append("UNIT TESTS SUMMARY")
        report.append("-" * 40)
        report.append(f"Total: {unit_results['total_tests']}")
        report.append(f"Passed: {unit_results['passed_tests']}")
        report.append(f"Failed: {unit_results['failed_tests']}")
        report.append(f"Success Rate: {unit_results['success_rate']:.2f}%")
        report.append(f"Execution Time: {unit_results['total_execution_time']:.2f} seconds")
        report.append("")
        
        # Integration tests summary
        integration_results = results["integration_tests"]
        report.append("INTEGRATION TESTS SUMMARY")
        report.append("-" * 40)
        report.append(f"Total: {integration_results['total_tests']}")
        report.append(f"Passed: {integration_results['passed_tests']}")
        report.append(f"Failed: {integration_results['failed_tests']}")
        report.append(f"Success Rate: {integration_results['success_rate']:.2f}%")
        report.append(f"Execution Time: {integration_results['total_execution_time']:.2f} seconds")
        report.append("")
        
        # Failed tests details
        failed_tests = []
        for test_code, result in self.test_results.items():
            if not result["success"]:
                failed_tests.append((test_code, result))
        
        if failed_tests:
            report.append("FAILED TESTS DETAILS")
            report.append("-" * 40)
            for test_code, result in failed_tests:
                report.append(f"Test: {test_code} - {result['test_name']}")
                report.append(f"Error: {result['output']}")
                report.append(f"Execution Time: {result['execution_time']:.2f} seconds")
                report.append("")
        
        # Database query for additional statistics
        try:
            db_info = await self.dcmm.get_database_info()
            report.append("DATABASE STATISTICS")
            report.append("-" * 40)
            report.append(f"Total Test Records: {db_info.get('test_results', {}).get('record_count', 0)}")
            report.append(f"Database Size: {db_info.get('total_size', 'Unknown')}")
            report.append("")
        except Exception as e:
            report.append(f"Database statistics unavailable: {e}")
            report.append("")
        
        report.append("=" * 80)
        report.append("END OF REPORT")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    async def cleanup(self):
        """Clean up resources."""
        try:
            await self.dcmm.stop()
            logger.info("Test runner cleanup completed")
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


async def main():
    """Main function to run the comprehensive test suite."""
    runner = ComprehensiveTestRunner()
    
    try:
        logger.info("Starting comprehensive test execution...")
        
        # Run all tests
        results = await runner.run_all_tests()
        
        # Generate and save report
        report = await runner.generate_test_report(results)
        
        # Save report to file
        report_file = Path(__file__).parent / "test_report.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        # Print report to console
        print(report)
        
        # Save detailed results to JSON
        results_file = Path(__file__).parent / "test_results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Test execution completed. Report saved to: {report_file}")
        logger.info(f"Detailed results saved to: {results_file}")
        
        return results
        
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        return {"success": False, "error": str(e)}
    
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main()) 
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
