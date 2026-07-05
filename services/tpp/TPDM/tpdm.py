"""
Text Processing Data Module (TPDM) for TPP Microservice

Comprehensive text processing with preprocessing, normalization, and analysis.
Based on TPP_CONFIGURATION_PLAN.md specifications.
"""

import logging
import asyncio
import re
import unicodedata
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import Counter


class TextProcessingDataModule:
    """
    Comprehensive Text Processing Data Module with multi-language support
    """
    
    def __init__(self):
        """Initialize the TPDM module."""
        self.logger = logging.getLogger(__name__)
        self.module_name = "TPDM"
        self.is_active = False
        
        # Processing configuration
        self.config = {
            "preserve_word_order": True,
            "normalize_unicode": True,
            "remove_extra_whitespace": True,
            "max_text_length": 100000,
            "enable_text_metrics": True
        }
        
        # Persian character normalization
        self.persian_normalization = {
            'ي': 'ی', 'ك': 'ک',  # Arabic to Persian
            '٠': '۰', '١': '۱', '٢': '۲', '٣': '۳', '٤': '۴',
            '٥': '۵', '٦': '۶', '٧': '۷', '٨': '۸', '٩': '۹'
        }
        
        # Processing statistics
        self.stats = {
            "total_processed": 0,
            "successful_processing": 0,
            "failed_processing": 0,
            "total_characters_processed": 0,
            "average_processing_time": 0.0,
            "last_activity": None
        }
        
        self.logger.info(f"{self.module_name} initialized with comprehensive text processing")
    
    async def start(self):
        """Start the TPDM module."""
        try:
            self.is_active = True
            self.logger.info(f"{self.module_name} started successfully")
        except Exception as e:
            self.logger.error(f"Failed to start {self.module_name}: {e}")
            raise
    
    async def process_text(self, text_data: Dict[str, Any], language_result: Dict[str, Any]) -> Dict[str, Any]:
        """Process text with comprehensive preprocessing and analysis."""
        try:
            if not self.is_active:
                raise RuntimeError(f"{self.module_name} is not active")
            
            start_time = datetime.now()
            original_text = text_data.get("message_text", "")
            language = language_result.get("language", "unknown").lower()
            
            # Validate input
            if not original_text or len(original_text) > self.config["max_text_length"]:
                return self._create_error_response("Invalid text input", text_data)
            
            # Preprocess text
            processed_text = await self._preprocess_text(original_text, language)
            
            # Analyze text
            analysis = self._analyze_text(processed_text, language)
            
            # Calculate metrics
            processing_time = (datetime.now() - start_time).total_seconds()
            metrics = self._create_metrics(original_text, processed_text, processing_time)
            
            # Update statistics
            self._update_stats(original_text, processing_time, True)
            
            return {
                "success": True,
                "processed_text": processed_text,
                "original_text": original_text,
                "language": language,
                "analysis": analysis,
                "metrics": metrics,
                "stats": {
                    "character_count": len(processed_text),
                    "word_count": len(processed_text.split()) if processed_text else 0,
                    "processing_time": processing_time
                },
                "processing_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error processing text: {e}")
            self._update_stats(text_data.get("message_text", ""), 0, False)
            return self._create_error_response(str(e), text_data)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current module status."""
        return {
            "module": self.module_name,
            "is_active": self.is_active,
            "statistics": self.stats,
            "timestamp": datetime.now().isoformat()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            # Test basic processing
            test_data = {"message_text": "سلام Hello"}
            test_lang = {"language": "persian"}
            result = await self.process_text(test_data, test_lang)
            
            return {
                "healthy": self.is_active and result["success"],
                "module": self.module_name,
                "test_result": "passed" if result["success"] else "failed",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "healthy": False,
                "module": self.module_name,
                "test_result": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _preprocess_text(self, text: str, language: str) -> str:
        """Preprocess text based on language rules."""
        try:
            processed = text
            
            # Unicode normalization
            if self.config["normalize_unicode"]:
                processed = unicodedata.normalize('NFKC', processed)
            
            # Persian-specific normalization
            if language == "persian":
                for arabic_char, persian_char in self.persian_normalization.items():
                    processed = processed.replace(arabic_char, persian_char)
            
            # Whitespace normalization
            if self.config["remove_extra_whitespace"]:
                processed = re.sub(r'\s+', ' ', processed).strip()
            
            return processed
            
        except Exception as e:
            self.logger.error(f"Error preprocessing text: {e}")
            return text
    
    def _analyze_text(self, text: str, language: str) -> Dict[str, Any]:
        """Analyze text characteristics."""
        try:
            if not text:
                return {"character_types": {}, "complexity": "low"}
            
            # Character analysis
            persian_chars = len(re.findall(r'[\u0600-\u06FF]', text))
            english_chars = len(re.findall(r'[a-zA-Z]', text))
            digits = len(re.findall(r'\d', text))
            
            # Basic complexity
            words = text.split()
            avg_word_length = sum(len(w) for w in words) / len(words) if words else 0
            unique_words = len(set(words))
            
            return {
                "character_types": {
                    "persian": persian_chars,
                    "english": english_chars,
                    "digits": digits,
                    "total": len(text)
                },
                "word_analysis": {
                    "total_words": len(words),
                    "unique_words": unique_words,
                    "average_length": round(avg_word_length, 2)
                },
                "complexity": "high" if avg_word_length > 6 else "medium" if avg_word_length > 4 else "low"
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing text: {e}")
            return {"error": str(e)}
    
    def _create_metrics(self, original: str, processed: str, time_taken: float) -> Dict[str, Any]:
        """Create processing metrics."""
        return {
            "processing_time": round(time_taken, 4),
            "character_reduction": len(original) - len(processed),
            "processing_speed": round(len(original) / time_taken, 2) if time_taken > 0 else 0,
            "efficiency": round(len(processed) / len(original), 3) if original else 1
        }
    
    def _update_stats(self, text: str, processing_time: float, success: bool):
        """Update processing statistics."""
        try:
            self.stats["total_processed"] += 1
            if success:
                self.stats["successful_processing"] += 1
                self.stats["total_characters_processed"] += len(text)
                
                # Update average processing time
                total = self.stats["successful_processing"]
                current_avg = self.stats["average_processing_time"]
                self.stats["average_processing_time"] = (
                    (current_avg * (total - 1) + processing_time) / total
                )
            else:
                self.stats["failed_processing"] += 1
                
            self.stats["last_activity"] = datetime.now().isoformat()
            
        except Exception as e:
            self.logger.error(f"Error updating stats: {e}")
    
    def _create_error_response(self, error: str, text_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create error response."""
        return {
            "success": False,
            "processed_text": text_data.get("message_text", ""),
            "original_text": text_data.get("message_text", ""),
            "error": error,
            "processing_timestamp": datetime.now().isoformat()
        } 