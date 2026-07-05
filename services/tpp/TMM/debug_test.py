import asyncio

async def debug_test():
    print("Debug test starting...")
    return {"success": True, "message": "Debug test passed"}

if __name__ == "__main__":
    print("Starting debug test...")
    result = asyncio.run(debug_test())
    print(f"Result: {result}") 