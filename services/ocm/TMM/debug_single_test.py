#!/usr/bin/env python3
"""
Debug Single Test - Test routing response specifically
"""

import asyncio
import json
import sys
import os
import uuid
from pathlib import Path
from datetime import datetime

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

async def debug_routing_test():
    """Debug routing test specifically."""
    print("=== Debug Routing Test ===")
    
    try:
        from RCMIM.rcmim import RCMInteractionModule
        
        # Initialize RCMIM
        config = {
            "validation_enabled": True,
            "max_response_size": 10 * 1024 * 1024,  # 10MB
            "max_processing_time": 30.0
        }
        
        rcmim = RCMInteractionModule(config)
        await rcmim.start()
        
        # Create routing test data
        routing_response_data = {
            "request_id": str(uuid.uuid4()),
            "response_type": "interaction_continuation",
            "status": "received",
            "received_at": datetime.now().isoformat(),
            "response_data": {
                "continuation_message": "I'll continue with the analysis based on your previous request.",
                "analysis_type": "financial",
                "parameters": {
                    "time_period": "Q1 2024",
                    "metrics": ["revenue", "profit", "growth"],
                    "format": "detailed_report"
                },
                "estimated_completion": "2 minutes"
            },
            "user_id": "user_12348",
            "session_id": "session_67892",
            "conversation_id": "conv_11113",
            "rcm_instance_id": "rcm-instance-003",
            "priority_level": "A",
            "requires_immediate_delivery": True,
            "routing_info": {
                "destination": "user_interface",
                "priority": "high",
                "delivery_method": "websocket"
            }
        }
        
        print(f"Testing routing response: {routing_response_data['request_id']}")
        
        # Test response routing
        routing_success = await rcmim.receive_rcm_response(routing_response_data)
        print(f"Routing success: {routing_success}")
        
        # Wait a moment for processing
        await asyncio.sleep(0.1)
        
        # Verify routing
        routing_status = rcmim.get_response_status(routing_response_data["request_id"])
        print(f"Routing status exists: {routing_status is not None}")
        
        if routing_status:
            print("Status keys:", list(routing_status.keys()))
            print("Response data keys:", list(routing_status.get('response_data', {}).keys()))
            
            # Check for routing fields
            print(f"routing_completed in status: {'routing_completed' in routing_status}")
            print(f"routing_destination in status: {'routing_destination' in routing_status}")
            
            # Check response_data for routing_result
            response_data = routing_status.get('response_data', {})
            print(f"routing_result in response_data: {'routing_result' in response_data}")
            
            if 'routing_result' in response_data:
                print("Routing result:", response_data['routing_result'])
        
        await rcmim.stop()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_routing_test()) 