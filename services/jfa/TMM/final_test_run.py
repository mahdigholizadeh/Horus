#!/usr/bin/env python3
"""
Final test run to check the status of all JFA tests.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

async def run_final_test():
    """Run all tests and show final results."""
    from test_suite import JFATestSuite
    
    print("🚀 Running Final JFA Test Suite...")
    print("=" * 50)
    
    test_suite = JFATestSuite()
    
    # Run unit tests
    print("🧪 Running Unit Tests...")
    unit_results = await test_suite.run_unit_tests()
    
    print(f"\n📊 Unit Test Results:")
    print(f"   Total: {unit_results['total_tests']}")
    print(f"   Passed: {unit_results['passed_tests']}")
    print(f"   Failed: {unit_results['failed_tests']}")
    print(f"   Success Rate: {unit_results['success_rate']:.1f}%")
    
    # Show individual test results
    print(f"\n📋 Individual Test Results:")
    for test_name, result in unit_results['results'].items():
        status = "✅ PASS" if result.get('success') else "❌ FAIL"
        print(f"   {test_name}: {status}")
    
    # Run integration tests
    print(f"\n🧪 Running Integration Tests...")
    integration_results = await test_suite.run_integration_tests()
    
    print(f"\n📊 Integration Test Results:")
    print(f"   Total: {integration_results['total_tests']}")
    print(f"   Passed: {integration_results['passed_tests']}")
    print(f"   Failed: {integration_results['failed_tests']}")
    print(f"   Success Rate: {integration_results['success_rate']:.1f}%")
    
    # Show individual integration test results
    print(f"\n📋 Integration Test Results:")
    for test_name, result in integration_results['results'].items():
        status = "✅ PASS" if result.get('success') else "❌ FAIL"
        print(f"   {test_name}: {status}")
    
    # Overall summary
    total_tests = unit_results['total_tests'] + integration_results['total_tests']
    total_passed = unit_results['passed_tests'] + integration_results['passed_tests']
    total_failed = unit_results['failed_tests'] + integration_results['failed_tests']
    overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    print(f"\n🎯 Overall Summary:")
    print(f"   Total Tests: {total_tests}")
    print(f"   Passed: {total_passed}")
    print(f"   Failed: {total_failed}")
    print(f"   Overall Success Rate: {overall_success_rate:.1f}%")
    
    if overall_success_rate >= 90:
        print(f"🎉 Excellent! Test suite is working well!")
    elif overall_success_rate >= 70:
        print(f"👍 Good progress! Most tests are working.")
    elif overall_success_rate >= 50:
        print(f"⚠️  Moderate success. Some issues need attention.")
    else:
        print(f"❌ Significant issues need to be addressed.")
    
    return overall_success_rate

if __name__ == "__main__":
    success_rate = asyncio.run(run_final_test())
    sys.exit(0 if success_rate >= 70 else 1) 