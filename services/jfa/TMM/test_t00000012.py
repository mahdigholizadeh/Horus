"""
Test T00000012: MSM (Monitoring System Module) Unit Test
Module(s) Tested: MSM
Description: To verify that the MSM accurately collects and reports system resource and performance metrics.
Success Criteria: Metrics accurately report templates_processed: 10, average processing time, and other relevant stats.
"""

import asyncio
import json
import sys
import time
import os
from pathlib import Path
from typing import Dict, Any
import importlib

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from MSM.msm import MonitoringSystemModule

if "MSM.msm" in sys.modules:
    importlib.reload(sys.modules["MSM.msm"])

async def test_t00000012():
    test_code = "T00000012"
    test_name = "MSM - Monitoring System Module Unit Test"
    results = []
    
    # Clean up metrics or persistent files before running the test
    metrics_file = Path("logs/msm_metrics.json")
    if metrics_file.exists():
        try:
            metrics_file.unlink()
        except Exception:
            pass
    
    msm = MonitoringSystemModule()
    await msm.start()
    
    try:
        # Step 1: Reset all MSM counters
        reset_result = await msm.reset_metrics()
        results.append(reset_result.get("success", False))
        
        # Step 2: Simulate the processing of 10 templates
        for i in range(10):
            # Simulate template processing
            start_time = time.time()
            
            # Simulate processing time
            await asyncio.sleep(0.1)
            
            processing_time = time.time() - start_time
            
            # Record metrics for each template
            await msm.record_template_processed(
                template_id=f"TEMPLATE-{i:03d}",
                processing_time=processing_time,
                success=True,
                size_bytes=1024 * (i + 1)
            )
        
        # Step 3: Request the current metrics from the module
        metrics = await msm.get_monitoring_data()
        
        # Check if metrics are present
        results.append(isinstance(metrics, dict))
        
        # Check if templates_processed is 10
        templates_processed = metrics.get("templates_processed", 0)
        results.append(templates_processed == 10)
        
        # Check if average processing time is calculated
        avg_processing_time = metrics.get("average_processing_time", 0)
        results.append(avg_processing_time > 0)
        results.append(avg_processing_time < 1.0)  # Should be reasonable
        
        # Check other relevant metrics
        results.append("total_processing_time" in metrics)
        results.append("successful_processing" in metrics)
        results.append("failed_processing" in metrics)
        results.append("success_rate" in metrics)
        
        # Check system resource metrics
        system_metrics = metrics.get("system_metrics", {})
        results.append(isinstance(system_metrics, dict))
        results.append("cpu_usage" in system_metrics)
        results.append("memory_usage" in system_metrics)
        results.append("disk_usage" in system_metrics)
        
        # Test metric recording for failed processing
        await msm.record_template_processed(
            template_id="FAILED-TEMPLATE",
            processing_time=0.5,
            success=False,
            size_bytes=2048,
            error_message="Test error"
        )
        
        # Check updated metrics
        updated_metrics = await msm.get_monitoring_data()
        results.append(updated_metrics.get("templates_processed", 0) == 11)
        results.append(updated_metrics.get("failed_processing", 0) == 1)
        
        # Test performance metrics
        performance_metrics = await msm.get_performance_metrics()
        results.append(isinstance(performance_metrics, dict))
        results.append("throughput" in performance_metrics)
        results.append("response_time" in performance_metrics)
        results.append("error_rate" in performance_metrics)
        
        # Test health check
        health_status = await msm.health_check()
        results.append(isinstance(health_status, dict))
        results.append("healthy" in health_status)
        results.append("timestamp" in health_status)
        
        # Test metric export
        export_result = await msm.export_metrics()
        results.append(export_result.get("success", False))
        
        if export_result.get("success", False):
            exported_data = export_result.get("data", {})
            results.append(isinstance(exported_data, dict))
            results.append("templates_processed" in exported_data)
        else:
            results.extend([False, False])
        
        # Test metric cleanup
        cleanup_result = await msm.cleanup_old_metrics(days=1)
        results.append(cleanup_result.get("success", False))
        
        success = all(results)
        
        return {
            "success": success,
            "test_code": test_code,
            "test_name": test_name,
            "message": "MSM unit test passed" if success else "MSM unit test failed",
            "details": {
                "metrics_reset_successful": results[0],
                "metrics_data_structure_valid": results[1],
                "templates_processed_correct": results[2],
                "average_processing_time_calculated": results[3],
                "average_processing_time_reasonable": results[4],
                "total_processing_time_present": results[5],
                "successful_processing_present": results[6],
                "failed_processing_present": results[7],
                "success_rate_present": results[8],
                "system_metrics_structure_valid": results[9],
                "cpu_usage_present": results[10],
                "memory_usage_present": results[11],
                "disk_usage_present": results[12],
                "failed_processing_counted": results[13],
                "failed_processing_updated": results[14],
                "performance_metrics_generated": results[15],
                "throughput_present": results[16],
                "response_time_present": results[17],
                "error_rate_present": results[18],
                "health_check_works": results[19],
                "health_status_valid": results[20],
                "health_timestamp_present": results[21],
                "metrics_export_successful": results[22],
                "exported_data_valid": results[23],
                "exported_data_has_templates": results[24],
                "metrics_cleanup_successful": results[25],
                "final_metrics": metrics,
                "results": results
            }
        }
        
    finally:
        await msm.stop()