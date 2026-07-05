#!/usr/bin/env python3
"""
Run DCM Tests Script

This script runs the three DCM tests:
- test_o00000028: DCM Request Storage and Retrieval
- test_o00000029: DCM Report Tracking  
- test_o00000030: DCM Database Backup and Recovery
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

async def run_dcm_tests():
    """Run all DCM tests and display results."""
    
    print("=" * 80)
    print("DCM (Database Control Module) Tests")
    print("=" * 80)
    
    # Import test modules
    from test_o00000028 import test_o00000028
    from test_o00000029 import test_o00000029
    from test_o00000030 import test_o00000030
    
    tests = [
        ("test_o00000028", "DCM Request Storage and Retrieval", test_o00000028),
        ("test_o00000029", "DCM Report Tracking", test_o00000029),
        ("test_o00000030", "DCM Database Backup and Recovery", test_o00000030)
    ]
    
    results = []
    total_passed = 0
    total_tests = 0
    
    for test_id, test_name, test_func in tests:
        print(f"\nRunning {test_id}: {test_name}")
        print("-" * 60)
        
        try:
            result = await test_func()
            results.append(result)
            
            status = result.get("status", "UNKNOWN")
            pass_rate = result.get("success_rate", result.get("pass_rate", 0))
            passed_tests = result.get("passed_tests", 0)
            total_test_count = result.get("total_tests", 0)
            
            total_passed += passed_tests
            total_tests += total_test_count
            
            print(f"Status: {status}")
            print(f"Pass Rate: {pass_rate:.2f}%")
            print(f"Passed: {passed_tests}/{total_test_count}")
            
            if status == "PASSED":
                print("✓ Test PASSED")
            else:
                print("✗ Test FAILED")
                
        except Exception as e:
            print(f"Error running {test_id}: {e}")
            results.append({
                "test_id": test_id,
                "test_name": test_name,
                "status": "ERROR",
                "error": str(e)
            })
    
    # Summary
    print("\n" + "=" * 80)
    print("DCM TESTS SUMMARY")
    print("=" * 80)
    
    overall_pass_rate = (total_passed / total_tests) * 100 if total_tests > 0 else 0
    overall_status = "PASSED" if overall_pass_rate >= 90 else "FAILED"
    
    print(f"Overall Status: {overall_status}")
    print(f"Overall Pass Rate: {overall_pass_rate:.2f}%")
    print(f"Total Tests Passed: {total_passed}/{total_tests}")
    
    print("\nIndividual Test Results:")
    for result in results:
        test_id = result.get("test_code", result.get("test_id", "UNKNOWN"))
        status = result.get("status", "UNKNOWN")
        pass_rate = result.get("success_rate", result.get("pass_rate", 0))
        print(f"  {test_id}: {status} ({pass_rate:.2f}%)")
    
    print("\n" + "=" * 80)
    
    return overall_status == "PASSED"

if __name__ == "__main__":
    success = asyncio.run(run_dcm_tests())
    sys.exit(0 if success else 1) 