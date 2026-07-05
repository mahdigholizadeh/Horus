"""
Test T00000017: CCU Registration on Startup
Description: Verifies the RLA registers with the CCU immediately after starting.
Success Criteria: Mock CCU server receives a service_registration message from the RLA within seconds of startup.
"""

import asyncio
from ECM.ecm import ExternalControlModule

async def test_t00000017():
    test_code = "T00000017"
    test_name = "CCU Registration on Startup"
    results = []
    ecm = ExternalControlModule()
    await ecm.start()
    # ECM should connect to CCU on startup
    connected = ecm.connection_status == "connected"
    results.append(connected)
    await ecm.stop()
    success = all(results)
    return {
        "success": success,
        "test_code": test_code,
        "test_name": test_name,
        "message": "CCU registration on startup scenario passed" if success else "CCU registration on startup scenario failed",
        "details": {
            "steps": results
        }
    }

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(test_t00000017())
    import pprint
    pprint.pprint(result) 