#!/usr/bin/env python3
"""
Debug test runner to show detailed error information.
"""

import asyncio
import sys
import traceback
from pathlib import Path

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

async def run_test_with_debug(test_name):
    """Run a specific test with detailed error reporting."""
    print(f"🧪 Running {test_name} with debug...")
    
    try:
        # Import the test module
        test_module = __import__(test_name)
        test_function = getattr(test_module, test_name)
        
        # Run the test
        result = await test_function()
        
        print(f"✅ {test_name}: PASS")
        return result
        
    except Exception as e:
        print(f"❌ {test_name}: FAIL")
        print(f"   Error: {e}")
        print(f"   Traceback:")
        traceback.print_exc()
        return None

async def main():
    """Run failing tests with debug."""
    failing_tests = [
        "test_t00000009",  # ARM
        "test_t00000010",  # CIM
        "test_t00000011",  # EMM
        "test_t00000012",  # MSM
        "test_t00000013"   # BTM
    ]
    
    results = []
    for test_name in failing_tests:
        result = await run_test_with_debug(test_name)
        results.append(result is not None)
        print()  # Empty line for readability
    
    print(f"📊 Debug Results: {sum(results)}/{len(results)} tests passed")

if __name__ == "__main__":
    asyncio.run(main())