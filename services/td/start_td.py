#!/usr/bin/env python3
"""
TD Microservice Startup Script

This script starts the TD (Task Divider) microservice with all modules.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from TD_main import TDMicroservice


async def main():
    """Main startup function."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('td_service.log')
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Starting TD Microservice...")
    
    # Create TD microservice instance
    td_service = TDMicroservice()
    
    try:
        # Start the service
        await td_service.start()
        
        logger.info("TD Microservice started successfully")
        logger.info("Service is running on:")
        logger.info(f"  - API Server: http://localhost:8003")
        logger.info(f"  - Health Check: http://localhost:8003/health")
        logger.info(f"  - WebSocket: ws://localhost:11492")
        logger.info("Press Ctrl+C to stop the service")
        
        # Keep the service running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
            
    except Exception as e:
        logger.error(f"Error running TD microservice: {e}")
        sys.exit(1)
    finally:
        # Stop the service
        logger.info("Stopping TD Microservice...")
        await td_service.stop()
        logger.info("TD Microservice stopped")


if __name__ == "__main__":
    asyncio.run(main()) 