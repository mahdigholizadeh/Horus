#!/usr/bin/env python3
"""
Debug script to test TVM validation with invalid values.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_tvm_validation():
    """Test TVM validation with invalid mpsz value."""
    from TVM.tvm import TemplateValidationModule
    
    tvm = TemplateValidationModule()
    await tvm.start()
    
    # Test with invalid mpsz value
    invalid_template = {
        "id": "SOLAR-002",
        "object": "horus.request",
        "created": 1234567891,
        "model": "horus-v1.0",
        "jfa_data": {
            "flag": {
                "vald": 1, "calc": 1, "plat": 1, "mpsz": 2,  # Invalid value
                "econ": 1, "rcon": 1, "mode": 1
            },
            "loca": {
                "Ecit": "Tehran", "Fcit": "Tehran",
                "lat": 35.6892, "lng": 51.3890
            },
            "cust": {
                "mode": 1, "need": 1, "npsz": 5
            },
            "sinf": {
                "mfreg": 1, "mled": 2, "mlcd": 1, "mtele": 1,
                "mlamp": 5, "mpump": 1, "mcool": 1, "mcamd": 1,
                "mpc": 2, "mpri": 1, "mwel": 1, "mmlo": 1,
                "nfreg": 1, "nled": 2, "nlcd": 1, "ntele": 1,
                "nlamp": 5, "npump": 1, "ncool": 1, "ncamd": 1,
                "npc": 2, "npri": 1, "nwel": 1, "nmlo": 1
            }
        }
    }
    
    result = await tvm.validate_template(invalid_template)
    print("TVM Validation Result:")
    print(f"Valid: {result.get('valid')}")
    print(f"Errors: {result.get('errors')}")
    print(f"Validation Details: {result.get('validation_details')}")
    
    await tvm.stop()

if __name__ == "__main__":
    asyncio.run(test_tvm_validation()) 