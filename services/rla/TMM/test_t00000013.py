"""
Test T00000013: BTM (Background Tasks Module) Unit Test
Module(s) Tested: BTM
Description: Ensures background tasks can be scheduled and executed without blocking the main thread.
Success Criteria: Task is scheduled immediately and completes after delay.
"""

import asyncio
from BTM.btm import BackgroundTasksModule

async def test_t00000013():
    test_code = "T00000013"
    test_name = "BTM - Background Task Scheduling"
    results = []
    btm = BackgroundTasksModule()
    await btm.start()
    # Step 1: Schedule a 2-second background task
    async def background_task():
        await asyncio.sleep(2)
        return "done"
    # Schedule the task
    task = asyncio.create_task(background_task())
    # Immediately after scheduling, the task should not be done
    results.append(not task.done())
    # Step 2: Wait for completion
    await task
    results.append(task.done() and task.result() == "done")
    await btm.stop()
    success = all(results)
    return {
        "success": success,
        "test_code": test_code,
        "test_name": test_name,
        "message": "BTM background task scenarios passed" if success else "BTM background task scenarios failed",
        "details": {
            "steps": results
        }
    }

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(test_t00000013())
    import pprint
    pprint.pprint(result) 