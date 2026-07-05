"""
RLA Modular Architecture Test Suite

This module contains all test cases for the RLA microservice modular architecture.
Tests are organized into Unit, Integration, E2E, and Security Tests.
"""

import asyncio
import importlib
import os
from pathlib import Path
from typing import Dict, Any, List

class RLATestSuite:
    def __init__(self):
        self.test_results = {}
        self.test_scripts = self._discover_tests()

    def _discover_tests(self) -> List[str]:
        # Discover all test_t000000XX.py files in the current directory
        test_dir = Path(__file__).parent
        return sorted([
            f.stem for f in test_dir.glob('test_t*.py')
            if f.is_file() and f.stem.startswith('test_t')
        ])

    async def run_all_tests(self) -> Dict[str, Any]:
        print("🚀 Starting RLA Modular Architecture Test Suite...")
        results = {}
        for test_script in self.test_scripts:
            try:
                mod = importlib.import_module(f".{{}}".format(test_script), package=__package__)
                test_func = getattr(mod, test_script)
                if asyncio.iscoroutinefunction(test_func):
                    result = await test_func()
                else:
                    result = test_func()
                results[test_script] = result
                print(f"✅ {test_script}: PASS" if result.get('success') else f"❌ {test_script}: FAIL")
            except Exception as e:
                results[test_script] = {"success": False, "error": str(e)}
                print(f"❌ {test_script}: ERROR - {e}")
        self.test_results = results
        return results

if __name__ == "__main__":
    suite = RLATestSuite()
    asyncio.run(suite.run_all_tests()) 