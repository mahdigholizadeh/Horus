#!/usr/bin/env python3
"""
JFA Test Suite Runner

Simple script to run JFA tests with various options.
"""

import asyncio
import sys
import argparse
import signal
import os
from pathlib import Path
from test_suite import JFATestSuite

# Global variable to track if we need to clean up
cleanup_needed = False

def cleanup_ports():
    """Clean up any processes using test ports."""
    try:
        from cleanup_ports import cleanup_port
        print("🧹 Cleaning up test ports...")
        cleanup_port(8001)  # ARM API server
        cleanup_port(11491)  # CCU WebSocket server
    except ImportError:
        print("⚠️  Port cleanup script not found, continuing...")

def signal_handler(signum, frame):
    """Handle interrupt signals gracefully."""
    global cleanup_needed
    print("\n🛑 Received interrupt signal. Cleaning up...")
    cleanup_needed = True
    sys.exit(1)

async def main():
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    parser = argparse.ArgumentParser(
        description="JFA Test Suite Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                    # Run all tests
  python run_tests.py --unit             # Run only unit tests
  python run_tests.py --integration      # Run only integration tests
  python run_tests.py --test T00000001   # Run specific test
  python run_tests.py --verbose          # Run with verbose output
  python run_tests.py --export           # Export results to file
        """
    )
    
    parser.add_argument('--unit', action='store_true', 
                       help='Run only unit tests (T00000001-T0000014)')
    parser.add_argument('--integration', action='store_true', 
                       help='Run only integration tests (T0000015-T0000018)')
    parser.add_argument('--test', type=str, 
                       help='Run specific test (e.g., T00000001)')
    parser.add_argument('--verbose', action='store_true', 
                       help='Enable verbose output')
    parser.add_argument('--export', action='store_true', 
                       help='Export results to JSON file')
    parser.add_argument('--list', action='store_true', 
                       help='List all available tests')
    parser.add_argument('--timeout', type=int, default=300,
                       help='Timeout for test execution in seconds')
    parser.add_argument('--no-cleanup', action='store_true',
                       help='Skip port cleanup before running tests')
    
    args = parser.parse_args()
    
    # Setup logging if verbose
    if args.verbose:
        import logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Clean up ports unless explicitly disabled
    if not args.no_cleanup:
        cleanup_ports()
    
    test_suite = JFATestSuite()
    
    # List tests
    if args.list:
        print("📋 Available JFA Tests:")
        print("\nUnit Tests:")
        for test in test_suite.unit_tests:
            metadata = test_suite.get_test_metadata(test)
            print(f"  {test}: {metadata.get('name', 'Unknown')}")
        
        print("\nIntegration Tests:")
        for test in test_suite.integration_tests:
            metadata = test_suite.get_test_metadata(test)
            print(f"  {test}: {metadata.get('name', 'Unknown')}")
        return
    
    # Run specific test
    if args.test:
        test_name = f"test_{args.test.lower()}"
        print(f"🧪 Running specific test: {args.test}")
        
        try:
            # Set timeout for test execution
            result = await asyncio.wait_for(
                test_suite.run_specific_test(test_name),
                timeout=args.timeout
            )
            
            if result.get('success'):
                print(f"✅ {args.test}: PASS")
            else:
                print(f"❌ {args.test}: FAIL")
                print(f"   Error: {result.get('error', 'Unknown error')}")
            
            if args.export:
                import json
                from datetime import datetime
                filename = f"jfa_test_{args.test.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(filename, 'w') as f:
                    json.dump(result, f, indent=2, default=str)
                print(f"📄 Results exported to: {filename}")
            
        except asyncio.TimeoutError:
            print(f"⏰ {args.test}: TIMEOUT (exceeded {args.timeout}s)")
            sys.exit(1)
        except Exception as e:
            print(f"💥 {args.test}: ERROR - {e}")
            sys.exit(1)
        
        return
    
    # Run test categories
    try:
        if args.unit:
            print("🧪 Running JFA Unit Tests...")
            results = await asyncio.wait_for(
                test_suite.run_unit_tests(),
                timeout=args.timeout
            )
        elif args.integration:
            print("🧪 Running JFA Integration Tests...")
            results = await asyncio.wait_for(
                test_suite.run_integration_tests(),
                timeout=args.timeout
            )
        else:
            print("🧪 Running All JFA Tests...")
            results = await asyncio.wait_for(
                test_suite.run_all_tests(),
                timeout=args.timeout
            )
        
        # Print summary
        print(f"\n📊 Test Summary:")
        print(f"   Total tests: {results['total_tests']}")
        print(f"   Passed: {results['passed_tests']}")
        print(f"   Failed: {results['failed_tests']}")
        print(f"   Success rate: {results['success_rate']:.1f}%")
        
        if 'total_execution_time' in results:
            print(f"   Total execution time: {results['total_execution_time']:.2f}s")
        
        # Export results if requested
        if args.export:
            export_file = test_suite.export_results()
            print(f"\n📄 Test results exported to: {export_file}")
        
        # Exit with appropriate code
        sys.exit(0 if results['success'] else 1)
        
    except asyncio.TimeoutError:
        print(f"⏰ Test execution timed out (exceeded {args.timeout}s)")
        sys.exit(1)
    except Exception as e:
        print(f"💥 Test execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Test execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
        sys.exit(1) 