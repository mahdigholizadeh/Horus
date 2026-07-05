#!/usr/bin/env python3
"""
Debug script to test IPM with the exact test data.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

async def debug_ipm():
    """Debug IPM with test data."""
    from IPM.ipm import InputProcessingModule
    
    ipm = InputProcessingModule()
    await ipm.start()
    
    # Test with clean data
    clean_data = {
        "request_id": "REQ-001",
        "template_data": {
            "system_id": "SOLAR-001",
            "inverter": {
                "model": "SMA-SB3000",
                "capacity_kw": 3.0,
                "efficiency": 0.96
            },
            "panels": [
                {
                    "model": "SunPower-X22",
                    "wattage": 360,
                    "quantity": 8,
                    "efficiency": 0.225
                }
            ]
        },
        "processing_options": {
            "analysis_type": "comprehensive",
            "include_binary": True,
            "validation_level": "strict"
        }
    }
    
    result = await ipm.process_input(clean_data)
    print("Clean data result:")
    print(f"Valid: {result.get('valid')}")
    print(f"Error: {result.get('error', 'None')}")
    
    await ipm.stop()

if __name__ == "__main__":
    asyncio.run(debug_ipm()) 