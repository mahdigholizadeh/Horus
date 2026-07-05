#!/usr/bin/env python3
"""
Debug script to test ARM module directly.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

async def debug_arm():
    """Debug ARM module."""
    from ARM.arm import APIRequestModule
    
    arm = APIRequestModule()
    await arm.start()
    
    print("ARM module started")
    print(f"Status: {arm.get_status()}")
    print(f"Health: {await arm.health_check()}")
    
    await arm.stop()

if __name__ == "__main__":
    asyncio.run(debug_arm())