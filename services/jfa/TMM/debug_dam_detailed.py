#!/usr/bin/env python3
"""
Detailed debug script to analyze DAM analysis results for both normal and anomalous data.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

async def debug_dam_analysis():
    """Debug DAM analysis with both normal and anomalous data."""
    from DAM.dam import DataAnalysisModule
    
    dam = DataAnalysisModule()
    await dam.start()
    
    # Test with normal data (high quality)
    normal_validation_result = {
        "valid": True,
        "validation_score": 0.95,
        "errors": [],
        "validated_data": {
            "system_configuration": {
                "inverter_efficiency": 0.96,
                "panel_efficiency": 0.225,
                "system_availability": 0.99,
                "maintenance_schedule": "quarterly",
                "monitoring_enabled": True
            },
            "performance_metrics": {
                "annual_output_kwh": 4200,
                "capacity_factor": 0.18,
                "system_losses": 0.05,
                "availability_factor": 0.98
            },
            "financial_metrics": {
                "roi_percentage": 12.5,
                "payback_period_years": 8.2,
                "lifetime_savings": 45000
            }
        }
    }
    
    # Test with anomalous data (low quality)
    anomalous_validation_result = {
        "valid": True,
        "validation_score": 0.95,
        "errors": [],
        "validated_data": {
            "system_configuration": {
                "inverter_efficiency": 0.96,
                "panel_efficiency": 0.05,  # Unusually low efficiency (anomaly)
                "system_availability": 0.99,
                "maintenance_schedule": "quarterly",
                "monitoring_enabled": True
            },
            "performance_metrics": {
                "annual_output_kwh": 800,  # Very low output for the system size
                "capacity_factor": 0.03,   # Unusually low capacity factor
                "system_losses": 0.05,
                "availability_factor": 0.98
            },
            "financial_metrics": {
                "roi_percentage": 2.1,     # Very low ROI
                "payback_period_years": 45.2,  # Extremely long payback
                "lifetime_savings": 5000   # Very low savings
            }
        }
    }
    
    binary_result = {
        "success": True,
        "binary_data": b"test binary data",
        "file_path": "/tmp/test.bin",
        "checksum": "abc123",
        "size": 1024
    }
    
    print("=== NORMAL DATA ANALYSIS ===")
    normal_result = await dam.analyze_data(normal_validation_result, binary_result)
    print(f"Success: {normal_result.get('success')}")
    
    # Analyze quality results
    quality_result = normal_result.get("results", {}).get("quality", {})
    print(f"Quality success: {quality_result.get('success')}")
    if quality_result.get('success'):
        quality_data = quality_result.get("quality", {})
        print(f"Overall quality score: {quality_data.get('overall_quality_score')}")
        print(f"Quality components: {quality_data.get('quality_components', {}).keys()}")
        
        # Check individual quality components
        for component, data in quality_data.get('quality_components', {}).items():
            print(f"  {component}: {data.get('quality_score')}")
    
    # Analyze decision results
    decision_result = normal_result.get("results", {}).get("decision", {})
    print(f"Decision success: {decision_result.get('success')}")
    if decision_result.get('success'):
        print(f"Decision data: {decision_result}")
    
    # Analyze anomaly results
    anomaly_result = normal_result.get("results", {}).get("anomaly", {})
    print(f"Anomaly success: {anomaly_result.get('success')}")
    if anomaly_result.get('success'):
        anomaly_data = anomaly_result.get("anomalies", {})
        print(f"Anomalies detected: {len(anomaly_data.get('anomalies_detected', []))}")
        print(f"Anomaly types: {anomaly_data.get('anomaly_types', [])}")
    
    print("\n=== ANOMALOUS DATA ANALYSIS ===")
    anomalous_result = await dam.analyze_data(anomalous_validation_result, binary_result)
    print(f"Success: {anomalous_result.get('success')}")
    
    # Analyze quality results
    quality_result = anomalous_result.get("results", {}).get("quality", {})
    print(f"Quality success: {quality_result.get('success')}")
    if quality_result.get('success'):
        quality_data = quality_result.get("quality", {})
        print(f"Overall quality score: {quality_data.get('overall_quality_score')}")
        print(f"Quality components: {quality_data.get('quality_components', {}).keys()}")
        
        # Check individual quality components
        for component, data in quality_data.get('quality_components', {}).items():
            print(f"  {component}: {data.get('quality_score')}")
    
    # Analyze decision results
    decision_result = anomalous_result.get("results", {}).get("decision", {})
    print(f"Decision success: {decision_result.get('success')}")
    if decision_result.get('success'):
        print(f"Decision data: {decision_result}")
    
    # Analyze anomaly results
    anomaly_result = anomalous_result.get("results", {}).get("anomaly", {})
    print(f"Anomaly success: {anomaly_result.get('success')}")
    if anomaly_result.get('success'):
        anomaly_data = anomaly_result.get("anomalies", {})
        print(f"Anomalies detected: {len(anomaly_data.get('anomalies_detected', []))}")
        print(f"Anomaly types: {anomaly_data.get('anomaly_types', [])}")
        if anomaly_data.get('anomalies_detected'):
            for anomaly in anomaly_data['anomalies_detected']:
                print(f"  - {anomaly.get('type')}: {anomaly.get('description')}")
    
    await dam.stop()

if __name__ == "__main__":
    asyncio.run(debug_dam_analysis()) 