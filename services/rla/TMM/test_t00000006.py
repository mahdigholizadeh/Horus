"""
Test T00000006: DRM (Data Receiver Module) Unit Test
Module(s) Tested: DRM
Description: Verifies the secure data reception protocol and handshake on port 3781.
Success Criteria: Correct sequence is processed successfully, incorrect sequences result in error or connection drop.
"""

import asyncio
import struct
import json
from DRM.drm import DataReceiverModule

async def test_t00000006():
    test_code = "T00000006"
    test_name = "DRM - Data Reception Protocol"
    results = []
    drm = DataReceiverModule()
    await drm.start()
    # Prepare protocol constants
    R1 = drm.protocol_markers['handshake_start']
    R2 = drm.protocol_markers['handshake_end']
    # Step 1: Correct handshake sequence
    payload = {"field": "value"}
    payload_bytes = json.dumps(payload).encode('utf-8')
    data = struct.pack('>I', R1) + struct.pack('>I', len(payload_bytes)) + payload_bytes + struct.pack('>I', R2)
    result1 = await drm._process_rla_protocol(data)
    results.append(result1.get('success', False))
    # Step 2: Incorrect R1 marker
    bad_r1 = 0xDEADBEEF
    data_bad_r1 = struct.pack('>I', bad_r1) + struct.pack('>I', len(payload_bytes)) + payload_bytes + struct.pack('>I', R2)
    result2 = await drm._process_rla_protocol(data_bad_r1)
    results.append(
        not result2.get('success', True) and 'R1' in result2.get('error', '')
    )
    # Step 3: Correct R1, incorrect R2 marker
    bad_r2 = 0xFEEDBEEF
    data_bad_r2 = struct.pack('>I', R1) + struct.pack('>I', len(payload_bytes)) + payload_bytes + struct.pack('>I', bad_r2)
    result3 = await drm._process_rla_protocol(data_bad_r2)
    results.append(
        not result3.get('success', True) and 'R2' in result3.get('error', '')
    )
    await drm.stop()
    success = all(results)
    return {
        "success": success,
        "test_code": test_code,
        "test_name": test_name,
        "message": "All DRM data reception protocol scenarios passed" if success else "Some DRM data reception protocol scenarios failed",
        "details": {
            "steps": results,
            "step_results": [result1, result2, result3]
        }
    }

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(test_t00000006())
    import pprint
    pprint.pprint(result) 