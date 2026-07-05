#!/usr/bin/env python3
"""
Debug script to test failing modules individually.
"""

import asyncio
import sys
import os
import tempfile
import time
from pathlib import Path

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_arm():
    """Test ARM module."""
    print("Testing ARM module...")
    try:
        from ARM.arm import APIRequestModule
        
        arm = APIRequestModule()
        await arm.start()
        
        print(f"ARM status: {arm.get_status()}")
        print(f"ARM health: {await arm.health_check()}")
        
        await arm.stop()
        return True
    except Exception as e:
        print(f"ARM error: {e}")
        return False

async def test_cim():
    """Test CIM module."""
    print("Testing CIM module...")
    try:
        from CIM.cim import ConfigurationInterfaceModule
        
        cim = ConfigurationInterfaceModule()
        await cim.start()
        
        # Test configuration
        config = cim.get_configuration()
        print(f"CIM config sections: {list(config.keys())}")
        
        # Test environment variable
        os.environ["JFA_LOG_LEVEL"] = "DEBUG"
        await cim._load_environment_variables()
        log_level = cim.get_config_value("logging.level")
        print(f"CIM log level: {log_level}")
        
        await cim.stop()
        return True
    except Exception as e:
        print(f"CIM error: {e}")
        return False

async def test_emm():
    """Test EMM module."""
    print("Testing EMM module...")
    try:
        from EMM.emm import ErrorManagementModule
        
        emm = ErrorManagementModule()
        await emm.start()
        
        # Test error handling
        error_result = await emm.handle_error(
            error_type="TestError",
            error_message="Test error message",
            module="TMM",
            function="test_function"
        )
        print(f"EMM error result: {error_result.get('success')}")
        
        await emm.stop()
        return True
    except Exception as e:
        print(f"EMM error: {e}")
        return False

async def test_msm():
    """Test MSM module."""
    print("Testing MSM module...")
    try:
        from MSM.msm import MonitoringSystemModule
        
        msm = MonitoringSystemModule()
        await msm.start()
        
        # Test metrics
        await msm.record_template_processed(
            template_id="TEST-001",
            processing_time=0.5,
            success=True,
            size_bytes=1024
        )
        
        metrics = await msm.get_monitoring_data()
        print(f"MSM templates processed: {metrics.get('templates_processed')}")
        
        await msm.stop()
        return True
    except Exception as e:
        print(f"MSM error: {e}")
        return False

async def test_btm():
    """Test BTM module."""
    print("Testing BTM module...")
    try:
        from BTM.btm import BackgroundTasksModule
        
        btm = BackgroundTasksModule()
        await btm.start()
        
        # Test task scheduling
        result = await btm.schedule_task(
            task_name="test_task",
            task_function="test_function",
            task_args={"test": "data"},
            delay_seconds=1
        )
        print(f"BTM task scheduled: {result.get('success')}")
        
        await asyncio.sleep(1)
        
        await btm.stop()
        return True
    except Exception as e:
        print(f"BTM error: {e}")
        return False

async def main():
    """Run all module tests."""
    print("🔍 Debugging Failing Modules...")
    
    results = []
    results.append(await test_arm())
    results.append(await test_cim())
    results.append(await test_emm())
    results.append(await test_msm())
    results.append(await test_btm())
    
    print(f"\n📊 Results: {sum(results)}/{len(results)} modules working")
    
    modules = ["ARM", "CIM", "EMM", "MSM", "BTM"]
    for i, result in enumerate(results):
        status = "✅" if result else "❌"
        print(f"   {status} {modules[i]}")

if __name__ == "__main__":
    asyncio.run(main()) 