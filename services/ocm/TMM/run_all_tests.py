#!/usr/bin/env python3
"""
OCM Test Runner

This script runs all OCM tests and provides a comprehensive report.
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import test modules
from test_o00000001 import test_o00000001
from test_o00000002 import test_o00000002
from test_o00000003 import test_o00000003
from test_o00000004 import test_o00000004
from test_o00000005 import test_o00000005

async def run_all_tests():
    """Run all OCM tests and generate a comprehensive report."""
    
    print("=" * 80)
    print("OCM Test Suite Runner")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test definitions
    tests = [
        ("O00000001", "OCM Main Service Initialization", test_o00000001),
        ("O00000002", "OCM Main Service Shutdown", test_o00000002),
        ("O00000003", "OCM Main Configuration Management", test_o00000003),
        ("O00000004", "ECM CCU WebSocket Connection", test_o00000004),
        ("O00000005", "ECM Service Registration", test_o00000005),
    ]
    
    results = []
    total_start_time = time.time()
    
    for test_code, test_name, test_func in tests:
        print(f"Running {test_code}: {test_name}")
        print("-" * 60)
        
        start_time = time.time()
        try:
            result = await test_func()
            end_time = time.time()
            execution_time = end_time - start_time
            
            result['execution_time'] = execution_time
            results.append(result)
            
            # Print test result summary
            status = result.get('status', 'UNKNOWN')
            if status == 'PASSED':
                print(f"✅ {test_code}: PASSED")
            elif status == 'FAILED':
                success_rate = result.get('success_rate', 0)
                print(f"⚠️  {test_code}: FAILED ({success_rate:.1f}% success rate)")
            else:
                print(f"❌ {test_code}: ERROR")
                error = result.get('error', 'Unknown error')
                print(f"   Error: {error}")
            
            if 'total_tests' in result:
                passed = result.get('passed_tests', 0)
                total = result.get('total_tests', 0)
                print(f"   Tests: {passed}/{total} passed")
            
            print(f"   Time: {execution_time:.2f}s")
            print()
            
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            
            error_result = {
                "test_code": test_code,
                "test_name": test_name,
                "status": "ERROR",
                "error": f"Test execution failed: {str(e)}",
                "execution_time": execution_time,
                "timestamp": time.time()
            }
            results.append(error_result)
            
            print(f"❌ {test_code}: ERROR")
            print(f"   Error: {str(e)}")
            print(f"   Time: {execution_time:.2f}s")
            print()
    
    total_end_time = time.time()
    total_execution_time = total_end_time - total_start_time
    
    # Generate comprehensive report
    report = generate_report(results, total_execution_time)
    
    # Print summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total execution time: {total_execution_time:.2f}s")
    print(f"Tests run: {len(results)}")
    
    passed_tests = [r for r in results if r.get('status') == 'PASSED']
    failed_tests = [r for r in results if r.get('status') == 'FAILED']
    error_tests = [r for r in results if r.get('status') == 'ERROR']
    
    print(f"Passed: {len(passed_tests)}")
    print(f"Failed: {len(failed_tests)}")
    print(f"Errors: {len(error_tests)}")
    
    if failed_tests:
        print("\nFailed Tests:")
        for test in failed_tests:
            success_rate = test.get('success_rate', 0)
            print(f"  - {test['test_code']}: {success_rate:.1f}% success rate")
    
    if error_tests:
        print("\nError Tests:")
        for test in error_tests:
            print(f"  - {test['test_code']}: {test.get('error', 'Unknown error')}")
    
    # Calculate overall success rate
    total_tests_run = sum(r.get('total_tests', 0) for r in results if r.get('status') in ['PASSED', 'FAILED'])
    total_tests_passed = sum(r.get('passed_tests', 0) for r in results if r.get('status') in ['PASSED', 'FAILED'])
    
    if total_tests_run > 0:
        overall_success_rate = (total_tests_passed / total_tests_run) * 100
        print(f"\nOverall Success Rate: {overall_success_rate:.1f}%")
        
        if overall_success_rate >= 90:
            print("🎉 Excellent! All major functionality is working.")
        elif overall_success_rate >= 75:
            print("👍 Good! Most functionality is working with minor issues.")
        elif overall_success_rate >= 50:
            print("⚠️  Fair! Some functionality is working, needs attention.")
        else:
            print("❌ Poor! Major issues need to be addressed.")
    
    # Save detailed report
    report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nDetailed report saved to: {report_file}")
    
    return report

def generate_report(results: List[Dict[str, Any]], total_execution_time: float) -> Dict[str, Any]:
    """Generate a comprehensive test report."""
    
    # Calculate statistics
    total_tests_run = sum(r.get('total_tests', 0) for r in results if r.get('status') in ['PASSED', 'FAILED'])
    total_tests_passed = sum(r.get('passed_tests', 0) for r in results if r.get('status') in ['PASSED', 'FAILED'])
    total_tests_failed = sum(r.get('failed_tests', 0) for r in results if r.get('status') in ['PASSED', 'FAILED'])
    
    passed_tests = [r for r in results if r.get('status') == 'PASSED']
    failed_tests = [r for r in results if r.get('status') == 'FAILED']
    error_tests = [r for r in results if r.get('status') == 'ERROR']
    
    overall_success_rate = (total_tests_passed / total_tests_run * 100) if total_tests_run > 0 else 0
    
    report = {
        "test_suite": "OCM Microservice Test Suite",
        "timestamp": datetime.now().isoformat(),
        "total_execution_time": total_execution_time,
        "summary": {
            "total_tests_run": len(results),
            "passed_tests": len(passed_tests),
            "failed_tests": len(failed_tests),
            "error_tests": len(error_tests),
            "total_individual_tests": total_tests_run,
            "total_individual_passed": total_tests_passed,
            "total_individual_failed": total_tests_failed,
            "overall_success_rate": overall_success_rate
        },
        "test_results": results,
        "recommendations": generate_recommendations(results, overall_success_rate)
    }
    
    return report

def generate_recommendations(results: List[Dict[str, Any]], overall_success_rate: float) -> List[str]:
    """Generate recommendations based on test results."""
    
    recommendations = []
    
    # Overall recommendations
    if overall_success_rate >= 90:
        recommendations.append("Excellent test results! The OCM microservice is working well.")
        recommendations.append("Consider adding more edge case tests for robustness.")
    elif overall_success_rate >= 75:
        recommendations.append("Good test results with some areas for improvement.")
        recommendations.append("Focus on fixing the failed tests to improve reliability.")
    elif overall_success_rate >= 50:
        recommendations.append("Fair test results. Several issues need attention.")
        recommendations.append("Prioritize fixing critical functionality first.")
    else:
        recommendations.append("Poor test results. Major issues need immediate attention.")
        recommendations.append("Review the error tests and fix fundamental problems.")
    
    # Specific recommendations based on test results
    for result in results:
        test_code = result.get('test_code', '')
        status = result.get('status', '')
        
        if test_code == 'O00000002' and status == 'ERROR':
            recommendations.append("Fix PDF generation engine issues in OCM service shutdown test.")
        
        if test_code == 'O00000004' and result.get('success_rate', 0) < 60:
            recommendations.append("Improve WebSocket connection reliability in ECM module.")
        
        if status == 'ERROR':
            error = result.get('error', '')
            if 'PDF generation' in error:
                recommendations.append("Implement mock PDF generation engine for testing.")
            elif 'WebSocket' in error:
                recommendations.append("Improve WebSocket connection handling and error recovery.")
    
    return recommendations

if __name__ == "__main__":
    try:
        report = asyncio.run(run_all_tests())
        
        # Exit with appropriate code
        overall_success_rate = report['summary']['overall_success_rate']
        if overall_success_rate >= 75:
            sys.exit(0)  # Success
        else:
            sys.exit(1)  # Failure
            
    except KeyboardInterrupt:
        print("\nTest execution interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nTest runner failed: {e}")
        sys.exit(1) 