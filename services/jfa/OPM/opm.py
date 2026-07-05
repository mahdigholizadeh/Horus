"""
Output Processing Module (OPM) for JFA Microservice

This module handles output processing operations:
- Output formatting and preparation
- Metadata addition and enrichment
- Result structuring and validation
- Legacy compatibility formatting
"""

import logging
import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime


class OutputProcessingModule:
    """Output Processing Module for JFA"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.module_name = "OPM"
        self.is_active = False
        
        self.stats = {
            "total_processed": 0,
            "successful_processing": 0,
            "failed_processing": 0,
            "last_activity": None
        }
    
    async def start(self):
        self.is_active = True
        self.logger.info(f"{self.module_name} started successfully")
    
    async def stop(self):
        self.is_active = False
        self.logger.info(f"{self.module_name} stopped successfully")
    
    async def generate_output(self, original_data: Dict[str, Any], 
                             processing_results: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate formatted output from processing results."""
        try:
            self.stats["total_processed"] += 1
            
            # Create base output structure
            output_data = {
                "JFA_flag": 1,  # Legacy compatibility
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
            
            # Add validation results at top level
            if "validation" in processing_results:
                output_data["validation"] = processing_results["validation"]
            
            # Add binary generation results at top level
            if "binary_generation" in processing_results:
                output_data["binary_generation"] = processing_results["binary_generation"]
            
            # Add analysis results at top level
            if "analysis" in processing_results:
                output_data["analysis"] = processing_results["analysis"]
            
            # Add metadata at top level
            if "metadata" in processing_results:
                output_data["metadata"] = processing_results["metadata"]
            
            # Add processing summary
            output_data["processing_summary"] = {
                "total_processing_time": self._calculate_total_processing_time(processing_results),
                "success": True,
                "modules_executed": self._get_modules_used(processing_results)
            }
            
            # Add modules used at top level
            output_data["modules_used"] = self._get_modules_used(processing_results)
            
            self.stats["successful_processing"] += 1
            self.stats["last_activity"] = datetime.now()
            
            return {
                "success": True,
                "output": output_data,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error generating output: {e}")
            self.stats["failed_processing"] += 1
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _calculate_total_processing_time(self, processing_results: Dict[str, Any]) -> float:
        """Calculate total processing time from all results."""
        try:
            total_time = 0.0
            
            for result in processing_results.values():
                if isinstance(result, dict) and "processing_time" in result:
                    total_time += result["processing_time"]
            
            return total_time
            
        except Exception as e:
            self.logger.error(f"Error calculating processing time: {e}")
            return 0.0
    
    def _get_modules_used(self, processing_results: Dict[str, Any]) -> List[str]:
        """Get list of modules used in processing."""
        modules = []
        
        # Check for JDPM (JSON processing)
        if any("json" in key.lower() or "jdpm" in key.lower() for key in processing_results.keys()):
            modules.append("JDPM")
        elif "validation" in processing_results:  # If validation exists, JDPM was likely used
            modules.append("JDPM")
        
        if "validation" in processing_results:
            modules.append("TVM")
        if "binary_generation" in processing_results:
            modules.append("BDM")
        if "analysis" in processing_results:
            modules.append("DAM")
        
        return modules
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "module": self.module_name,
            "is_active": self.is_active,
            "statistics": self.stats,
            "timestamp": datetime.now().isoformat()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        try:
            test_data = {"id": "test-001"}
            test_results = {"validation": {"valid": True, "processing_time": 0.1}}
            result = await self.generate_output(test_data, test_results)
            
            return {
                "healthy": self.is_active and result["success"],
                "module": self.module_name,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "healthy": False,
                "module": self.module_name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            } 