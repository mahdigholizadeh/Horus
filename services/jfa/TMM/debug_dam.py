#!/usr/bin/env python3
"""
Debug script to test DAM analysis and see the actual return structure.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_dam_analysis():
    """Test DAM analysis with sample data."""
    from DAM.dam import DataAnalysisModule
    
    dam = DataAnalysisModule()
    await dam.start()
    
    # Test with validation and binary results
    validation_result = {
        "valid": True,
        "validation_score": 0.95,
        "errors": [],
        "validated_data": {"test": "data"}
    }
    
    binary_result = {
        "success": True,
        "binary_data": b"test binary data",
        "file_path": "/tmp/test.bin",
        "checksum": "abc123",
        "size": 1024
    }
    
    result = await dam.analyze_data(validation_result, binary_result)
    print("DAM Analysis Result:")
    print(f"Success: {result.get('success')}")
    print(f"Results structure: {result.get('results', {}).keys()}")
    
    if 'quality' in result.get('results', {}):
        quality = result['results']['quality']
        print(f"Quality result: {quality}")
        if quality.get('success') and 'quality' in quality:
            quality_data = quality['quality']
            print(f"Quality score: {quality_data.get('overall_quality_score', 'NOT_FOUND')}")
        else:
            print(f"Quality score: {quality.get('quality_score', 'NOT_FOUND')}")
    
    if 'anomaly' in result.get('results', {}):
        anomaly = result['results']['anomaly']
        print(f"Anomaly result: {anomaly}")
        if anomaly.get('success') and 'anomalies' in anomaly:
            anomaly_data = anomaly['anomalies']
            print(f"Anomalies detected: {anomaly_data.get('anomalies_detected', 'NOT_FOUND')}")
        else:
            print(f"Anomalies detected: {anomaly.get('anomalies_detected', 'NOT_FOUND')}")
    
    await dam.stop()

if __name__ == "__main__":
    asyncio.run(test_dam_analysis()) 