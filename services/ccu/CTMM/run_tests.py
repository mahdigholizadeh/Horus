"""
CCU CTMM Test Runner
Executes all 40 test cases for CCU microservice modules

Test Coverage:
- Unit Tests (1-20): All CCU internal modules
- Integration Tests (21-33): Workflow and system integration  
- Advanced Tests (34-40): Performance, resilience, and E2E validation

Usage:
    python run_tests.py [--test-number N] [--module MODULE] [--verbose] [--category CATEGORY]
"""

import asyncio
import sys
import time
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ctmm_test_results.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Test definitions
TESTS = {
    # SEM Module Tests
    "test_t00000001": {
        "name": "SEM Pilot Checklist Complete Execution",
        "module": "SEM",
        "description": "Verify complete SEM pilot checklist execution with all phases"
    },
    "test_t00000002": {
        "name": "SEM Service Activation Sequence", 
        "module": "SEM",
        "description": "Test controlled sequential startup of all 7 microservices"
    },
    "test_t00000003": {
        "name": "SEM Configuration Validation",
        "module": "SEM", 
        "description": "Test comprehensive configuration validation during startup"
    },
    "test_t00000004": {
        "name": "SEM Request Gateway Blocking",
        "module": "SEM",
        "description": "Test RLA input gateway blocking during startup/restart"
    },
    "test_t00000005": {
        "name": "SEM Systemd Integration",
        "module": "SEM",
        "description": "Test systemd service integration and management"
    },
    
    # PMM Module Tests
    "test_t00000006": {
        "name": "PMM Installation Root Detection",
        "module": "PMM",
        "description": "Test automatic installation root directory detection"
    },
    "test_t00000007": {
        "name": "PMM Service Path Distribution",
        "module": "PMM",
        "description": "Test path distribution to all dependent microservices"
    },
    "test_t00000008": {
        "name": "PMM Environment Management",
        "module": "PMM",
        "description": "Test environment switching and configuration management"
    },
    
    # RTM Module Tests
    "test_t00000009": {
        "name": "RTM Request Workflow Orchestration",
        "module": "RTM",
        "description": "Test end-to-end request workflow management through all stages"
    },
    "test_t00000010": {
        "name": "RTM Concurrent Request Management",
        "module": "RTM",
        "description": "Test management of multiple concurrent requests (10 max)"
    },
    
    # Integration & Workflow Tests (21-33)
    "test_t00000021": {
        "name": "CCU Complete WebSocket Startup Workflow",
        "module": "SEM",
        "description": "Test complete CCU startup workflow with three-phase WebSocket orchestration",
        "category": "integration",
        "priority": "critical"
    },
    "test_t00000022": {
        "name": "End-to-End WebSocket Request Processing Workflow",
        "module": "RTM",
        "description": "Test complete request processing through WebSocket communication from RLA to OCM",
        "category": "integration", 
        "priority": "critical"
    },
    "test_t00000023": {
        "name": "Multi-Service Health Monitoring Integration",
        "module": "MSMM",
        "description": "Test integrated health monitoring across all dependent services",
        "category": "integration",
        "priority": "high"
    },
    "test_t00000024": {
        "name": "Configuration Management Integration", 
        "module": "SMM",
        "description": "Test integrated configuration management across all services",
        "category": "integration",
        "priority": "high"
    },
    "test_t00000025": {
        "name": "Error Management Integration",
        "module": "CEIM", 
        "description": "Test integrated error management across all services",
        "category": "integration",
        "priority": "high"
    },
    "test_t00000026": {
        "name": "SEM Restart Workflow with Request Blocking",
        "module": "SEM",
        "description": "Test SEM restart workflow with request gateway blocking",
        "category": "integration",
        "priority": "high"
    },
    "test_t00000027": {
        "name": "Resource Monitoring and Backpressure Workflow",
        "module": "SRMM",
        "description": "Test integrated resource monitoring with backpressure management",
        "category": "integration",
        "priority": "medium"
    },
    "test_t00000028": {
        "name": "Certificate Management and Distribution Workflow",
        "module": "PMM",
        "description": "Test certificate management and distribution to all services",
        "category": "integration",
        "priority": "medium"
    },
    "test_t00000029": {
        "name": "API Key Security and Distribution Workflow",
        "module": "PMM",
        "description": "Test secure API key management and distribution", 
        "category": "integration",
        "priority": "medium"
    },
    "test_t00000030": {
        "name": "Database Backup and Recovery Workflow",
        "module": "PMM",
        "description": "Test automated database backup and recovery procedures",
        "category": "integration",
        "priority": "medium"
    },
    "test_t00000031": {
        "name": "Concurrent Request Processing Stress Test",
        "module": "RTM",
        "description": "Test CCU performance with maximum concurrent requests (10)",
        "category": "stress",
        "priority": "high"
    },
    "test_t00000032": {
        "name": "SEM Startup Performance Test",
        "module": "SEM",
        "description": "Test SEM pilot checklist performance under various conditions",
        "category": "performance",
        "priority": "medium"
    },
    "test_t00000033": {
        "name": "Resource Monitoring Performance Test",
        "module": "SRMM",
        "description": "Test resource monitoring performance under high load",
        "category": "performance", 
        "priority": "medium"
    },
    
    # Advanced Integration Tests (34-40)
    "test_t00000034": {
        "name": "Dashboard Performance and Scalability Test",
        "module": "GMM",
        "description": "Test web dashboard performance under high user load",
        "category": "performance",
        "priority": "high"
    },
    "test_t00000035": {
        "name": "WebSocket Communication Resilience and Recovery Test", 
        "module": "Interaction_Modules",
        "description": "Test WebSocket communication resilience and automatic recovery",
        "category": "resilience",
        "priority": "critical"
    },
    "test_t00000036": {
        "name": "Service Failure Recovery Integration Test",
        "module": "MSMM", 
        "description": "Test integrated recovery from service failures",
        "category": "integration",
        "priority": "critical"
    },
    "test_t00000037": {
        "name": "Configuration Change and Rollback Test",
        "module": "SMM",
        "description": "Test configuration change management with rollback capabilities", 
        "category": "integration",
        "priority": "high"
    },
    "test_t00000038": {
        "name": "Network Communication Resilience Test",
        "module": "Network_Layer",
        "description": "Test network communication resilience and recovery",
        "category": "resilience", 
        "priority": "high"
    },
    "test_t00000039": {
        "name": "Data Integrity and Consistency Test",
        "module": "Data_Management", 
        "description": "Test data integrity and consistency across system operations",
        "category": "integration",
        "priority": "critical"
    },
    "test_t00000040": {
        "name": "End-to-End System Validation Test",
        "module": "System_Integration",
        "description": "Comprehensive end-to-end system validation",
        "category": "e2e",
        "priority": "critical"
    }
}

async def run_single_test(test_name: str, verbose: bool = False) -> Dict[str, Any]:
    """Run a single test and return results."""
    try:
        # Import and run the test
        test_module = __import__(test_name)
        test_function = getattr(test_module, test_name)
        
        if verbose:
            logging.info(f"🚀 Starting {test_name}: {TESTS[test_name]['name']}")
        
        start_time = time.time()
        result = await test_function()
        end_time = time.time()
        
        result['execution_time'] = end_time - start_time
        
        if verbose:
            if result['success']:
                logging.info(f"✅ {test_name} completed successfully")
            else:
                logging.error(f"❌ {test_name} failed")
        
        return result
        
    except Exception as e:
        logging.error(f"Failed to run {test_name}: {e}")
        return {
            "test_code": test_name,
            "test_name": TESTS.get(test_name, {}).get("name", "Unknown Test"),
            "success": False,
            "error": str(e),
            "execution_time": 0.0
        }

async def run_all_tests(verbose: bool = False) -> Dict[str, Any]:
    """Run all tests and return comprehensive results."""
    logging.info("🧪 Starting CCU CTMM Test Suite")
    logging.info(f"📅 Test run started at: {datetime.now()}")
    
    results = {}
    total_start_time = time.time()
    
    for test_name in TESTS.keys():
        logging.info(f"\n{'='*60}")
        logging.info(f"Running {test_name}: {TESTS[test_name]['name']}")
        logging.info(f"Module: {TESTS[test_name]['module']}")
        logging.info(f"Description: {TESTS[test_name]['description']}")
        logging.info(f"{'='*60}")
        
        result = await run_single_test(test_name, verbose)
        results[test_name] = result
        
        # Add delay between tests to avoid resource conflicts
        await asyncio.sleep(1)
    
    total_end_time = time.time()
    total_duration = total_end_time - total_start_time
    
    # Calculate summary statistics
    total_tests = len(results)
    passed_tests = sum(1 for r in results.values() if r.get('success', False))
    failed_tests = total_tests - passed_tests
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    # Module-wise statistics
    module_stats = {}
    for test_name, result in results.items():
        module = TESTS[test_name]['module']
        if module not in module_stats:
            module_stats[module] = {'total': 0, 'passed': 0, 'failed': 0}
        
        module_stats[module]['total'] += 1
        if result.get('success', False):
            module_stats[module]['passed'] += 1
        else:
            module_stats[module]['failed'] += 1
    
    summary = {
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "success_rate": success_rate,
        "total_duration": total_duration,
        "module_stats": module_stats,
        "results": results,
        "timestamp": datetime.now().isoformat()
    }
    
    return summary

def print_summary(summary: Dict[str, Any]):
    """Print comprehensive test summary."""
    print("\n" + "="*80)
    print("🧪 CCU CTMM TEST SUITE RESULTS")
    print("="*80)
    print(f"📅 Test Run: {summary['timestamp']}")
    print(f"⏱️  Total Duration: {summary['total_duration']:.2f}s")
    print(f"📊 Overall Results: {summary['passed_tests']}/{summary['total_tests']} tests passed")
    print(f"📈 Success Rate: {summary['success_rate']:.2f}%")
    
    print("\n📋 Module-wise Results:")
    for module, stats in summary['module_stats'].items():
        module_success_rate = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
        status = "✅" if stats['failed'] == 0 else "⚠️" if stats['passed'] > 0 else "❌"
        print(f"   {status} {module}: {stats['passed']}/{stats['total']} ({module_success_rate:.1f}%)")
    
    print("\n📝 Detailed Results:")
    for test_name, result in summary['results'].items():
        status = "✅" if result.get('success', False) else "❌"
        test_info = TESTS[test_name]
        print(f"   {status} {test_name}: {test_info['name']}")
        print(f"      Module: {test_info['module']}")
        print(f"      Duration: {result.get('execution_time', 0):.2f}s")
        
        if not result.get('success', False) and 'error' in result:
            print(f"      Error: {result['error']}")
        
        if 'passed_tests' in result and 'total_tests' in result:
            print(f"      Tests: {result['passed_tests']}/{result['total_tests']} passed")
    
    print("\n" + "="*80)
    
    # Overall status
    if summary['success_rate'] >= 90:
        print("🎉 EXCELLENT: All tests passed successfully!")
    elif summary['success_rate'] >= 70:
        print("✅ GOOD: Most tests passed with minor issues")
    elif summary['success_rate'] >= 50:
        print("⚠️  FAIR: Some tests failed, review needed")
    else:
        print("❌ POOR: Many tests failed, immediate attention required")
    
    print("="*80)

async def main():
    """Main function to run tests based on command line arguments."""
    parser = argparse.ArgumentParser(description="CCU CTMM Test Runner")
    parser.add_argument("--test-number", type=str, help="Run specific test (e.g., test_t00000001)")
    parser.add_argument("--module", type=str, choices=["SEM", "PMM", "RTM", "GMM", "Interaction_Modules", "MSMM", "SMM", "Network_Layer", "Data_Management", "System_Integration"], help="Run tests for specific module")
    parser.add_argument("--category", type=str, choices=["performance", "resilience", "integration", "e2e", "stress"], help="Run tests for specific category")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--list", action="store_true", help="List all available tests")
    
    args = parser.parse_args()
    
    if args.list:
        print("Available Tests:")
        for test_name, test_info in TESTS.items():
            print(f"  {test_name}: {test_info['name']} ({test_info['module']})")
        return
    
    if args.test_number:
        if args.test_number not in TESTS:
            print(f"Error: Test {args.test_number} not found")
            return
        
        logging.info(f"Running single test: {args.test_number}")
        result = await run_single_test(args.test_number, args.verbose)
        print_summary({
            "total_tests": 1,
            "passed_tests": 1 if result.get('success', False) else 0,
            "failed_tests": 0 if result.get('success', False) else 1,
            "success_rate": 100 if result.get('success', False) else 0,
            "total_duration": result.get('execution_time', 0),
            "module_stats": {TESTS[args.test_number]['module']: {'total': 1, 'passed': 1 if result.get('success', False) else 0, 'failed': 0 if result.get('success', False) else 1}},
            "results": {args.test_number: result},
            "timestamp": datetime.now().isoformat()
        })
        
    elif args.module:
        module_tests = {name: info for name, info in TESTS.items() if info['module'] == args.module}
        logging.info(f"Running tests for module: {args.module}")
        
        results = {}
        for test_name in module_tests.keys():
            result = await run_single_test(test_name, args.verbose)
            results[test_name] = result
            await asyncio.sleep(1)
        
        passed_tests = sum(1 for r in results.values() if r.get('success', False))
        total_tests = len(results)
        
        summary = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            "total_duration": sum(r.get('execution_time', 0) for r in results.values()),
            "module_stats": {args.module: {'total': total_tests, 'passed': passed_tests, 'failed': total_tests - passed_tests}},
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
        
        print_summary(summary)
        
    elif args.category:
        category_tests = {name: info for name, info in TESTS.items() if info.get('category') == args.category}
        logging.info(f"Running tests for category: {args.category}")
        
        results = {}
        for test_name in category_tests.keys():
            result = await run_single_test(test_name, args.verbose)
            results[test_name] = result
            await asyncio.sleep(1)
        
        passed_tests = sum(1 for r in results.values() if r.get('success', False))
        total_tests = len(results)
        
        summary = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            "total_duration": sum(r.get('execution_time', 0) for r in results.values()),
            "module_stats": {f"Category_{args.category}": {'total': total_tests, 'passed': passed_tests, 'failed': total_tests - passed_tests}},
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
        
        print_summary(summary)
        
    else:
        # Run all tests
        summary = await run_all_tests(args.verbose)
        print_summary(summary)

if __name__ == "__main__":
    asyncio.run(main()) 