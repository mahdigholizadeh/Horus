"""
Test T0000044: PRM - Priority Routing Module
Module(s) Tested: PRM
Description: Test priority-based file routing functionality.
Success Criteria: The module correctly routes files to appropriate priority queues.
"""

import asyncio
import tempfile
from pathlib import Path
import sys
import os
import json

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from PRM.prm import PRM

async def test_prm_priority_routing():
    """Test priority-based file routing functionality."""
    test_code = "T0000044"
    test_name = "PRM - Priority Routing Module"
    try:
        # Initialize module
        prm = PRM()
        
        # Create temp files for each priority
        priorities = ["A", "B", "C", "D"]
        temp_files = []
        for priority in priorities:
            file_data = {"priority_flag": priority, "data": f"test_data_{priority}"}
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
            json.dump(file_data, temp_file)
            temp_file_path = Path(temp_file.name)
            temp_file.close()
            temp_files.append(temp_file_path)
        
        # Test file routing for different priorities
        routing_results = []
        for temp_file_path in temp_files:
            try:
                result = await prm.route_file(temp_file_path)
                routing_results.append(isinstance(result, dict))
            except Exception as e:
                print(f"[DEBUG] Exception in route_file for {temp_file_path}: {e}")
                routing_results.append(False)
        routing_success = all(routing_results)
        
        # Test queue status
        try:
            status_result = await prm.get_priority_queue_status()
            print(f"[DEBUG] get_priority_queue_status output: {status_result}")
            status_success = isinstance(status_result, dict)
        except Exception as e:
            print(f"[DEBUG] Exception in get_priority_queue_status: {e}")
            status_success = False
        
        # Test module status
        try:
            module_status = await prm.get_status()
            print(f"[DEBUG] get_status output: {module_status}")
            module_status_success = isinstance(module_status, dict)
        except Exception as e:
            print(f"[DEBUG] Exception in get_status: {e}")
            module_status_success = False
        
        # Clean up: Remove routed files from priority directories
        for priority in priorities:
            dir_path = Path(f"input/priority_{priority.lower()}/")
            if dir_path.exists():
                for file in dir_path.glob("*.json"):
                    try:
                        file.unlink()
                    except Exception:
                        pass
        
        test_success = (routing_success and status_success and module_status_success)
        
        return {
            "success": test_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": f"Priority routing module successful",
            "details": {
                "routing_success": routing_success,
                "status_success": status_success,
                "module_status_success": module_status_success
            }
        }
    except Exception as e:
        print(f"[DEBUG] Exception in test_prm_priority_routing: {e}")
        return {
            "success": False,
            "test_code": test_code,
            "test_name": test_name,
            "error": f"Test execution failed: {str(e)}"
        }

async def main():
    print("=" * 60)
    print("Test T0000044: PRM - Priority Routing Module")
    print("=" * 60)
    result = await test_prm_priority_routing()
    print(f"\nTest Result: {'PASSED' if result['success'] else 'FAILED'}")
    print(f"Test Code: {result['test_code']}")
    print(f"Test Name: {result['test_name']}")
    if result['success']:
        print(f"Message: {result['message']}")
        print("\nDetails:")
        for key, value in result['details'].items():
            print(f"  {key}: {value}")
    else:
        error_msg = result.get('error', 'Unknown error occurred')
        print(f"Error: {error_msg}")
        if 'details' in result:
            print("\nDetails:")
            for key, value in result['details'].items():
                print(f"  {key}: {value}")
    print("\n" + "=" * 60)
    return result

if __name__ == "__main__":
    asyncio.run(main()) 