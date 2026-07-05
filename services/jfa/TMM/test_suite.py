"""
JFA Modular Architecture Test Suite

This module contains all test cases for the JFA microservice modular architecture.
Tests are organized into Unit Tests (T0000001-T0000014) and Integration/E2E Tests (T0000015-T0000018).
"""

import asyncio
import importlib
import os
import sys
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import subprocess
import json

class JFATestSuite:
    """
    Comprehensive test suite for JFA modular architecture.
    
    Unit Tests (T0000001-T0000014):
    - Individual module functionality testing
    - Error handling and recovery testing
    - API interaction testing
    - Security validation testing
    
    Integration/E2E Tests (T0000015-T0000018):
    - End-to-end workflow testing
    - API integration testing
    - Security testing
    - Pipeline failure handling
    """
    
    def __init__(self):
        # Add parent directory to path for module imports
        test_dir = Path(__file__).parent
        parent_dir = str(test_dir.parent)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        
        self.test_results = {}
        self.test_scripts = self._discover_tests()
        
        # Test categories
        self.unit_tests = [
            "test_t00000001", "test_t00000002", "test_t00000003", "test_t00000004",
            "test_t00000005", "test_t00000006", "test_t00000007", "test_t00000008",
            "test_t00000009", "test_t00000010", "test_t00000011", "test_t00000012",
            "test_t00000013", "test_t00000014"
        ]
        
        self.integration_tests = [
            "test_t00000015", "test_t00000016", "test_t00000017", "test_t00000018"
        ]
        
        # Test metadata
        self.test_metadata = {
            "test_t00000001": {"name": "JDPM - JSON Data Processing Module Unit Test", "modules": ["JDPM"]},
            "test_t00000002": {"name": "TVM - Template Validation Module Unit Test", "modules": ["TVM"]},
            "test_t00000003": {"name": "BDM - Binary Data Module Unit Test", "modules": ["BDM"]},
            "test_t00000004": {"name": "DAM - Data Analysis Module Unit Test", "modules": ["DAM"]},
            "test_t00000005": {"name": "IPM - Input Processing Module Unit Test", "modules": ["IPM"]},
            "test_t00000006": {"name": "OPM - Output Processing Module Unit Test", "modules": ["OPM"]},
            "test_t00000007": {"name": "FIM - File Interface Module Unit Test", "modules": ["FIM"]},
            "test_t00000008": {"name": "ECM - External Control Module Unit Test", "modules": ["ECM"]},
            "test_t00000009": {"name": "ARM - API Request Module Unit Test", "modules": ["ARM"]},
            "test_t00000010": {"name": "CIM - Configuration Interface Module Unit Test", "modules": ["CIM"]},
            "test_t00000011": {"name": "EMM - Error Management Module Unit Test", "modules": ["EMM"]},
            "test_t00000012": {"name": "MSM - Monitoring System Module Unit Test", "modules": ["MSM"]},
            "test_t00000013": {"name": "BTM - Background Tasks Module Unit Test", "modules": ["BTM"]},
            "test_t00000014": {"name": "TMM - Test Management Module Unit Test", "modules": ["TMM"]},
            "test_t00000015": {"name": "API Test - Batch Processing Endpoint", "modules": ["ARM", "JDPM", "TVM", "BDM", "DAM", "OPM"]},
            "test_t00000016": {"name": "E2E Happy Path Scenario", "modules": ["IPM", "JDPM", "TVM", "BDM", "DAM", "OPM", "ARM"]},
            "test_t00000017": {"name": "E2E Pipeline Failure (Validation Stage)", "modules": ["IPM", "JDPM", "TVM"]},
            "test_t00000018": {"name": "Security Test - API Key Authentication", "modules": ["ARM", "IPM"]}
        }

    def _discover_tests(self) -> List[str]:
        """Discover all test_t000000XX.py files in the current directory."""
        test_dir = Path(__file__).parent
        return sorted([
            f.stem for f in test_dir.glob('test_t*.py')
            if f.is_file() and f.stem.startswith('test_t')
        ])

    async def _run_test_in_subprocess(self, test_script: str) -> dict:
        """Run a test script in a separate subprocess for isolation."""
        try:
            # Compose the command to run the test
            cmd = [
                sys.executable,
                "-c",
                (
                    f"import asyncio; "
                    f"import {test_script}; "
                    f"result = asyncio.run({test_script}.{test_script}()); "
                    f"import json; print(json.dumps(result, default=str))"
                )
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if proc.returncode == 0 and proc.stdout:
                try:
                    return json.loads(proc.stdout.strip())
                except Exception:
                    return {"success": False, "error": "Could not parse test output", "raw_output": proc.stdout}
            else:
                return {"success": False, "error": proc.stderr or "Test failed with no output"}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Test timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return results."""
        print("🚀 Starting JFA Modular Architecture Test Suite...")
        print(f"📋 Discovered {len(self.test_scripts)} test scripts")
        
        results = {}
        start_time = datetime.now()
        
        for test_script in self.test_scripts:
            try:
                print(f"🧪 Running {test_script} (isolated)...")
                test_start_time = datetime.now()
                result = await self._run_test_in_subprocess(test_script)
                test_end_time = datetime.now()
                execution_time = (test_end_time - test_start_time).total_seconds()
                result["execution_time"] = execution_time
                result["timestamp"] = test_end_time.isoformat()
                results[test_script] = result
                status = "✅ PASS" if result.get('success') else "❌ FAIL"
                print(f"   {status} - {execution_time:.2f}s")
                if not result.get('success'):
                    error_msg = result.get('message', result.get('error', 'Unknown error'))
                    print(f"   Error: {error_msg}")
            except Exception as e:
                print(f"❌ {test_script}: ERROR - {e}")
                results[test_script] = {
                    "success": False, 
                    "error": str(e),
                    "execution_time": 0,
                    "timestamp": datetime.now().isoformat()
                }
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        # Calculate statistics
        total_tests = len(results)
        passed_tests = sum(1 for r in results.values() if r.get('success'))
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        # Categorize results
        unit_results = {k: v for k, v in results.items() if k in self.unit_tests}
        integration_results = {k: v for k, v in results.items() if k in self.integration_tests}
        
        unit_passed = sum(1 for r in unit_results.values() if r.get('success'))
        integration_passed = sum(1 for r in integration_results.values() if r.get('success'))
        
        self.test_results = results
        
        print(f"\n📊 Test Summary:")
        print(f"   Total tests: {total_tests}")
        print(f"   Passed: {passed_tests}")
        print(f"   Failed: {failed_tests}")
        print(f"   Success rate: {success_rate:.1f}%")
        print(f"   Total execution time: {total_time:.2f}s")
        print(f"\n   Unit tests: {unit_passed}/{len(unit_results)} passed")
        print(f"   Integration tests: {integration_passed}/{len(integration_results)} passed")
        
        return {
            "success": failed_tests == 0,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": success_rate,
            "total_execution_time": total_time,
            "unit_tests": {
                "total": len(unit_results),
                "passed": unit_passed,
                "failed": len(unit_results) - unit_passed,
                "success_rate": (unit_passed / len(unit_results) * 100) if unit_results else 0,
                "results": unit_results
            },
            "integration_tests": {
                "total": len(integration_results),
                "passed": integration_passed,
                "failed": len(integration_results) - integration_passed,
                "success_rate": (integration_passed / len(integration_results) * 100) if integration_results else 0,
                "results": integration_results
            },
            "results": results,
            "timestamp": end_time.isoformat()
        }

    async def run_unit_tests(self) -> Dict[str, Any]:
        """Run only unit tests (isolated)."""
        print("🧪 Running JFA Unit Tests...")
        results = {}
        for test_script in self.unit_tests:
            if test_script in self.test_scripts:
                try:
                    result = await self._run_test_in_subprocess(test_script)
                    results[test_script] = result
                    status = "✅ PASS" if result.get('success') else "❌ FAIL"
                    print(f"   {test_script}: {status}")
                except Exception as e:
                    print(f"❌ {test_script}: ERROR - {e}")
                    results[test_script] = {"success": False, "error": str(e)}
        passed = sum(1 for r in results.values() if r.get('success'))
        failed = len(results) - passed
        return {
            "success": failed == 0,
            "total_tests": len(results),
            "passed_tests": passed,
            "failed_tests": failed,
            "success_rate": (passed / len(results) * 100) if results else 0,
            "results": results
        }

    async def run_integration_tests(self) -> Dict[str, Any]:
        """Run only integration tests (isolated)."""
        print("🧪 Running JFA Integration Tests...")
        results = {}
        for test_script in self.integration_tests:
            if test_script in self.test_scripts:
                try:
                    result = await self._run_test_in_subprocess(test_script)
                    results[test_script] = result
                    status = "✅ PASS" if result.get('success') else "❌ FAIL"
                    print(f"   {test_script}: {status}")
                except Exception as e:
                    print(f"❌ {test_script}: ERROR - {e}")
                    results[test_script] = {"success": False, "error": str(e)}
        passed = sum(1 for r in results.values() if r.get('success'))
        failed = len(results) - passed
        return {
            "success": failed == 0,
            "total_tests": len(results),
            "passed_tests": passed,
            "failed_tests": failed,
            "success_rate": (passed / len(results) * 100) if results else 0,
            "results": results
        }

    async def run_specific_test(self, test_name: str) -> Dict[str, Any]:
        """Run a specific test by name (isolated)."""
        if test_name not in self.test_scripts:
            return {"success": False, "error": f"Test {test_name} not found"}
        try:
            return await self._run_test_in_subprocess(test_name)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_test_metadata(self, test_name: str) -> Dict[str, Any]:
        """Get metadata for a specific test."""
        return self.test_metadata.get(test_name, {})

    def export_results(self, filename: str = None) -> str:
        """Export test results to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"jfa_test_results_{timestamp}.json"
        
        import json
        with open(filename, 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        return filename

async def main():
    """Main function to run the test suite."""
    test_suite = JFATestSuite()
    
    # Run all tests
    results = await test_suite.run_all_tests()
    
    # Export results
    export_file = test_suite.export_results()
    print(f"\n📄 Test results exported to: {export_file}")
    
    return results

if __name__ == "__main__":
    asyncio.run(main()) 