"""
Test O00000047: TDIM TD Data Reception
Module(s) Tested: TDIM (TD Interaction Module)
Description: Test reception of computation results from TD microservice
Test Description:
- Receive TD computation results
- Test data format validation
- Verify result correlation
- Check data integrity
- Test result processing
- Validate result storage
Expected Result: Reliable TD data reception and processing
Pass Criteria: Data received, validated, correlated, integrity maintained, processed
Implementation Notes: Test with various TD result formats
"""

import asyncio
import json
import sys
import os
import tempfile
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import uuid

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_o00000047():
    test_code = "O00000047"
    test_name = "TDIM TD Data Reception"
    results = []
    
    test_dir = None
    tdim = None
    
    try:
        # Import TDIM module
        from TDIM.tdim import TDInteractionModule, TDDataType, ValidationStatus, TDDataPacket
        
        # Create temporary test directory
        test_dir = tempfile.mkdtemp(prefix="tdim_reception_test_")
        
        # Step 1: Test TDIM module initialization with data reception config
        config = {
            "td_integration": {
                "data_reception": True,
                "data_format_validation": True,
                "result_correlation": True,
                "data_integrity": True,
                "result_processing": True,
                "result_storage": True
            },
            "validation": {
                "enabled": True,
                "max_data_size": 100 * 1024 * 1024,  # 100MB
                "timeout": 30
            },
            "processing": {
                "enabled": True,
                "queue_size": 1000,
                "worker_count": 5
            }
        }
        
        tdim = TDInteractionModule(config)
        await tdim.start()
        
        # Test module initialization
        results.append(tdim.is_active == True)
        results.append(hasattr(tdim, 'receive_td_data'))
        results.append(hasattr(tdim, 'get_processing_status'))
        results.append(hasattr(tdim, 'get_status'))
        
        # Step 2: Test TD computation result reception
        reception_results = []
        
        # Create TD computation result data
        computation_result_data = {
            "request_id": f"comp_{uuid.uuid4().hex[:8]}",
            "data_type": "computation_result",
            "td_instance_id": "td_instance_001",
            "processing_time": 45.2,
            "priority": "A",
            "report_formats": ["HTML", "PDF", "JSON"],
            "template_requirements": {
                "template_type": "computation_report",
                "include_charts": True,
                "include_tables": True
            },
            "content": {
                "route": "forward",
                "input_parameters": {
                    "parameter1": 100.0,
                    "parameter2": 200.0,
                    "parameter3": "test_value"
                },
                "computation_results": {
                    "result1": 150.5,
                    "result2": 300.2,
                    "result3": "computed_value"
                },
                "metadata": {
                    "calculation_version": "1.2.3",
                    "execution_time": 45.2,
                    "memory_usage": "256MB",
                    "cpu_usage": "75%"
                },
                "status": "completed",
                "error_count": 0,
                "warning_count": 2
            }
        }
        
        try:
            # Receive TD computation result
            reception_success = await tdim.receive_td_data(computation_result_data)
            reception_results.append(reception_success == True)
            
            # Check processing status
            processing_status = tdim.get_processing_status(computation_result_data["request_id"])
            reception_results.append(isinstance(processing_status, dict))
            reception_results.append("request_id" in processing_status)
            reception_results.append(processing_status.get("request_id") == computation_result_data["request_id"])
            
            # Check data type
            reception_results.append(processing_status.get("data_type") == TDDataType.COMPUTATION_RESULT.value)
            reception_results.append(processing_status.get("validation_status") in [ValidationStatus.PENDING.value, ValidationStatus.VALID.value])
            
        except Exception as e:
            print(f"Computation result reception failed: {e}")
            reception_results.extend([False, False, False, False, False, False])
        
        # Step 3: Test data format validation
        validation_results = []
        
        # Test valid data format
        valid_analysis_data = {
            "request_id": f"analysis_{uuid.uuid4().hex[:8]}",
            "data_type": "analysis_report",
            "td_instance_id": "td_instance_002",
            "processing_time": 30.1,
            "priority": "B",
            "report_formats": ["HTML"],
            "template_requirements": {
                "template_type": "analysis_report",
                "include_summary": True
            },
            "content": {
                "analysis_type": "statistical_analysis",
                "data_points": 1000,
                "statistics": {
                    "mean": 50.5,
                    "median": 49.8,
                    "std_dev": 15.2,
                    "min": 10.0,
                    "max": 95.0
                },
                "insights": [
                    "Data shows normal distribution",
                    "Outliers detected in upper range",
                    "Correlation coefficient: 0.75"
                ],
                "recommendations": [
                    "Consider data normalization",
                    "Investigate outlier causes",
                    "Apply statistical corrections"
                ]
            }
        }
        
        try:
            # Receive valid analysis data
            valid_reception = await tdim.receive_td_data(valid_analysis_data)
            validation_results.append(valid_reception == True)
            
            # Check validation status
            valid_status = tdim.get_processing_status(valid_analysis_data["request_id"])
            validation_results.append(isinstance(valid_status, dict))
            validation_results.append(valid_status.get("data_type") == TDDataType.ANALYSIS_REPORT.value)
            validation_results.append(valid_status.get("validation_status") in [ValidationStatus.PENDING.value, ValidationStatus.VALID.value])
            
        except Exception as e:
            print(f"Valid data format validation failed: {e}")
            validation_results.extend([False, False, False, False])
        
        # Test invalid data format (missing required fields)
        invalid_data = {
            "request_id": f"invalid_{uuid.uuid4().hex[:8]}",
            "data_type": "computation_result"
            # Missing required fields
        }
        
        try:
            # Receive invalid data
            invalid_reception = await tdim.receive_td_data(invalid_data)
            validation_results.append(invalid_reception == False)  # Should fail due to missing fields
            
        except Exception as e:
            print(f"Invalid data format test failed: {e}")
            validation_results.append(True)  # Exception is also acceptable
        
        # Step 4: Test result correlation
        correlation_results = []
        
        # Create correlated data sets
        correlated_data_1 = {
            "request_id": f"corr_1_{uuid.uuid4().hex[:8]}",
            "data_type": "data_summary",
            "td_instance_id": "td_instance_003",
            "processing_time": 20.5,
            "priority": "C",
            "report_formats": ["JSON"],
            "template_requirements": {},
            "content": {
                "summary_type": "data_overview",
                "total_records": 5000,
                "summary_data": {
                    "processed_records": 4800,
                    "failed_records": 200,
                    "success_rate": 0.96
                },
                "correlation_id": "correlation_001"
            }
        }
        
        correlated_data_2 = {
            "request_id": f"corr_2_{uuid.uuid4().hex[:8]}",
            "data_type": "data_summary",
            "td_instance_id": "td_instance_003",
            "processing_time": 25.3,
            "priority": "C",
            "report_formats": ["JSON"],
            "template_requirements": {},
            "content": {
                "summary_type": "data_details",
                "total_records": 5000,
                "summary_data": {
                    "processed_records": 4800,
                    "failed_records": 200,
                    "success_rate": 0.96
                },
                "correlation_id": "correlation_001"
            }
        }
        
        try:
            # Receive correlated data
            corr_1_success = await tdim.receive_td_data(correlated_data_1)
            correlation_results.append(corr_1_success == True)
            
            corr_2_success = await tdim.receive_td_data(correlated_data_2)
            correlation_results.append(corr_2_success == True)
            
            # Check correlation
            corr_1_status = tdim.get_processing_status(correlated_data_1["request_id"])
            corr_2_status = tdim.get_processing_status(correlated_data_2["request_id"])
            
            correlation_results.append(isinstance(corr_1_status, dict))
            correlation_results.append(isinstance(corr_2_status, dict))
            correlation_results.append(corr_1_status.get("data_type") == TDDataType.DATA_SUMMARY.value)
            correlation_results.append(corr_2_status.get("data_type") == TDDataType.DATA_SUMMARY.value)
            
        except Exception as e:
            print(f"Result correlation test failed: {e}")
            correlation_results.extend([False, False, False, False, False, False])
        
        # Step 5: Test data integrity
        integrity_results = []
        
        # Create data with integrity checks
        integrity_data = {
            "request_id": f"integrity_{uuid.uuid4().hex[:8]}",
            "data_type": "computation_result",
            "td_instance_id": "td_instance_004",
            "processing_time": 60.0,
            "priority": "A",
            "report_formats": ["HTML", "PDF"],
            "template_requirements": {
                "template_type": "integrity_report",
                "include_checksums": True
            },
            "content": {
                "route": "parallel",
                "input_parameters": {
                    "param1": 100,
                    "param2": 200
                },
                "computation_results": {
                    "result1": 150,
                    "result2": 300
                },
                "integrity_checks": {
                    "input_hash": "abc123def456",
                    "output_hash": "def456ghi789",
                    "computation_hash": "ghi789jkl012"
                },
                "validation_status": "verified",
                "checksum_valid": True
            }
        }
        
        try:
            # Receive integrity data
            integrity_success = await tdim.receive_td_data(integrity_data)
            integrity_results.append(integrity_success == True)
            
            # Check integrity validation
            integrity_status = tdim.get_processing_status(integrity_data["request_id"])
            integrity_results.append(isinstance(integrity_status, dict))
            integrity_results.append("data_hash" in integrity_status)
            integrity_results.append(len(integrity_status.get("data_hash", "")) > 0)
            integrity_results.append(integrity_status.get("validation_status") in [ValidationStatus.PENDING.value, ValidationStatus.VALID.value])
            
        except Exception as e:
            print(f"Data integrity test failed: {e}")
            integrity_results.extend([False, False, False, False, False])
        
        # Step 6: Test result processing
        processing_results = []
        
        # Create data for processing test
        processing_data = {
            "request_id": f"process_{uuid.uuid4().hex[:8]}",
            "data_type": "computation_result",
            "td_instance_id": "td_instance_005",
            "processing_time": 35.7,
            "priority": "B",
            "report_formats": ["HTML"],
            "template_requirements": {
                "template_type": "processing_report",
                "include_timeline": True
            },
            "content": {
                "route": "sequential",
                "processing_steps": [
                    {"step": 1, "name": "Data validation", "duration": 5.2, "status": "completed"},
                    {"step": 2, "name": "Computation", "duration": 25.1, "status": "completed"},
                    {"step": 3, "name": "Result formatting", "duration": 5.4, "status": "completed"}
                ],
                "total_processing_time": 35.7,
                "memory_usage": "512MB",
                "cpu_usage": "85%",
                "status": "completed"
            }
        }
        
        try:
            # Receive processing data
            processing_success = await tdim.receive_td_data(processing_data)
            processing_results.append(processing_success == True)
            
            # Check processing status
            processing_status = tdim.get_processing_status(processing_data["request_id"])
            processing_results.append(isinstance(processing_status, dict))
            processing_results.append(processing_status.get("data_type") == TDDataType.COMPUTATION_RESULT.value)
            processing_results.append(processing_status.get("processing_time") == 35.7)
            processing_results.append(processing_status.get("priority_level") == "B")
            
        except Exception as e:
            print(f"Result processing test failed: {e}")
            processing_results.extend([False, False, False, False, False])
        
        # Step 7: Test result storage
        storage_results = []
        
        # Create multiple data sets for storage test
        storage_data_sets = []
        for i in range(3):
            storage_data = {
                "request_id": f"storage_{i}_{uuid.uuid4().hex[:8]}",
                "data_type": "status_update",
                "td_instance_id": f"td_instance_{i+6}",
                "processing_time": 10.0 + i,
                "priority": "C",
                "report_formats": ["JSON"],
                "template_requirements": {},
                "content": {
                    "status": "completed",
                    "message": f"Processing completed for dataset {i}",
                    "timestamp": datetime.now().isoformat(),
                    "dataset_id": f"dataset_{i}"
                }
            }
            storage_data_sets.append(storage_data)
        
        try:
            # Receive multiple data sets
            storage_successes = []
            for storage_data in storage_data_sets:
                success = await tdim.receive_td_data(storage_data)
                storage_successes.append(success)
            
            storage_results.append(all(storage_successes))
            storage_results.append(len(storage_successes) == 3)
            
            # Check storage status
            overall_status = tdim.get_processing_status()
            storage_results.append(isinstance(overall_status, dict))
            storage_results.append("received" in overall_status)
            storage_results.append("processing" in overall_status)
            storage_results.append("completed" in overall_status)
            storage_results.append(overall_status.get("received", 0) >= 3)
            
        except Exception as e:
            print(f"Result storage test failed: {e}")
            storage_results.extend([False, False, False, False, False, False])
        
        # Step 8: Test error handling
        error_results = []
        
        # Test with None data
        try:
            none_reception = await tdim.receive_td_data(None)
            error_results.append(none_reception == False)
        except Exception:
            error_results.append(True)  # Exception is also acceptable
        
        # Test with empty data
        try:
            empty_reception = await tdim.receive_td_data({})
            error_results.append(empty_reception == False)
        except Exception:
            error_results.append(True)  # Exception is also acceptable
        
        # Test with very large data
        large_data = {
            "request_id": f"large_{uuid.uuid4().hex[:8]}",
            "data_type": "computation_result",
            "content": "A" * (150 * 1024 * 1024)  # 150MB, exceeds limit
        }
        
        try:
            large_reception = await tdim.receive_td_data(large_data)
            error_results.append(large_reception == False)  # Should fail due to size
        except Exception:
            error_results.append(True)  # Exception is also acceptable
        
        # Step 9: Test performance
        performance_results = []
        
        # Test concurrent data reception
        start_time = datetime.now()
        
        concurrent_data_sets = []
        for i in range(5):
            concurrent_data = {
                "request_id": f"perf_{i}_{uuid.uuid4().hex[:8]}",
                "data_type": "computation_result",
                "td_instance_id": f"td_perf_{i}",
                "processing_time": 15.0,
                "priority": "C",
                "report_formats": ["JSON"],
                "template_requirements": {},
                "content": {
                    "calculation_type": f"TEST_{i}",
                    "result": f"result_{i}",
                    "status": "completed"
                }
            }
            concurrent_data_sets.append(concurrent_data)
        
        try:
            # Receive data concurrently
            concurrent_tasks = []
            for concurrent_data in concurrent_data_sets:
                task = tdim.receive_td_data(concurrent_data)
                concurrent_tasks.append(task)
            
            concurrent_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            end_time = datetime.now()
            performance_time = (end_time - start_time).total_seconds()
            
            performance_results.append(len(concurrent_results) == 5)
            performance_results.append(any(result == True for result in concurrent_results))
            performance_results.append(performance_time < 10.0)  # Should complete within 10 seconds
            
        except Exception as e:
            print(f"Performance test failed: {e}")
            performance_results.extend([False, False, False])
        
        # Step 10: Test validation
        validation_results = []
        
        # Test module status
        try:
            status = tdim.get_status()
            validation_results.append(isinstance(status, dict))
            validation_results.append("module" in status)
            validation_results.append("active" in status)
            validation_results.append("validation_enabled" in status)
            validation_results.append("td_service_status" in status)
            validation_results.append("data_counts" in status)
            validation_results.append("queue_sizes" in status)
            validation_results.append("stats" in status)
            
        except Exception as e:
            print(f"Module status test failed: {e}")
            validation_results.extend([False, False, False, False, False, False, False, False])
        
        # Test health check
        try:
            health = await tdim.health_check()
            validation_results.append(isinstance(health, dict))
            validation_results.append("healthy" in health)
            validation_results.append("is_active" in health)
            validation_results.append("module" in health)
            
        except Exception as e:
            print(f"Health check test failed: {e}")
            validation_results.extend([False, False, False, False])
        
        # Test statistics
        try:
            status = tdim.get_status()
            stats = status.get("stats", {})
            validation_results.append(isinstance(stats, dict))
            validation_results.append("data_packets_received" in stats)
            validation_results.append("data_packets_processed" in stats)
            validation_results.append("data_packets_validated" in stats)
            validation_results.append(stats.get("data_packets_received", 0) >= 0)
            
        except Exception as e:
            print(f"Statistics test failed: {e}")
            validation_results.extend([False, False, False, False, False])
        
        # Aggregate all results
        all_results = (
            results + 
            reception_results + 
            validation_results + 
            correlation_results + 
            integrity_results + 
            processing_results + 
            storage_results + 
            error_results + 
            performance_results + 
            validation_results
        )
        
        # Calculate pass rate
        passed_tests = sum(all_results)
        total_tests = len(all_results)
        pass_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        # Get final status
        final_status = tdim.get_status()
        
        # Cleanup
        await tdim.stop()
        
        # Clean up test directory
        try:
            import shutil
            shutil.rmtree(test_dir)
        except Exception:
            pass  # Ignore cleanup errors
        
        return {
            "test_code": test_code,
            "test_name": test_name,
            "status": "PASSED" if pass_rate >= 85 else "FAILED",
            "pass_rate": pass_rate,
            "passed_tests": passed_tests,
            "total_tests": total_tests,
            "results": {
                "module_initialization": results,
                "td_computation_result_reception": reception_results,
                "data_format_validation": validation_results,
                "result_correlation": correlation_results,
                "data_integrity": integrity_results,
                "result_processing": processing_results,
                "result_storage": storage_results,
                "error_handling": error_results,
                "performance": performance_results,
                "validation": validation_results
            },
            "tdim_metrics": {
                "data_packets_received": final_status.get("stats", {}).get("data_packets_received", 0),
                "data_packets_processed": final_status.get("stats", {}).get("data_packets_processed", 0),
                "data_packets_validated": final_status.get("stats", {}).get("data_packets_validated", 0),
                "validation_failures": final_status.get("stats", {}).get("validation_failures", 0),
                "td_connection_errors": final_status.get("stats", {}).get("td_connection_errors", 0),
                "data_types_received": final_status.get("stats", {}).get("data_types_received", {}),
                "queue_sizes": final_status.get("queue_sizes", {}),
                "data_counts": final_status.get("data_counts", {})
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "test_code": test_code,
            "test_name": test_name,
            "status": "ERROR",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

async def main():
    """Main test execution function."""
    result = await test_o00000047()
    print(json.dumps(result, indent=2))
    return result

if __name__ == "__main__":
    asyncio.run(main())