"""
Test T0000007: MMM & DRM - Memory Spill-to-Disk & Restore
Module(s) Tested: MMM, DRM
Description: Test memory management and disk restoration with FIFO queue management.
Success Criteria: The module correctly spills data to disk and restores it when needed.
"""

import asyncio
import tempfile
from pathlib import Path
import sys
import os
import json
import time
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from MMM.mmm import MemoryManagementModule
from DRM.drm import DiskRestorationModule

async def test_mmm_drm_memory_spill_to_disk_and_restore():
    """Test memory management and disk restoration with FIFO queue."""
    test_code = "T0000007"
    test_name = "MMM & DRM - Memory Spill-to-Disk & Restore"
    try:
        print(f"Starting {test_name}...")
        
        # Initialize modules
        mmm = MemoryManagementModule()
        drm = DiskRestorationModule()
        
        print("Modules initialized successfully")
        
        # Configure MMM with 40% threshold
        await mmm.configure_thresholds(
            memory_threshold=40.0,
            process_threshold=35.0,
            critical_threshold=50.0,
            restore_threshold=30.0
        )
        print("MMM configured with 40% threshold")
        
        # Start MMM monitoring
        await mmm.start()
        print("MMM monitoring started")
        
        # Add some test requests to the queue (FIFO)
        test_requests = [
            {"id": "req_1", "data": {"key": "value1", "test": True}, "priority": "high"},
            {"id": "req_2", "data": {"key": "value2", "test": True}, "priority": "medium"},
            {"id": "req_3", "data": {"key": "value3", "test": True}, "priority": "low"},
            {"id": "req_4", "data": {"key": "value4", "test": True}, "priority": "high"},
            {"id": "req_5", "data": {"key": "value5", "test": True}, "priority": "medium"}
        ]
        
        print(f"Adding {len(test_requests)} test requests to queue...")
        request_ids = []
        for request in test_requests:
            req_id = mmm.add_request(request)
            request_ids.append(req_id)
            print(f"Added request {req_id}")
        
        # Check queue status
        queue_status = mmm.get_queue_status()
        print(f"Queue status: {queue_status}")
        
        # Test direct spill functionality
        print("Testing direct spill functionality...")
        test_data = {"key": "test_value", "test": True}
        spill_success = await mmm.spill_data("test_key", test_data)
        print(f"Direct spill result: {spill_success}")
        
        # Test disk restoration
        print("Testing disk restoration...")
        restore_success = drm.restore_file(Path("cache/test_key.spill"))
        print(f"Restore result: {restore_success}")
        
        # Test FIFO queue operations
        print("Testing FIFO queue operations...")
        oldest_request = mmm.get_oldest_request()
        if oldest_request:
            print(f"Oldest request: {oldest_request['id']}")
        
        # Test memory status
        memory_status = await mmm.get_memory_status()
        print(f"Memory status - System: {memory_status['current_usage']['system']['percent']:.1f}%")
        print(f"Memory status - Process: {memory_status['current_usage']['process']['percent']:.1f}%")
        
        # Test DRM status
        drm_status = drm.get_status()
        print(f"DRM status - Restored files: {drm_status['stats']['total_restored']}")
        
        # Stop MMM monitoring
        await mmm.stop()
        print("MMM monitoring stopped")
        
        # Determine test success
        test_success = (
            spill_success and 
            restore_success and 
            len(request_ids) == len(test_requests) and
            queue_status['size'] == len(test_requests)
        )
        
        result = {
            "success": test_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": f"Memory spill and restore successful with FIFO queue",
            "details": {
                "spill_success": spill_success,
                "restore_success": restore_success,
                "requests_added": len(request_ids),
                "queue_size": queue_status['size'],
                "memory_threshold": memory_status['thresholds']['memory_threshold'],
                "drm_restored_count": drm_status['stats']['total_restored']
            }
        }
        
        print(f"Test result: {result}")
        return result
        
    except Exception as e:
        error_result = {
            "success": False,
            "test_code": test_code,
            "test_name": test_name,
            "error": f"Test execution failed: {str(e)}"
        }
        print(f"Test failed: {error_result}")
        return error_result

async def test_mmm_drm_integration():
    """Test MMM and DRM integration with automatic restoration."""
    test_code = "T0000007_INTEGRATION"
    test_name = "MMM & DRM Integration Test"
    try:
        print(f"Starting {test_name}...")
        
        # Initialize modules
        mmm = MemoryManagementModule()
        drm = DiskRestorationModule()
        
        # Configure MMM
        await mmm.configure_thresholds(
            memory_threshold=40.0,
            process_threshold=35.0,
            critical_threshold=50.0,
            restore_threshold=30.0
        )
        
        # Set up DRM to work with MMM
        async def memory_status_callback():
            return await mmm.get_memory_status()
        
        drm.set_mmm_callback(memory_status_callback)
        drm.enable_auto_restoration(True)
        
        # Start both modules
        await mmm.start()
        await drm.start_monitoring()
        
        print("Both modules started and integrated")
        
        # Add some requests
        test_requests = [
            {"id": "int_req_1", "data": {"test": "integration_1"}},
            {"id": "int_req_2", "data": {"test": "integration_2"}},
            {"id": "int_req_3", "data": {"test": "integration_3"}}
        ]
        
        for request in test_requests:
            mmm.add_request(request)
        
        print(f"Added {len(test_requests)} integration test requests")
        
        # Wait a bit for processing
        await asyncio.sleep(2)
        
        # Check status
        mmm_status = await mmm.get_status()
        drm_status = drm.get_status()
        
        print(f"MMM status: {mmm_status['status']}")
        print(f"DRM status: Auto-restore enabled: {drm_status['auto_restore_enabled']}")
        
        # Stop modules
        await mmm.stop()
        await drm.stop_monitoring()
        
        # Wait a moment for modules to stop
        await asyncio.sleep(1)
        
        # Check status after stopping
        mmm_status = await mmm.get_status()
        drm_status = drm.get_status()
        
        integration_success = (
            mmm_status['status'] == 'inactive' and
            drm_status['auto_restore_enabled'] and
            drm_status['is_monitoring'] == False  # Should be stopped now
        )
        
        result = {
            "success": integration_success,
            "test_code": test_code,
            "test_name": test_name,
            "message": "MMM and DRM integration successful",
            "details": {
                "mmm_status": mmm_status['status'],
                "drm_auto_restore": drm_status['auto_restore_enabled'],
                "drm_monitoring": drm_status['is_monitoring']
            }
        }
        
        print(f"Integration test result: {result}")
        return result
        
    except Exception as e:
        error_result = {
            "success": False,
            "test_code": test_code,
            "test_name": test_name,
            "error": f"Integration test failed: {str(e)}"
        }
        print(f"Integration test failed: {error_result}")
        return error_result

async def main():
    """Run the tests."""
    print("=== MMM & DRM Test Suite ===")
    
    # Run basic functionality test
    print("\n1. Running basic functionality test...")
    result1 = await test_mmm_drm_memory_spill_to_disk_and_restore()
    
    # Run integration test
    print("\n2. Running integration test...")
    result2 = await test_mmm_drm_integration()
    
    # Overall results
    overall_success = result1["success"] and result2["success"]
    
    print(f"\n=== Test Results ===")
    print(f"Basic functionality test: {'PASS' if result1['success'] else 'FAIL'}")
    print(f"Integration test: {'PASS' if result2['success'] else 'FAIL'}")
    print(f"Overall result: {'PASS' if overall_success else 'FAIL'}")
    
    if not overall_success:
        print(f"\nDetailed results:")
        print(f"Test 1: {json.dumps(result1, indent=2)}")
        print(f"Test 2: {json.dumps(result2, indent=2)}")

if __name__ == "__main__":
    asyncio.run(main()) 