"""
Text Processing Data Module (TPDM) for TPP Microservice
"""

import logging
import asyncio
from typing import Dict, Any
from datetime import datetime

class TextProcessingDataModule:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.module_name = "TPDM"
        self.is_active = False
        self.stats = {
            "total_processed": 0,
            "total_words": 0,
            "total_characters": 0,
            "processing_time": 0.0,
            "last_activity": None
        }
        self.logger.info(f"{self.module_name} initialized successfully")
    
    async def start(self):
        try:
            self.is_active = True
            self.logger.info(f"{self.module_name} started successfully")
        except Exception as e:
            self.logger.error(f"Failed to start {self.module_name}: {e}")
            raise
    
    async def process_text(self, text_data, language_result):
        try:
            text = text_data.get("message_text", "")
            return {
                "success": True,
                "processed_text": text,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_status(self):
        return {
            "module": self.module_name,
            "is_active": self.is_active,
            "statistics": self.stats,
            "timestamp": datetime.now().isoformat()
        }
    
    async def health_check(self):
        try:
            test_data = {"message_text": "Test"}
            result = await self.process_text(test_data, {"language": "en"})
            return {
                "healthy": self.is_active and result.get("success", False),
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