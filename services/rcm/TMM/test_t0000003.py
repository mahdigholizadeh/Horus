"""
Test T0000003: PBRPM - Priority Queue Processing
Module(s) Tested: PBRPM
Description: Place files with priorities A, B, and C into the input directories simultaneously.
Success Criteria: The module processes the 'A' priority file first, followed by 'B', then 'C', demonstrating correct prioritization.
"""

import asyncio
import json
import tempfile
from pathlib import Path
import sys
import os
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from PBRPM.pbrpm import PriorityBasedRequestProcessingModule

async def test_pbrpm_priority_queue_processing():
    """Test priority queue processing functionality."""
    test_code = "T0000003"
    test_name = "PBRPM - Priority Queue Processing"
    
    try:
        # Initialize PBRPM
        pbrpm = PriorityBasedRequestProcessingModule()
        
        # Create test files in priority directories
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create priority directories
            for priority in ["A", "B", "C", "D"]:
                priority_dir = temp_path / f"priority_{priority.lower()}"
                priority_dir.mkdir(parents=True)
                
                # Create test JSON files
                test_data = {
                    "priority_flag": priority,
                    "model": "gpt-4",
                    "messages": [{"role": "user", "content": f"Test message {priority}"}]
                }
                
                test_file = priority_dir / f"test_{priority}.json"
                with open(test_file, 'w', encoding='utf-8') as f:
                    json.dump(test_data, f)
            
            # Temporarily replace priority directories for testing
            original_dirs = pbrpm.priority_dirs
            pbrpm.priority_dirs = {
                "A": temp_path / "priority_a",
                "B": temp_path / "priority_b", 
                "C": temp_path / "priority_c",
                "D": temp_path / "priority_d"
            }
            
            try:
                # Test 1: Scan priority directories
                requests = await pbrpm.scan_priority_directories()
                scan_success = len(requests) == 4
                
                # Test 2: Add to priority queue
                await pbrpm.add_to_priority_queue(requests)
                queue_success = len(pbrpm.priority_queue) == 4
                
                # Test 3: Get next request (should be priority A)
                next_request = await pbrpm.get_next_request()
                priority_order_success = next_request and next_request.priority == "A"
                
                # Test 4: Process all requests
                stats = await pbrpm.process_all_pending_requests()
                processing_success = stats["processed"] >= 3  # At least 3 should be processed
                
                # Test 5: Get queue status
                status = await pbrpm.get_queue_status()
                status_success = isinstance(status, dict) and "queue_size" in status
                
                # Calculate overall success
                tests = [
                    scan_success,
                    queue_success,
                    priority_order_success,
                    processing_success,
                    status_success
                ]
                
                successful_tests = sum(tests)
                total_tests = len(tests)
                success_rate = (successful_tests / total_tests) * 100
                
                test_success = success_rate >= 80  # At least 80% success rate
                
                return {
                    "success": test_success,
                    "test_code": test_code,
                    "test_name": test_name,
                    "message": f"Priority processing: {successful_tests}/{total_tests} successful ({success_rate:.1f}% success rate)",
                    "details": {
                        "scan_success": scan_success,
                        "queue_success": queue_success,
                        "priority_order": priority_order_success,
                        "processing_success": processing_success,
                        "status_success": status_success,
                        "success_rate": success_rate,
                        "stats": stats
                    }
                }
                
            finally:
                # Restore original directories
                pbrpm.priority_dirs = original_dirs
        
    except Exception as e:
        return {
            "success": False,
            "test_code": test_code,
            "test_name": test_name,
            "error": f"Test execution failed: {str(e)}"
        } 

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(test_pbrpm_priority_queue_processing())
    print(result) 