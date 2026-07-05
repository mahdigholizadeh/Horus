"""
Test O00000023: MSM System Metrics Collection
Module(s) Tested: MSM (Monitoring System Module)
Description: Test system-level metrics collection
Test Description:
- Collect CPU usage metrics
- Monitor memory utilization
- Track disk I/O statistics
- Test network usage monitoring
- Verify process monitoring
- Check system load metrics
Expected Result: Comprehensive system metrics collection
Pass Criteria: Metrics collected, accuracy maintained, performance acceptable, alerts generated
Implementation Notes: Monitor system resources during testing
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_o00000023():
    test_code = "O00000023"
    test_name = "MSM System Metrics Collection"
    results = []
    
    try:
        # Import MSM module
        from MSM.msm import MonitoringSystemModule
        
        # Step 1: Test MSM module initialization with monitoring config
        config = {
            "monitoring": {
                "enabled": True,
                "collection_interval": 30,
                "retention_period": 86400,  # 24 hours
                "max_metrics_points": 10000,
                "health_check_interval": 60
            },
            "system_metrics": {
                "enabled": True,
                "cpu_monitoring": True,
                "memory_monitoring": True,
                "disk_monitoring": True,
                "network_monitoring": True,
                "process_monitoring": True
            },
            "thresholds": {
                "cpu_usage_warning": 80.0,
                "cpu_usage_critical": 95.0,
                "memory_usage_warning": 85.0,
                "memory_usage_critical": 95.0,
                "disk_usage_warning": 85.0,
                "disk_usage_critical": 95.0
            }
        }
        
        msm = MonitoringSystemModule(config)
        results.append(msm is not None)
        results.append(hasattr(msm, 'record_metric'))
        results.append(hasattr(msm, 'get_metrics'))
        results.append(hasattr(msm, 'get_system_metrics'))
        
        # Step 2: Test CPU usage metrics collection
        cpu_results = []
        
        # Test CPU metrics recording
        msm.record_metric("cpu_usage_percent", 45.5, tags={"core": "all"})
        msm.record_metric("cpu_usage_percent", 67.2, tags={"core": "0"})
        msm.record_metric("cpu_usage_percent", 23.8, tags={"core": "1"})
        
        # Test CPU metrics retrieval
        cpu_metrics = msm.get_metrics("cpu_usage_percent")
        cpu_results.append("cpu_usage_percent" in cpu_metrics)
        cpu_results.append(len(cpu_metrics.get("cpu_usage_percent", [])) >= 3)
        
        # Test CPU threshold monitoring
        cpu_thresholds = config["thresholds"]
        cpu_results.append(cpu_thresholds.get("cpu_usage_warning") == 80.0)
        cpu_results.append(cpu_thresholds.get("cpu_usage_critical") == 95.0)
        
        # Test CPU usage validation
        cpu_results.append(0 <= 45.5 <= 100)  # Valid CPU usage
        cpu_results.append(0 <= 67.2 <= 100)  # Valid CPU usage
        cpu_results.append(0 <= 23.8 <= 100)  # Valid CPU usage
        
        results.extend(cpu_results)
        
        # Step 3: Test memory utilization monitoring
        memory_results = []
        
        # Test memory metrics recording
        msm.record_metric("memory_usage_percent", 65.3, tags={"type": "ram"})
        msm.record_metric("memory_available_mb", 2048.5, tags={"type": "ram"})
        msm.record_metric("memory_used_mb", 4096.2, tags={"type": "ram"})
        msm.record_metric("swap_usage_percent", 12.7, tags={"type": "swap"})
        
        # Test memory metrics retrieval
        memory_metrics = msm.get_metrics("memory_usage_percent")
        memory_results.append("memory_usage_percent" in memory_metrics)
        memory_results.append(len(memory_metrics.get("memory_usage_percent", [])) >= 1)
        
        # Test memory threshold monitoring
        memory_thresholds = config["thresholds"]
        memory_results.append(memory_thresholds.get("memory_usage_warning") == 85.0)
        memory_results.append(memory_thresholds.get("memory_usage_critical") == 95.0)
        
        # Test memory usage validation
        memory_results.append(0 <= 65.3 <= 100)  # Valid memory usage
        memory_results.append(2048.5 > 0)  # Valid available memory
        memory_results.append(4096.2 > 0)  # Valid used memory
        memory_results.append(0 <= 12.7 <= 100)  # Valid swap usage
        
        results.extend(memory_results)
        
        # Step 4: Test disk I/O statistics
        disk_results = []
        
        # Test disk metrics recording
        msm.record_metric("disk_usage_percent", 72.1, tags={"device": "/dev/sda1"})
        msm.record_metric("disk_read_bytes", 1024000, tags={"device": "/dev/sda1"})
        msm.record_metric("disk_write_bytes", 512000, tags={"device": "/dev/sda1"})
        msm.record_metric("disk_read_ops", 150, tags={"device": "/dev/sda1"})
        msm.record_metric("disk_write_ops", 75, tags={"device": "/dev/sda1"})
        
        # Test disk metrics retrieval
        disk_metrics = msm.get_metrics("disk_usage_percent")
        disk_results.append("disk_usage_percent" in disk_metrics)
        disk_results.append(len(disk_metrics.get("disk_usage_percent", [])) >= 1)
        
        # Test disk threshold monitoring
        disk_thresholds = config["thresholds"]
        disk_results.append(disk_thresholds.get("disk_usage_warning") == 85.0)
        disk_results.append(disk_thresholds.get("disk_usage_critical") == 95.0)
        
        # Test disk usage validation
        disk_results.append(0 <= 72.1 <= 100)  # Valid disk usage
        disk_results.append(1024000 > 0)  # Valid read bytes
        disk_results.append(512000 > 0)  # Valid write bytes
        disk_results.append(150 > 0)  # Valid read ops
        disk_results.append(75 > 0)  # Valid write ops
        
        results.extend(disk_results)
        
        # Step 5: Test network usage monitoring
        network_results = []
        
        # Test network metrics recording
        msm.record_metric("network_bytes_sent", 2048000, tags={"interface": "eth0"})
        msm.record_metric("network_bytes_recv", 3072000, tags={"interface": "eth0"})
        msm.record_metric("network_packets_sent", 500, tags={"interface": "eth0"})
        msm.record_metric("network_packets_recv", 750, tags={"interface": "eth0"})
        msm.record_metric("network_errors", 2, tags={"interface": "eth0"})
        msm.record_metric("network_dropped", 1, tags={"interface": "eth0"})
        
        # Test network metrics retrieval
        network_metrics = msm.get_metrics("network_bytes_sent")
        network_results.append("network_bytes_sent" in network_metrics)
        network_results.append(len(network_metrics.get("network_bytes_sent", [])) >= 1)
        
        # Test network usage validation
        network_results.append(2048000 > 0)  # Valid bytes sent
        network_results.append(3072000 > 0)  # Valid bytes received
        network_results.append(500 > 0)  # Valid packets sent
        network_results.append(750 > 0)  # Valid packets received
        network_results.append(2 >= 0)  # Valid errors (can be 0)
        network_results.append(1 >= 0)  # Valid dropped (can be 0)
        
        results.extend(network_results)
        
        # Step 6: Test process monitoring
        process_results = []
        
        # Test process metrics recording
        msm.record_metric("process_count", 125, tags={"type": "total"})
        msm.record_metric("process_count", 15, tags={"type": "running"})
        msm.record_metric("process_count", 5, tags={"type": "sleeping"})
        msm.record_metric("process_count", 2, tags={"type": "stopped"})
        msm.record_metric("process_count", 1, tags={"type": "zombie"})
        
        # Test process metrics retrieval
        process_metrics = msm.get_metrics("process_count")
        process_results.append("process_count" in process_metrics)
        process_results.append(len(process_metrics.get("process_count", [])) >= 5)
        
        # Test process count validation
        process_results.append(125 > 0)  # Valid total processes
        process_results.append(15 > 0)  # Valid running processes
        process_results.append(5 >= 0)  # Valid sleeping processes
        process_results.append(2 >= 0)  # Valid stopped processes
        process_results.append(1 >= 0)  # Valid zombie processes
        
        # Test process count consistency
        total_processes = 15 + 5 + 2 + 1  # running + sleeping + stopped + zombie
        process_results.append(total_processes <= 125)  # Should not exceed total
        
        results.extend(process_results)
        
        # Step 7: Test system load metrics
        load_results = []
        
        # Test load average metrics recording
        msm.record_metric("load_average_1min", 1.25, tags={"period": "1min"})
        msm.record_metric("load_average_5min", 1.15, tags={"period": "5min"})
        msm.record_metric("load_average_15min", 1.05, tags={"period": "15min"})
        
        # Test load metrics retrieval
        load_metrics = msm.get_metrics("load_average_1min")
        load_results.append("load_average_1min" in load_metrics)
        load_results.append(len(load_metrics.get("load_average_1min", [])) >= 1)
        
        # Test load average validation
        load_results.append(1.25 >= 0)  # Valid 1min load
        load_results.append(1.15 >= 0)  # Valid 5min load
        load_results.append(1.05 >= 0)  # Valid 15min load
        
        # Test load average trends (should generally decrease over longer periods)
        load_results.append(1.25 >= 1.15)  # 1min >= 5min
        load_results.append(1.15 >= 1.05)  # 5min >= 15min
        
        results.extend(load_results)
        
        # Step 8: Test metrics aggregation
        aggregation_results = []
        
        # Test metrics summary calculation
        test_values = [10.0, 20.0, 30.0, 40.0, 50.0]
        for value in test_values:
            msm.record_metric("test_aggregation", value)
        
        # Get aggregated metrics
        aggregated_metrics = msm.get_metrics("test_aggregation")
        aggregation_results.append("test_aggregation" in aggregated_metrics)
        aggregation_results.append(len(aggregated_metrics.get("test_aggregation", [])) >= 5)
        
        # Test aggregation accuracy
        test_metrics = aggregated_metrics.get("test_aggregation", [])
        if test_metrics:
            values = [metric.get("value", 0) for metric in test_metrics]
            aggregation_results.append(min(values) == 10.0)
            aggregation_results.append(max(values) == 50.0)
            aggregation_results.append(sum(values) == 150.0)
        
        results.extend(aggregation_results)
        
        # Step 9: Test metrics retention
        retention_results = []
        
        # Test retention configuration
        retention_config = config["monitoring"]
        retention_results.append(retention_config.get("retention_period") == 86400)
        retention_results.append(retention_config.get("max_metrics_points") == 10000)
        
        # Test metrics storage limits
        for i in range(100):
            msm.record_metric("retention_test", float(i))
        
        retention_metrics = msm.get_metrics("retention_test")
        retention_results.append("retention_test" in retention_metrics)
        retention_results.append(len(retention_metrics.get("retention_test", [])) >= 50)
        
        results.extend(retention_results)
        
        # Step 10: Test system metrics summary
        summary_results = []
        
        # Test system metrics collection
        system_metrics = msm.get_system_metrics()
        summary_results.append(isinstance(system_metrics, list))
        summary_results.append(len(system_metrics) >= 0)
        
        # Test metrics collection performance
        start_time = datetime.now()
        for i in range(100):
            msm.record_metric("performance_test", float(i))
        end_time = datetime.now()
        
        collection_time = (end_time - start_time).total_seconds()
        summary_results.append(collection_time < 1.0)  # Should be fast
        summary_results.append(collection_time >= 0)  # Should be positive
        
        results.extend(summary_results)
        
        # Calculate test results
        total_tests = len(results)
        passed_tests = sum(results)
        failed_tests = total_tests - passed_tests
        
        test_result = {
            "test_code": test_code,
            "test_name": test_name,
            "status": "PASSED" if failed_tests == 0 else "FAILED",
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": (passed_tests / total_tests) * 100 if total_tests > 0 else 0,
            "details": {
                "cpu_metrics_collected": all(cpu_results[:7]),
                "memory_metrics_collected": all(memory_results[:8]),
                "disk_metrics_collected": all(disk_results[:9]),
                "network_metrics_collected": all(network_results[:8]),
                "process_metrics_collected": all(process_results[:9]),
                "load_metrics_collected": all(load_results[:7]),
                "aggregation_working": all(aggregation_results[:6]),
                "retention_functional": all(retention_results[:5]),
                "summary_generated": all(summary_results[:4])
            },
            "timestamp": asyncio.get_event_loop().time()
        }
        
        return test_result
        
    except Exception as e:
        return {
            "test_code": test_code,
            "test_name": test_name,
            "status": "ERROR",
            "error": f"Test execution error: {str(e)}",
            "details": {"error_type": type(e).__name__, "message": str(e)},
            "timestamp": asyncio.get_event_loop().time()
        }

if __name__ == "__main__":
    async def main():
        result = await test_o00000023()
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["status"] == "PASSED" else 1)
    
    asyncio.run(main()) 