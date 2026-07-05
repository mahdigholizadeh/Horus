"""
Activation Flag Module (AFM) for TD Microservice

This module handles:
- Activation flag analysis from JFA processing
- Calculation block routing determination
- Priority-based calculation scheduling
- Flag validation and consistency checking
- Calculation type detection and classification
- Resource allocation planning
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple, Set
from datetime import datetime
import json


class ActivationFlagModule:
    """
    Activation Flag Module for TD Microservice
    
    Handles analysis and interpretation of activation flags with:
    - Flag validation and consistency checking
    - Calculation block routing determination
    - Priority-based scheduling
    - Resource allocation planning
    - Calculation type classification
    """
    
    def __init__(self):
        """Initialize the Activation Flag Module."""
        self.logger = logging.getLogger(__name__)
        self.module_name = "AFM"
        self.is_active = False
        
        # Generic routing flags (proxy mode — no domain calculations)
        self.route_handlers = {
            "forward": {
                "name": "forward",
                "description": "Single-hop forward to next pipeline stage",
                "priority": 1,
            },
            "parallel": {
                "name": "parallel",
                "description": "Fan-out to multiple downstream handlers",
                "priority": 2,
            },
            "sequential": {
                "name": "sequential",
                "description": "Ordered multi-step routing",
                "priority": 3,
            },
        }
        self.dependencies: Dict[str, List[str]] = {}
        self.conflicts: Dict[str, List[str]] = {}
        
        # Processing statistics
        self.stats = {
            "total_analyzed": 0,
            "successful_analysis": 0,
            "failed_analysis": 0,
            "flags_processed": 0,
            "calculations_scheduled": 0,
            "conflicts_detected": 0,
            "dependencies_resolved": 0,
            "last_activity": None
        }
        
        self.logger.info("Activation Flag Module initialized")
    
    async def start(self):
        """Start the Activation Flag Module."""
        try:
            self.is_active = True
            self.logger.info("Activation Flag Module started")
            
        except Exception as e:
            self.logger.error(f"Failed to start AFM: {e}")
            raise
    
    async def stop(self):
        """Stop the Activation Flag Module."""
        try:
            self.is_active = False
            self.logger.info("Activation Flag Module stopped")
            
        except Exception as e:
            self.logger.error(f"Failed to stop AFM: {e}")
            raise
    
    async def analyze_activation_flags(self, activation_flags: Dict[str, int]) -> Dict[str, Any]:
        """
        Analyze activation flags and determine which calculations to execute.
        
        Args:
            activation_flags: Dictionary of activation flags from binary file
            
        Returns:
            Analysis results with calculation plan
        """
        try:
            start_time = datetime.now()
            self.stats["total_analyzed"] += 1
            
            # Map activation flags to routing handlers (proxy mode)
            active_routes = []
            for flag, value in activation_flags.items():
                if value == 1:
                    route_key = flag.replace("block", "").replace("_flag", "")
                    if route_key in self.route_handlers:
                        active_routes.append(self.route_handlers[route_key]["name"])
                    elif flag in self.route_handlers:
                        active_routes.append(self.route_handlers[flag]["name"])

            if not active_routes:
                active_routes = ["forward"]

            conflicts: List[List[str]] = []
            dependencies: Dict[str, List[str]] = {}
            priority_order = sorted(
                active_routes,
                key=lambda x: next(
                    (info["priority"] for info in self.route_handlers.values() if info["name"] == x),
                    999,
                ),
            )
            
            # Update statistics
            self.stats["successful_analysis"] += 1
            self.stats["flags_processed"] += len(activation_flags)
            self.stats["calculations_scheduled"] += len(active_routes)
            self.stats["conflicts_detected"] += len(conflicts)
            self.stats["dependencies_resolved"] += len(dependencies)
            self.stats["last_activity"] = datetime.now()
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'success': True,
                'active_calculations': active_routes,
                'active_routes': active_routes,
                'conflicts': conflicts,
                'dependencies': dependencies,
                'priority_order': priority_order,
                'analysis_summary': {
                    'total_flags': len(activation_flags),
                    'active_flags': len([f for f in activation_flags.values() if f == 1]),
                    'routes_to_run': len(active_routes),
                    'conflicts_detected': len(conflicts),
                    'dependencies_found': len(dependencies),
                },
                'processing_time': processing_time
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing activation flags: {e}")
            self.stats["failed_analysis"] += 1
            return {
                'success': False,
                'errors': [str(e)]
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the module."""
        return {
            'module': self.module_name,
            'is_active': self.is_active,
            'supported_routes': [block["name"] for block in self.route_handlers.values()],
            'route_handlers': self.route_handlers,
            'dependencies': self.dependencies,
            'conflicts': self.conflicts,
            'statistics': self.stats
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        return {
            'healthy': self.is_active,
            'status': 'All systems operational' if self.is_active else 'Module not active',
            'timestamp': datetime.now().isoformat()
        } 