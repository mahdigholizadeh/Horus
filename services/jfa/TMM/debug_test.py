#!/usr/bin/env python3
"""
Debug script to test individual JFA modules and understand their interfaces.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_jdpm():
    """Test JDPM module interface."""
    print("Testing JDPM module...")
    try:
        from JDPM.jdpm import JSONDataProcessingModule
        jdpm = JSONDataProcessingModule()
        await jdpm.start()
        
        # Test with valid template
        valid_template = {
            "id": "test-001",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "gpt-4",
            "choices": {
                "message": {
                    "role": "user",
                    "content": "Hello, world!"
                },
                "finish_reason": "stop"
            }
        }
        
        result = await jdpm.process_json_data(valid_template)
        print(f"JDPM result: {result.get('success', False)}")
        await jdpm.stop()
        return True
    except Exception as e:
        print(f"JDPM error: {e}")
        return False

async def test_tvm():
    """Test TVM module interface."""
    print("Testing TVM module...")
    try:
        from TVM.tvm import TemplateValidationModule
        tvm = TemplateValidationModule()
        await tvm.start()
        
        # Disable business rules for simpler testing
        tvm.validation_config["enable_business_rules"] = False
        
        # Test with valid template that includes JFA data
        valid_template = {
            "id": "SOLAR-001",
            "object": "horus.request",
            "created": 1234567890,
            "model": "horus-v1.0",
            "jfa_data": {
                "flag": {
                    "vald": 1, "calc": 1, "plat": 1, "mpsz": 1,
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
        
        result = await tvm.validate_template(valid_template)
        print(f"TVM result: {result.get('valid', False)}")
        await tvm.stop()
        return True
    except Exception as e:
        print(f"TVM error: {e}")
        return False

async def test_bdm():
    """Test BDM module interface."""
    print("Testing BDM module...")
    try:
        from BDM.bdm import BinaryDataModule
        bdm = BinaryDataModule()
        await bdm.start()
        
        # Test with simple data
        test_data = {"test": "data", "number": 42}
        result = await bdm.generate_binary_data(test_data)
        print(f"BDM result: {result.get('success', False)}")
        await bdm.stop()
        return True
    except Exception as e:
        print(f"BDM error: {e}")
        return False

async def test_dam():
    """Test DAM module interface."""
    print("Testing DAM module...")
    try:
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
            "checksum": "abc123"
        }
        
        result = await dam.analyze_data(validation_result, binary_result)
        print(f"DAM result: {result.get('success', False)}")
        await dam.stop()
        return True
    except Exception as e:
        print(f"DAM error: {e}")
        return False

async def main():
    """Run all module tests."""
    print("🔍 Debugging JFA Modules...")
    
    results = []
    results.append(await test_jdpm())
    results.append(await test_tvm())
    results.append(await test_bdm())
    results.append(await test_dam())
    
    print(f"\n📊 Results: {sum(results)}/{len(results)} modules working")
    
    for i, result in enumerate(results):
        status = "✅" if result else "❌"
        print(f"   {status} Module {i+1}")

if __name__ == "__main__":
    asyncio.run(main()) 