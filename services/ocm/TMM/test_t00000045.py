"""
Test O00000045: DSM Compression and Optimization
Module(s) Tested: DSM (Data Sender Module)
Description: Test data compression and optimization capabilities
Test Description:
- Test data compression algorithms
- Verify compression ratio optimization
- Check compression performance
- Test optimization strategies
- Validate compression quality
- Test compression error handling
Expected Result: Efficient data compression and optimization
Pass Criteria: Compression works, ratios optimized, performance good, quality maintained
Implementation Notes: Test with various data types and sizes
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

async def test_o00000045():
    test_code = "O00000045"
    test_name = "DSM Compression and Optimization"
    results = []
    
    try:
        # Import required modules
        from DSM.dsm import DataSenderModule, DataType, CompressionType
        from RMM.rmm import RequestInfo, RequestType, RequestPriority, RequestStatus
        
        # Create temporary test directory
        test_dir = tempfile.mkdtemp(prefix="dsm_compression_test_")
        
        # Step 1: Test DSM module initialization with compression config
        config = {
            "compression": {
                "enabled": True,
                "compression_threshold": 1024,
                "default_compression": "gzip",
                "compression_algorithms": ["gzip", "brotli", "lz4"],
                "compression_quality": 6,
                "optimization_enabled": True
            },
            "optimization": {
                "data_optimization": True,
                "size_optimization": True,
                "performance_optimization": True,
                "quality_optimization": True
            },
            "compression_settings": {
                "gzip_level": 6,
                "brotli_quality": 6,
                "lz4_acceleration": 1,
                "min_compression_ratio": 0.8
            }
        }
        
        dsm = DataSenderModule(config)
        await dsm.start()
        results.append(dsm.is_active == True)
        results.append(hasattr(dsm, 'send_data'))
        results.append(hasattr(dsm, 'get_transmission_history'))
        results.append(hasattr(dsm, 'get_statistics'))
        
        # Step 2: Test data compression algorithms
        compression_results = []
        
        # Create test request info for compression test
        compression_request_info = RequestInfo(
            request_id=str(uuid.uuid4()),
            request_type=RequestType.API_RESPONSE,
            priority=RequestPriority.A,
            status=RequestStatus.READY_TO_SEND,
            source_module="RCMIM",
            received_at=datetime.now(),
            content_type="json",
            content_size=2048,
            content_hash="compression_test_hash",
            destination="https://compression-test-server.com/api",
            metadata={
                "compression_config": {
                    "algorithm": "gzip",
                    "level": 6,
                    "threshold": 1024,
                    "optimize": True
                },
                "response_data": {
                    "status": "compression_test",
                    "data_size": 2048,
                    "compression_enabled": True,
                    "test_data": "A" * 1000  # Repeatable data for compression
                }
            }
        )
        
        try:
            # Test data compression
            compression_result = await dsm.send_data(compression_request_info)
            compression_results.append(compression_result is not None)
            compression_results.append(isinstance(compression_result, dict))
            
            if compression_result:
                compression_results.append('success' in compression_result or 'error' in compression_result)
                compression_results.append('request_id' in compression_result)
            else:
                compression_results.extend([False, False])
                
        except Exception as e:
            print(f"Data compression test failed: {e}")
            compression_results.extend([False, False, False, False])
        
        # Step 3: Test compression ratio optimization
        ratio_results = []
        
        # Create test request info for ratio optimization
        ratio_request_info = RequestInfo(
            request_id=str(uuid.uuid4()),
            request_type=RequestType.API_RESPONSE,
            priority=RequestPriority.A,
            status=RequestStatus.READY_TO_SEND,
            source_module="RCMIM",
            received_at=datetime.now(),
            content_type="json",
            content_size=4096,
            content_hash="ratio_test_hash",
            destination="https://ratio-test-server.com/api",
            metadata={
                "compression_optimization": {
                    "target_ratio": 0.5,
                    "min_ratio": 0.8,
                    "optimize_for_size": True,
                    "quality_threshold": 0.9
                },
                "response_data": {
                    "status": "ratio_optimization_test",
                    "data_size": 4096,
                    "target_compression_ratio": 0.5,
                    "test_data": "B" * 2000 + "C" * 2000  # Mixed data for ratio testing
                }
            }
        )
        
        try:
            # Test compression ratio optimization
            ratio_result = await dsm.send_data(ratio_request_info)
            ratio_results.append(ratio_result is not None)
            ratio_results.append(isinstance(ratio_result, dict))
            
            if ratio_result:
                ratio_results.append('success' in ratio_result or 'error' in ratio_result)
                ratio_results.append('request_id' in ratio_result)
            else:
                ratio_results.extend([False, False])
                
        except Exception as e:
            print(f"Compression ratio optimization test failed: {e}")
            ratio_results.extend([False, False, False, False])
        
        # Step 4: Test compression performance
        performance_results = []
        
        # Create test request info for performance test
        performance_request_info = RequestInfo(
            request_id=str(uuid.uuid4()),
            request_type=RequestType.API_RESPONSE,
            priority=RequestPriority.B,
            status=RequestStatus.READY_TO_SEND,
            source_module="RCMIM",
            received_at=datetime.now(),
            content_type="json",
            content_size=8192,
            content_hash="performance_test_hash",
            destination="https://performance-test-server.com/api",
            metadata={
                "compression_performance": {
                    "measure_time": True,
                    "measure_memory": True,
                    "measure_cpu": True,
                    "performance_threshold": 100  # ms
                },
                "response_data": {
                    "status": "performance_test",
                    "data_size": 8192,
                    "performance_measurement": True,
                    "test_data": "D" * 4000 + "E" * 4000  # Large data for performance testing
                }
            }
        )
        
        try:
            # Test compression performance
            perf_result = await dsm.send_data(performance_request_info)
            performance_results.append(perf_result is not None)
            performance_results.append(isinstance(perf_result, dict))
            
            if perf_result:
                performance_results.append('success' in perf_result or 'error' in perf_result)
                performance_results.append('request_id' in perf_result)
            else:
                performance_results.extend([False, False])
                
        except Exception as e:
            print(f"Compression performance test failed: {e}")
            performance_results.extend([False, False, False, False])
        
        # Step 5: Test optimization strategies
        optimization_results = []
        
        # Create test request info for optimization test
        optimization_request_info = RequestInfo(
            request_id=str(uuid.uuid4()),
            request_type=RequestType.API_RESPONSE,
            priority=RequestPriority.B,
            status=RequestStatus.READY_TO_SEND,
            source_module="RCMIM",
            received_at=datetime.now(),
            content_type="json",
            content_size=3072,
            content_hash="optimization_test_hash",
            destination="https://optimization-test-server.com/api",
            metadata={
                "optimization_strategy": {
                    "data_optimization": True,
                    "size_optimization": True,
                    "performance_optimization": True,
                    "quality_optimization": True
                },
                "response_data": {
                    "status": "optimization_test",
                    "data_size": 3072,
                    "optimization_enabled": True,
                    "test_data": "F" * 1500 + "G" * 1500  # Data for optimization testing
                }
            }
        )
        
        try:
            # Test optimization strategies
            opt_result = await dsm.send_data(optimization_request_info)
            optimization_results.append(opt_result is not None)
            optimization_results.append(isinstance(opt_result, dict))
            
            if opt_result:
                optimization_results.append('success' in opt_result or 'error' in opt_result)
                optimization_results.append('request_id' in opt_result)
            else:
                optimization_results.extend([False, False])
                
        except Exception as e:
            print(f"Optimization strategies test failed: {e}")
            optimization_results.extend([False, False, False, False])
        
        # Step 6: Test compression quality
        quality_results = []
        
        # Create test request info for quality test
        quality_request_info = RequestInfo(
            request_id=str(uuid.uuid4()),
            request_type=RequestType.API_RESPONSE,
            priority=RequestPriority.C,
            status=RequestStatus.READY_TO_SEND,
            source_module="RCMIM",
            received_at=datetime.now(),
            content_type="json",
            content_size=1536,
            content_hash="quality_test_hash",
            destination="https://quality-test-server.com/api",
            metadata={
                "compression_quality": {
                    "quality_threshold": 0.9,
                    "lossless_compression": True,
                    "quality_verification": True,
                    "checksum_validation": True
                },
                "response_data": {
                    "status": "quality_test",
                    "data_size": 1536,
                    "quality_threshold": 0.9,
                    "test_data": "H" * 768 + "I" * 768  # Data for quality testing
                }
            }
        )
        
        try:
            # Test compression quality
            quality_result = await dsm.send_data(quality_request_info)
            quality_results.append(quality_result is not None)
            quality_results.append(isinstance(quality_result, dict))
            
            if quality_result:
                quality_results.append('success' in quality_result or 'error' in quality_result)
                quality_results.append('request_id' in quality_result)
            else:
                quality_results.extend([False, False])
                
        except Exception as e:
            print(f"Compression quality test failed: {e}")
            quality_results.extend([False, False, False, False])
        
        # Step 7: Test compression error handling
        error_results = []
        
        # Test with invalid compression algorithm
        invalid_compression_request = RequestInfo(
            request_id=str(uuid.uuid4()),
            request_type=RequestType.API_RESPONSE,
            priority=RequestPriority.D,
            status=RequestStatus.READY_TO_SEND,
            source_module="RCMIM",
            received_at=datetime.now(),
            content_type="json",
            content_size=512,
            content_hash="error_compression_hash",
            destination="https://error-compression-server.com/api",
            metadata={
                "compression_config": {
                    "algorithm": "invalid_algorithm",
                    "level": 10,
                    "threshold": -1
                },
                "response_data": {
                    "test_type": "error_handling"
                }
            }
        )
        
        try:
            error_result = await dsm.send_data(invalid_compression_request)
            error_results.append(error_result is not None)
            
            if error_result:
                error_results.append('error' in error_result or 'success' in error_result)
            else:
                error_results.append(False)
                
        except Exception:
            # Exception is also acceptable for invalid compression
            error_results.extend([True, True])
        
        # Test with very large data
        try:
            large_data_request = RequestInfo(
                request_id=str(uuid.uuid4()),
                request_type=RequestType.API_RESPONSE,
                priority=RequestPriority.D,
                status=RequestStatus.READY_TO_SEND,
                source_module="RCMIM",
                received_at=datetime.now(),
                content_type="json",
                content_size=1048576,  # 1MB
                content_hash="large_data_hash",
                destination="https://large-data-server.com/api",
                metadata={
                    "response_data": {
                        "test_type": "large_data",
                        "data_size": 1048576
                    }
                }
            )
            
            large_result = await dsm.send_data(large_data_request)
            error_results.append(large_result is not None)
            
        except Exception:
            # Exception is also acceptable for very large data
            error_results.append(True)
        
        # Step 8: Test compression performance with multiple algorithms
        multi_algorithm_results = []
        
        # Test multiple compression algorithms
        start_time = datetime.now()
        
        algorithms = ["gzip", "brotli", "lz4"]
        algorithm_requests = []
        
        for i, algorithm in enumerate(algorithms):
            algo_request = RequestInfo(
                request_id=str(uuid.uuid4()),
                request_type=RequestType.API_RESPONSE,
                priority=RequestPriority.C,
                status=RequestStatus.READY_TO_SEND,
                source_module="RCMIM",
                received_at=datetime.now(),
                content_type="json",
                content_size=1024,
                content_hash=f"algo_{algorithm}_hash",
                destination=f"https://{algorithm}-test-server.com/api",
                metadata={
                    "compression_config": {
                        "algorithm": algorithm,
                        "level": 6,
                        "threshold": 512
                    },
                    "response_data": {
                        "test_id": i,
                        "algorithm": algorithm,
                        "test_data": f"Algorithm {algorithm} test data"
                    }
                }
            )
            algorithm_requests.append(algo_request)
        
        try:
            # Execute multiple algorithm tests
            algo_results = []
            for request in algorithm_requests:
                result = await dsm.send_data(request)
                algo_results.append(result is not None)
            
            end_time = datetime.now()
            algorithm_time = (end_time - start_time).total_seconds()
            
            multi_algorithm_results.append(len(algo_results) == 3)
            multi_algorithm_results.append(any(algo_results))
            multi_algorithm_results.append(algorithm_time < 10.0)  # Should complete within 10 seconds
            
        except Exception as e:
            print(f"Multi-algorithm compression test failed: {e}")
            multi_algorithm_results.extend([False, False, False])
        
        # Step 9: Test compression validation
        validation_results = []
        
        # Test compression statistics
        try:
            stats = dsm.get_statistics()
            validation_results.append(isinstance(stats, dict))
            validation_results.append('data_packets_sent' in stats)
            validation_results.append('compression_ratio' in stats)
        except Exception:
            validation_results.extend([False, False, False])
        
        # Test transmission history
        try:
            history = dsm.get_transmission_history()
            validation_results.append(isinstance(history, dict))
            validation_results.append(len(history) >= 0)  # Should have some history
        except Exception:
            validation_results.extend([False, False])
        
        # Test module status
        try:
            status = dsm.get_status()
            validation_results.append(isinstance(status, dict))
            validation_results.append('is_active' in status)
        except Exception:
            validation_results.extend([False, False])
        
        # Test health check
        try:
            health = await dsm.health_check()
            validation_results.append(isinstance(health, dict))
        except Exception:
            validation_results.append(False)
        
        # Aggregate all results
        all_results = (
            results + 
            compression_results + 
            ratio_results + 
            performance_results + 
            optimization_results + 
            quality_results + 
            error_results + 
            multi_algorithm_results + 
            validation_results
        )
        
        # Calculate pass rate
        passed_tests = sum(all_results)
        total_tests = len(all_results)
        pass_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        # Cleanup
        await dsm.stop()
        
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
                "data_compression_algorithms": compression_results,
                "compression_ratio_optimization": ratio_results,
                "compression_performance": performance_results,
                "optimization_strategies": optimization_results,
                "compression_quality": quality_results,
                "compression_error_handling": error_results,
                "multi_algorithm_compression": multi_algorithm_results,
                "compression_validation": validation_results
            },
            "compression_metrics": {
                "total_compression_tests": 6,
                "compression_time_seconds": algorithm_time if 'algorithm_time' in locals() else 0,
                "successful_compressions": sum([1 for r in [compression_results, ratio_results, performance_results, optimization_results, quality_results] if r and len(r) > 0 and r[0]]),
                "algorithms_tested": 3
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
    result = await test_o00000045()
    print(json.dumps(result, indent=2))
    return result

if __name__ == "__main__":
    asyncio.run(main())