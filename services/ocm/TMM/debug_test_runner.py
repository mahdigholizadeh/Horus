#!/usr/bin/env python3
"""
Debug Test Runner for OCM Test Scripts
Helps identify and debug issues with test scripts
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

async def debug_test_imports():
    """Test if all required modules can be imported."""
    print("=== Testing Module Imports ===")
    
    try:
        print("Testing TDIM import...")
        from TDIM.tdim import TDInteractionModule, TDDataType, ValidationStatus, TDDataPacket
        print("✓ TDIM module imported successfully")
        
        print("Testing RCMIM import...")
        from RCMIM.rcmim import RCMInteractionModule, RCMResponseType, ResponseStatus, RCMResponse
        print("✓ RCMIM module imported successfully")
        
        print("Testing OCVM import...")
        from OCVM.ocvm import OutputCheckValidityModule, ValidationType, ValidationResult, Severity
        print("✓ OCVM module imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"✗ Unexpected error during import: {e}")
        traceback.print_exc()
        return False

async def debug_test_o00000048():
    """Debug test O00000048."""
    print("\n=== Debugging Test O00000048 ===")
    
    try:
        # Import the test function
        from test_o00000048 import test_o00000048
        
        print("✓ Test function imported successfully")
        
        # Run the test
        print("Running test...")
        result = await test_o00000048()
        
        print("✓ Test completed successfully")
        print(f"Result: {json.dumps(result, indent=2, default=str)}")
        
        return result
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        traceback.print_exc()
        return None

async def debug_test_o00000049():
    """Debug test O00000049."""
    print("\n=== Debugging Test O00000049 ===")
    
    try:
        # Import the test function
        from test_o00000049 import test_o00000049
        
        print("✓ Test function imported successfully")
        
        # Run the test
        print("Running test...")
        result = await test_o00000049()
        
        print("✓ Test completed successfully")
        print(f"Result: {json.dumps(result, indent=2, default=str)}")
        
        return result
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        traceback.print_exc()
        return None

async def debug_test_o00000050():
    """Debug test O00000050."""
    print("\n=== Debugging Test O00000050 ===")
    
    try:
        # Import the test function
        from test_o00000050 import test_o00000050
        
        print("✓ Test function imported successfully")
        
        # Run the test
        print("Running test...")
        result = await test_o00000050()
        
        print("✓ Test completed successfully")
        print(f"Result: {json.dumps(result, indent=2, default=str)}")
        
        return result
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        traceback.print_exc()
        return None

async def main():
    """Main debug function."""
    print("OCM Test Debug Runner")
    print("=" * 50)
    
    # Test imports first
    imports_ok = await debug_test_imports()
    
    if not imports_ok:
        print("\n✗ Module imports failed. Cannot proceed with tests.")
        return
    
    print("\n✓ All modules imported successfully. Proceeding with tests...")
    
    # Run all tests
    results = {}
    
    results['test_o00000048'] = await debug_test_o00000048()
    results['test_o00000049'] = await debug_test_o00000049()
    results['test_o00000050'] = await debug_test_o00000050()
    
    # Summary
    print("\n" + "=" * 50)
    print("DEBUG SUMMARY")
    print("=" * 50)
    
    for test_name, result in results.items():
        if result is None:
            print(f"✗ {test_name}: FAILED")
        else:
            status = result.get('status', 'UNKNOWN')
            pass_rate = result.get('pass_rate', 0)
            print(f"✓ {test_name}: {status} ({pass_rate:.1f}%)")
    
    print("\nDebug run completed.")

if __name__ == "__main__":
    asyncio.run(main()) 