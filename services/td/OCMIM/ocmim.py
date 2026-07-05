"""
OCM Interface Module (OCMIM) for TD Microservice

This module handles:
- OCM formatting and preparation
- Data structuring for OCM consumption
- Output validation and compliance
- OCM-specific data transformations
"""

import logging
import asyncio
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid


class OCMInterfaceModule:
    """OCM Interface Module for TD Microservice"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.module_name = "OCMIM"
        self.is_active = False
        self.stats = {
            "total_preparations": 0,
            "successful_preparations": 0,
            "failed_preparations": 0,
            "last_activity": None
        }
        self.logger.info("OCM Interface Module initialized")
    
    async def start(self):
        self.is_active = True
        self.logger.info("OCM Interface Module started")
    
    async def stop(self):
        self.is_active = False
        self.logger.info("OCM Interface Module stopped")
    
    async def prepare_for_ocm(self, aggregated_data: Dict[str, Any], 
                            metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for OCM consumption."""
        try:
            # Format for OCM
            ocm_formatted_data = {
                'ocm_request_id': metadata.get('request_id', ''),
                'calculations': aggregated_data.get('calculation_results', {}),
                'summary': aggregated_data.get('combined_summary', {}),
                'recommendations': aggregated_data.get('recommendations', []),
                'metadata': {
                    'processing_timestamp': datetime.now().isoformat(),
                    'data_source': 'TD_microservice',
                    'format_version': '1.0',
                    'calculations_executed': metadata.get('calculations_executed', [])
                }
            }
            
            self.stats["total_preparations"] += 1
            self.stats["successful_preparations"] += 1
            self.stats["last_activity"] = datetime.now()
            
            return {
                'success': True,
                'ocm_formatted_data': ocm_formatted_data
            }
            
        except Exception as e:
            self.stats["failed_preparations"] += 1
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_status(self) -> Dict[str, Any]:
        return {
            'module': self.module_name,
            'is_active': self.is_active,
            'statistics': self.stats
        }
    
    async def health_check(self) -> Dict[str, Any]:
        return {
            'healthy': self.is_active,
            'status': 'All systems operational' if self.is_active else 'Module not active',
            'timestamp': datetime.now().isoformat()
        } 