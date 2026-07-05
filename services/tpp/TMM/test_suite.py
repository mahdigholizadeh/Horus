"""
TPP Modular Architecture Test Suite

This module contains all test cases for the TPP microservice modular architecture.
Tests are organized into Unit, Integration, E2E, and Security Tests.
"""

import asyncio
import importlib
import os
from pathlib import Path
from typing import Dict, Any, List

class TPPTestSuite:
    def __init__(self):
        self.test_results = {}
        self.test_scripts = self._discover_tests()

    def _discover_tests(self) -> List[str]:
        # Discover all test_t000000XX.py files in the current directory, except test_t00000001_simple.py
        test_dir = Path(__file__).parent
        return sorted([
            f.stem for f in test_dir.glob('test_t*.py')
            if f.is_file() and f.stem.startswith('test_t') and f.stem != 'test_t00000001_simple'
        ])

    async def run_all_tests(self) -> Dict[str, Any]:
        print("🚀 Starting TPP Modular Architecture Test Suite...")
        results = {}
        for test_script in self.test_scripts:
            try:
                # Use exec to run the test file directly
                test_file_path = Path(__file__).parent / f"{test_script}.py"
                if test_file_path.exists():
                    # Read and execute the test file
                    with open(test_file_path, 'r', encoding='utf-8') as f:
                        test_code = f.read()
                    
                    # Create a namespace for the test
                    test_namespace = {}
                    exec(test_code, test_namespace)
                    
                    # Get the test function
                    test_func = test_namespace.get(test_script)
                    if test_func and asyncio.iscoroutinefunction(test_func):
                        result = await test_func()
                    elif test_func:
                        result = test_func()
                    else:
                        result = {"success": False, "error": f"Test function {test_script} not found"}
                    
                    results[test_script] = result
                    print(f"✅ {test_script}: PASS" if result.get('success') else f"❌ {test_script}: FAIL")
                else:
                    results[test_script] = {"success": False, "error": f"Test file {test_script}.py not found"}
                    print(f"❌ {test_script}: ERROR - File not found")
            except Exception as e:
                results[test_script] = {"success": False, "error": str(e)}
                print(f"❌ {test_script}: ERROR - {e}")
        self.test_results = results
        return results

if __name__ == "__main__":
    suite = TPPTestSuite()
    asyncio.run(suite.run_all_tests()) 