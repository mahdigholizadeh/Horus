"""
Routing and Orchestration Module (ROM) for TD Microservice

This module handles:
- Multi-calculation orchestration and coordination
- Workflow management and execution planning
- Concurrent calculation scheduling
- Resource management and allocation
- Calculation pipeline coordination
- Performance optimization and load balancing
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import json
import uuid


class RoutingOrchestrationModule:
    """
    Routing and Orchestration Module for TD Microservice
    
    Handles multi-calculation orchestration with:
    - Concurrent execution planning
    - Dependency management
    - Resource allocation
    - Performance optimization
    - Workflow coordination
    """
    
    def __init__(self):
        """Initialize the Routing and Orchestration Module."""
        self.logger = logging.getLogger(__name__)
        self.module_name = "ROM"
        self.is_active = False
        
        # Configuration
        self.config = {
            "max_concurrent_calculations": 12,
            "max_concurrent_orchestrations": 5,
            "orchestration_timeout": 300,  # 5 minutes
            "calculation_timeout": 120,  # 2 minutes per calculation
            "retry_attempts": 3,
            "retry_delay": 5
        }
        
        # Statistics
        self.stats = {
            "total_orchestrations": 0,
            "successful_orchestrations": 0,
            "failed_orchestrations": 0,
            "total_calculations_orchestrated": 0,
            "successful_calculations": 0,
            "failed_calculations": 0,
            "last_activity": None
        }
        
        self.logger.info("Routing and Orchestration Module initialized")
    
    async def start(self):
        """Start the Routing and Orchestration Module."""
        try:
            self.is_active = True
            self.logger.info("Routing and Orchestration Module started")
            
        except Exception as e:
            self.logger.error(f"Failed to start ROM: {e}")
            raise
    
    async def stop(self):
        """Stop the Routing and Orchestration Module."""
        try:
            self.is_active = False
            self.logger.info("Routing and Orchestration Module stopped")
            
        except Exception as e:
            self.logger.error(f"Failed to stop ROM: {e}")
            raise
    
    async def orchestrate_calculations(self, technical_data: Dict[str, Any], 
                                     active_calculations: List[str],
                                     request_id: str) -> Dict[str, Any]:
        """
        Orchestrate the execution of multiple calculations.
        
        Args:
            technical_data: Technical data from binary file processing
            active_calculations: List of calculations to execute
            request_id: Request identifier for tracking
            
        Returns:
            Orchestration plan and execution strategy
        """
        try:
            start_time = datetime.now()
            self.stats["total_orchestrations"] += 1
            
            # Create calculation plan
            calculation_plan = {}
            
            for calc_name in active_calculations:
                task_id = f"task_{uuid.uuid4().hex[:8]}"
                calculation_plan[calc_name] = {
                    'task_id': task_id,
                    'technical_data': technical_data,
                    'priority': self._get_calculation_priority(calc_name),
                    'estimated_time': self._get_estimated_time(calc_name),
                    'dependencies': self._get_dependencies(calc_name),
                    'resource_requirements': self._get_resource_requirements(calc_name)
                }
            
            # Calculate estimated total time
            estimated_total_time = self._calculate_estimated_time(active_calculations)
            
            # Create execution strategy
            execution_strategy = {
                'execution_pattern': 'parallel',
                'concurrency_level': min(len(active_calculations), self.config["max_concurrent_calculations"]),
                'enable_pipelining': True,
                'timeout_per_calculation': self.config["calculation_timeout"],
                'retry_configuration': {
                    'max_retries': self.config["retry_attempts"],
                    'retry_delay': self.config["retry_delay"]
                }
            }
            
            # Update statistics
            self.stats["successful_orchestrations"] += 1
            self.stats["total_calculations_orchestrated"] += len(active_calculations)
            self.stats["last_activity"] = datetime.now()
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'success': True,
                'calculation_plan': calculation_plan,
                'execution_strategy': execution_strategy,
                'orchestration_summary': {
                    'total_calculations': len(active_calculations),
                    'estimated_total_time': estimated_total_time,
                    'processing_time': processing_time
                },
                'request_id': request_id
            }
            
        except Exception as e:
            self.logger.error(f"Error orchestrating calculations: {e}")
            self.stats["failed_orchestrations"] += 1
            return {
                'success': False,
                'errors': [str(e)],
                'request_id': request_id
            }
    
    def _get_calculation_priority(self, calc_name: str) -> int:
        """Get priority for route handler."""
        priority_map = {"forward": 1, "parallel": 2, "sequential": 3}
        return priority_map.get(calc_name, 5)

    def _get_estimated_time(self, calc_name: str) -> int:
        """Get estimated time for route."""
        return {"forward": 5, "parallel": 15, "sequential": 20}.get(calc_name, 10)

    def _get_dependencies(self, calc_name: str) -> List[str]:
        """Get dependencies for route (proxy mode — none)."""
        return []

    def _get_resource_requirements(self, calc_name: str) -> Dict[str, str]:
        """Get resource requirements for route."""
        return {"cpu": "low", "memory": "low"}

    def _calculate_estimated_time(self, active_calculations: List[str]) -> int:
        """Calculate estimated total execution time."""
        # For parallel execution, use maximum time (assuming sufficient resources)
        max_time = max(self._get_estimated_time(calc) for calc in active_calculations) if active_calculations else 0
        return max_time
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the module."""
        return {
            'module': self.module_name,
            'is_active': self.is_active,
            'configuration': self.config,
            'statistics': self.stats,
            'capabilities': {
                'multi_calculation_orchestration': True,
                'dependency_management': True,
                'resource_optimization': True,
                'concurrent_execution': True,
                'performance_monitoring': True,
                'workflow_coordination': True
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        return {
            'healthy': self.is_active,
            'status': 'All systems operational' if self.is_active else 'Module not active',
            'orchestration_statistics': self.stats,
            'timestamp': datetime.now().isoformat()
        } 