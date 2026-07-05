#!/usr/bin/env python3
"""
Detailed Test Runner for OCM Test Scripts
Shows exactly which tests are failing
"""

import asyncio
import json
import sys
import os
import traceback
from pathlib import Path
from datetime import datetime

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

async def detailed_test_o00000050():
    """Run detailed test for O00000050 to see specific failures."""
    print("=== Detailed Test O00000050 ===")
    
    try:
        from test_o00000050 import test_o00000050
        result = await test_o00000050()
        
        print(f"Overall Result: {result['status']} ({result['pass_rate']:.1f}%)")
        print(f"Passed: {result['passed_tests']}/{result['total_tests']}")
        
        # Analyze each test category
        for category, tests in result['results'].items():
            passed = sum(tests)
            total = len(tests)
            rate = (passed / total) * 100 if total > 0 else 0
            print(f"\n{category}: {passed}/{total} ({rate:.1f}%)")
            
            # Show failed tests
            failed_indices = [i for i, test in enumerate(tests) if not test]
            if failed_indices:
                print(f"  Failed tests: {failed_indices}")
        
        return result
        
    except Exception as e:
        print(f"Test failed: {e}")
        traceback.print_exc()
        return None

async def detailed_test_o00000049():
    """Run detailed test for O00000049 to see specific failures."""
    print("=== Detailed Test O00000049 ===")
    
    try:
        from test_o00000049 import test_o00000049
        result = await test_o00000049()
        
        print(f"Overall Result: {result['status']} ({result['pass_rate']:.1f}%)")
        print(f"Passed: {result['passed_tests']}/{result['total_tests']}")
        
        # Analyze each test category
        for category, tests in result['results'].items():
            passed = sum(tests)
            total = len(tests)
            rate = (passed / total) * 100 if total > 0 else 0
            print(f"\n{category}: {passed}/{total} ({rate:.1f}%)")
            
            # Show failed tests
            failed_indices = [i for i, test in enumerate(tests) if not test]
            if failed_indices:
                print(f"  Failed tests: {failed_indices}")
        
        return result
        
    except Exception as e:
        print(f"Test failed: {e}")
        traceback.print_exc()
        return None

async def main():
    """Main detailed test function."""
    print("OCM Detailed Test Runner")
    print("=" * 50)
    
    # Run detailed tests
    result_49 = await detailed_test_o00000049()
    result_50 = await detailed_test_o00000050()
    
    print("\n" + "=" * 50)
    print("DETAILED SUMMARY")
    print("=" * 50)
    
    if result_49:
        print(f"O00000049: {result_49['status']} ({result_49['pass_rate']:.1f}%)")
    if result_50:
        print(f"O00000050: {result_50['status']} ({result_50['pass_rate']:.1f}%)")

if __name__ == "__main__":
    asyncio.run(main()) 