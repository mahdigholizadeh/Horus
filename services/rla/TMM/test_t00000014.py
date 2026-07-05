"""
Test T00000014: TMM (Test Management Module) Unit Test
Module(s) Tested: TMM
Description: Validates that the testing and validation framework itself is operational.
Success Criteria: TMM discovers and runs all designated unit tests and reports results correctly.
"""

import asyncio
import importlib
import os
import sys
from pathlib import Path
from typing import Dict, Any, List

async def test_t00000014():
    test_code = "T00000014"
    test_name = "TMM - Test Harness Validation"
    results = []
    
    # Add parent directory to Python path for module imports
    current_dir = Path(__file__).parent
    parent_dir = current_dir.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    
    # Custom test discovery that excludes test_t00000014.py to prevent recursion
    test_scripts = sorted([
        f.stem for f in current_dir.glob('test_t*.py')
        if f.is_file() and f.stem.startswith('test_t') and f.stem != 'test_t00000014'
    ])
    
    print(f"🚀 Running TMM test harness validation with {len(test_scripts)} tests...")
    test_results = {}
    
    for test_script in test_scripts:
        try:
            # Use absolute import
            mod = importlib.import_module(test_script)
            test_func = getattr(mod, test_script)
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            test_results[test_script] = result
            print(f"✅ {test_script}: PASS" if result.get('success') else f"❌ {test_script}: FAIL")
        except Exception as e:
            test_results[test_script] = {"success": False, "error": str(e)}
            print(f"❌ {test_script}: ERROR - {e}")
    
    # Check that all tests ran and results are present
    all_present = all(isinstance(res, dict) and "success" in res for res in test_results.values())
    results.append(all_present)
    
    success = all(results)
    return {
        "success": success,
        "test_code": test_code,
        "test_name": test_name,
        "message": "TMM test harness scenario passed" if success else "TMM test harness scenario failed",
        "details": {
            "steps": results,
            "test_results": test_results,
            "tests_run": len(test_scripts)
        }
    }

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(test_t00000014())
    import pprint
    pprint.pprint(result) 