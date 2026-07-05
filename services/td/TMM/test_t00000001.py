"""TD proxy smoke tests."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from CIM.cim import CalculationInterfaceModule


async def test_cim_passthrough_route():
    """CIM forwards payload without domain computation."""
    cim = CalculationInterfaceModule()
    await cim.start()
    result = await cim.execute_calculation(
        "forward",
        {"technical_data": {"request_id": "test-001", "message": "hello"}},
        "req_test_001",
    )
    await cim.stop()
    assert result["success"] is True
    assert result.get("proxy_mode") is True
    assert result["route"] == "forward"
    return result


async def test_cim_health():
    cim = CalculationInterfaceModule()
    await cim.start()
    health = await cim.health_check()
    await cim.stop()
    assert health["healthy"] is True
    return health
