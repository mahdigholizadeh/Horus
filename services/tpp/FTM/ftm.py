"""
Filter Text Module (FTM) for TPP Microservice

This module handles the core text filtering operations:
- Spam word removal with order preservation
- Multi-language filtering support
- Advanced filtering algorithms
- Performance optimization
- Statistical analysis of filtering results
"""

import logging
import asyncio
import re
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import unicodedata


class FilterTextModule:
    """
    Filter Text Module
    
    Core text filtering engine that removes spam words while preserving
    text structure and providing detailed filtering statistics.
    """
    
    def __init__(self):
        """Initialize the FTM module."""
        self.logger = logging.getLogger(__name__)
        self.module_name = "FTM"
        self.is_active = False
        
        # Filtering configuration
        self.filter_config = {
            "preserve_word_order": True,
            "preserve_punctuation": True,
            "preserve_spacing": True,
            "case_sensitive": True,
            "remove_partial_matches": False,
            "aggressive_filtering": False,
            "word_boundary_strict": True
        }
        
        # Persian text processing patterns
        self.persian_patterns = {
            "word_separator": r"[\s\u200C\u200D]+",  # Space, ZWNJ, ZWJ
            "punctuation": r"[۰-۹\u060C\u061B\u061F\u06D4\u06D5]",  # Persian punctuation
            "diacritics": r"[\u064B-\u065F\u0670\u06D6-\u06DC\u06DF-\u06E4\u06E7-\u06E8\u06EA-\u06ED]",
            "persian_letters": r"[\u0600-\u06FF]",
            "latin_letters": r"[a-zA-Z]",
            "mixed_script": r"[\u0600-\u06FF\u0020-\u007E]"
        }
        
        # Compiled regex patterns for performance
        self.compiled_patterns = {}
        
        # Filter statistics
        self.stats = {
            "total_texts_filtered": 0,
            "total_words_processed": 0,
            "total_spam_words_removed": 0,
            "total_characters_removed": 0,
            "average_filter_time": 0.0,
            "filter_effectiveness": 0.0,
            "language_distribution": {},
            "spam_category_distribution": {},
            "last_activity": None
        }
        
        # Performance metrics
        self.performance_metrics = {
            "words_per_second": 0.0,
            "average_text_length": 0.0,
            "average_reduction_percentage": 0.0,
            "filtering_accuracy": 0.0,
            "false_positive_rate": 0.0
        }
        
        self.logger.info(f"{self.module_name} initialized successfully")
    
    async def start(self):
        """Start the FTM module."""
        try:
            self.is_active = True
            
            # Compile regex patterns for performance
            await self._compile_patterns()
            
            self.logger.info(f"{self.module_name} started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start {self.module_name}: {e}")
            raise
    
    async def stop(self):
        """Stop the FTM module."""
        try:
            self.is_active = False
            self.logger.info(f"{self.module_name} stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to stop {self.module_name}: {e}")
            raise
    
    async def _compile_patterns(self):
        """Compile regex patterns for performance optimization."""
        try:
            for pattern_name, pattern in self.persian_patterns.items():
                self.compiled_patterns[pattern_name] = re.compile(pattern)
            
            self.logger.info("Regex patterns compiled successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to compile patterns: {e}")
            raise
    
    async def filter_spam_words(self, text: str, language: str, spam_manager) -> Dict[str, Any]:
        """
        Filter spam words from text using the spam word manager.
        
        Args:
            text: Text to filter
            language: Language code (fa, en, ar, ur)
            spam_manager: SWM instance for spam word detection
            
        Returns:
            Filtering result with statistics
        """
        try:
            start_time = datetime.now()
            
            # Get spam analysis first
            spam_analysis = await spam_manager.check_spam_text(text, language)
            
            # If no spam found, return original text
            if not spam_analysis.get("is_spam_text", False):
                return await self._create_filter_result(
                    original_text=text,
                    filtered_text=text,
                    language=language,
                    processing_time=(datetime.now() - start_time).total_seconds(),
                    spam_found=False,
                    spam_analysis=spam_analysis
                )
            
            # Filter the text based on language
            if language == "fa" or language == "persian":
                filtered_result = await self._filter_persian_text(text, spam_manager, spam_analysis)
            elif language in ["en", "ar", "ur"]:
                filtered_result = await self._filter_multilingual_text(text, language, spam_manager, spam_analysis)
            else:
                # Default to multilingual filtering
                filtered_result = await self._filter_multilingual_text(text, "en", spam_manager, spam_analysis)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Create comprehensive result
            result = await self._create_filter_result(
                original_text=text,
                filtered_text=filtered_result["filtered_text"],
                language=language,
                processing_time=processing_time,
                spam_found=True,
                spam_analysis=spam_analysis,
                filter_details=filtered_result
            )
            
            # Update statistics
            await self._update_filter_statistics(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error filtering spam words: {e}")
            return await self._create_error_result(text, language, str(e))
    
    async def _filter_persian_text(self, text: str, spam_manager, spam_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Filter Persian text with specialized handling."""
        try:
            # Split text into words while preserving structure
            words = self._split_persian_text(text)
            
            filtered_words = []
            removed_words = []
            removed_positions = []
            
            for i, word_info in enumerate(words):
                word = word_info["word"]
                original_token = word_info["original"]
                
                # Check if word is spam
                spam_check = await spam_manager.check_spam_word(word, "fa")
                
                if spam_check["is_spam"]:
                    removed_words.append({
                        "word": word,
                        "original": original_token,
                        "position": i,
                        "sources": spam_check["detection_sources"]
                    })
                    removed_positions.append(i)
                    
                    # Replace with empty string or space based on configuration
                    if self.filter_config["preserve_spacing"]:
                        filtered_words.append("")
                    else:
                        continue  # Skip entirely
                else:
                    filtered_words.append(original_token)
            
            # Reconstruct filtered text
            if self.filter_config["preserve_word_order"]:
                filtered_text = self._reconstruct_persian_text(filtered_words, words)
            else:
                filtered_text = " ".join([w for w in filtered_words if w])
            
            return {
                "filtered_text": filtered_text,
                "removed_words": removed_words,
                "removed_positions": removed_positions,
                "original_word_count": len(words),
                "final_word_count": len([w for w in filtered_words if w]),
                "language": "fa",
                "filter_method": "persian_alphabet"
            }
            
        except Exception as e:
            self.logger.error(f"Error filtering Persian text: {e}")
            raise
    
    async def _filter_multilingual_text(self, text: str, language: str, spam_manager, spam_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Filter non-Persian text."""
        try:
            # Simple word splitting for non-Persian languages
            words = text.split()
            
            filtered_words = []
            removed_words = []
            removed_positions = []
            
            for i, word in enumerate(words):
                # Clean word for checking
                clean_word = re.sub(r"[^\w\s]", "", word).lower()
                
                if clean_word:
                    spam_check = await spam_manager.check_spam_word(clean_word, language)
                    
                    if spam_check["is_spam"]:
                        removed_words.append({
                            "word": clean_word,
                            "original": word,
                            "position": i,
                            "sources": spam_check["detection_sources"]
                        })
                        removed_positions.append(i)
                        
                        if self.filter_config["preserve_spacing"]:
                            filtered_words.append("")
                        else:
                            continue
                    else:
                        filtered_words.append(word)
                else:
                    filtered_words.append(word)
            
            # Reconstruct text
            if self.filter_config["preserve_word_order"]:
                filtered_text = " ".join(filtered_words)
            else:
                filtered_text = " ".join([w for w in filtered_words if w])
            
            # Clean up extra spaces
            filtered_text = re.sub(r"\s+", " ", filtered_text).strip()
            
            return {
                "filtered_text": filtered_text,
                "removed_words": removed_words,
                "removed_positions": removed_positions,
                "original_word_count": len(words),
                "final_word_count": len([w for w in filtered_words if w]),
                "language": language,
                "filter_method": "multilingual"
            }
            
        except Exception as e:
            self.logger.error(f"Error filtering multilingual text: {e}")
            raise
    
    def _split_persian_text(self, text: str) -> List[Dict[str, Any]]:
        """Split Persian text into words while preserving structure."""
        try:
            word_pattern = self.compiled_patterns.get("word_separator")
            if word_pattern:
                tokens = word_pattern.split(text)
            else:
                tokens = text.split()
            
            words = []
            for token in tokens:
                if token.strip():
                    # Remove diacritics for spam checking but preserve original
                    clean_token = self._remove_diacritics(token.strip())
                    words.append({
                        "word": clean_token,
                        "original": token,
                        "length": len(token),
                        "has_diacritics": clean_token != token.strip()
                    })
            
            return words
            
        except Exception as e:
            self.logger.error(f"Error splitting Persian text: {e}")
            return [{"word": text, "original": text, "length": len(text), "has_diacritics": False}]
    
    def _remove_diacritics(self, text: str) -> str:
        """Remove Persian diacritics from text."""
        try:
            # Remove Persian diacritics
            diacritics_pattern = self.compiled_patterns.get("diacritics")
            if diacritics_pattern:
                return diacritics_pattern.sub("", text)
            return text
            
        except Exception as e:
            self.logger.error(f"Error removing diacritics: {e}")
            return text
    
    def _reconstruct_persian_text(self, filtered_words: List[str], original_words: List[Dict[str, Any]]) -> str:
        """Reconstruct Persian text maintaining original structure."""
        try:
            # Simple reconstruction - join with spaces
            result = " ".join([w for w in filtered_words if w])
            
            # Clean up multiple spaces
            result = re.sub(r"\s+", " ", result).strip()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error reconstructing Persian text: {e}")
            return " ".join([w for w in filtered_words if w])
    
    async def _create_filter_result(self, original_text: str, filtered_text: str, language: str, 
                                   processing_time: float, spam_found: bool, spam_analysis: Dict[str, Any],
                                   filter_details: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a comprehensive filter result."""
        try:
            original_word_count = len(original_text.split())
            final_word_count = len(filtered_text.split())
            words_removed = original_word_count - final_word_count
            
            reduction_percentage = (words_removed / original_word_count * 100) if original_word_count > 0 else 0
            
            result = {
                "success": True,
                "original_text": original_text,
                "filtered_text": filtered_text,
                "language": language,
                "processing_time": processing_time,
                "spam_detected": spam_found,
                "statistics": {
                    "original_word_count": original_word_count,
                    "final_word_count": final_word_count,
                    "words_removed": words_removed,
                    "reduction_percentage": reduction_percentage,
                    "original_length": len(original_text),
                    "final_length": len(filtered_text),
                    "characters_removed": len(original_text) - len(filtered_text)
                },
                "spam_analysis": spam_analysis,
                "filter_config": self.filter_config,
                "timestamp": datetime.now().isoformat()
            }
            
            if filter_details:
                result["filter_details"] = filter_details
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error creating filter result: {e}")
            return await self._create_error_result(original_text, language, str(e))
    
    async def _create_error_result(self, original_text: str, language: str, error_message: str) -> Dict[str, Any]:
        """Create an error result."""
        return {
            "success": False,
            "error": True,
            "original_text": original_text,
            "filtered_text": original_text,  # Return original on error
            "language": language,
            "error_message": error_message,
            "timestamp": datetime.now().isoformat(),
            "spam_detected": False,
            "statistics": {
                "original_word_count": len(original_text.split()),
                "final_word_count": len(original_text.split()),
                "words_removed": 0,
                "reduction_percentage": 0.0
            }
        }
    
    async def _update_filter_statistics(self, result: Dict[str, Any]):
        """Update filtering statistics."""
        try:
            self.stats["total_texts_filtered"] += 1
            self.stats["total_words_processed"] += result["statistics"]["original_word_count"]
            self.stats["total_spam_words_removed"] += result["statistics"]["words_removed"]
            self.stats["total_characters_removed"] += result["statistics"]["characters_removed"]
            self.stats["last_activity"] = datetime.now()
            
            # Update language distribution
            language = result["language"]
            if language not in self.stats["language_distribution"]:
                self.stats["language_distribution"][language] = 0
            self.stats["language_distribution"][language] += 1
            
            # Update average filter time
            total_texts = self.stats["total_texts_filtered"]
            current_avg = self.stats["average_filter_time"]
            processing_time = result["processing_time"]
            self.stats["average_filter_time"] = (current_avg * (total_texts - 1) + processing_time) / total_texts
            
            # Update effectiveness
            if self.stats["total_words_processed"] > 0:
                self.stats["filter_effectiveness"] = (
                    self.stats["total_spam_words_removed"] / self.stats["total_words_processed"]
                )
            
            # Update performance metrics
            await self._update_performance_metrics(result)
            
        except Exception as e:
            self.logger.error(f"Error updating filter statistics: {e}")
    
    async def _update_performance_metrics(self, result: Dict[str, Any]):
        """Update performance metrics."""
        try:
            # Words per second
            if result["processing_time"] > 0:
                wps = result["statistics"]["original_word_count"] / result["processing_time"]
                current_wps = self.performance_metrics["words_per_second"]
                total_texts = self.stats["total_texts_filtered"]
                self.performance_metrics["words_per_second"] = (
                    (current_wps * (total_texts - 1) + wps) / total_texts
                )
            
            # Average text length
            text_length = result["statistics"]["original_length"]
            current_avg = self.performance_metrics["average_text_length"]
            total_texts = self.stats["total_texts_filtered"]
            self.performance_metrics["average_text_length"] = (
                (current_avg * (total_texts - 1) + text_length) / total_texts
            )
            
            # Average reduction percentage
            reduction = result["statistics"]["reduction_percentage"]
            current_avg = self.performance_metrics["average_reduction_percentage"]
            self.performance_metrics["average_reduction_percentage"] = (
                (current_avg * (total_texts - 1) + reduction) / total_texts
            )
            
        except Exception as e:
            self.logger.error(f"Error updating performance metrics: {e}")
    
    async def batch_filter(self, texts: List[str], language: str, spam_manager) -> List[Dict[str, Any]]:
        """Filter multiple texts in batch."""
        try:
            results = []
            
            for text in texts:
                result = await self.filter_spam_words(text, language, spam_manager)
                results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error in batch filtering: {e}")
            raise
    
    async def get_filter_statistics(self) -> Dict[str, Any]:
        """Get comprehensive filtering statistics."""
        return {
            "module": self.module_name,
            "statistics": self.stats,
            "performance_metrics": self.performance_metrics,
            "filter_config": self.filter_config,
            "compiled_patterns": list(self.compiled_patterns.keys()),
            "timestamp": datetime.now().isoformat()
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the FTM module."""
        return {
            "module": self.module_name,
            "is_active": self.is_active,
            "texts_processed": self.stats["total_texts_filtered"],
            "words_processed": self.stats["total_words_processed"],
            "spam_words_removed": self.stats["total_spam_words_removed"],
            "filter_effectiveness": self.stats["filter_effectiveness"],
            "performance": {
                "words_per_second": self.performance_metrics["words_per_second"],
                "average_filter_time": self.stats["average_filter_time"]
            },
            "supported_languages": ["fa", "en", "ar", "ur"],
            "timestamp": datetime.now().isoformat()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            # Test filtering with sample text
            test_text = "این یک متن تست است"
            start_time = datetime.now()
            
            # Mock spam manager for health check
            class MockSpamManager:
                async def check_spam_text(self, text, language):
                    return {"is_spam_text": False}
            
            mock_manager = MockSpamManager()
            test_result = await self.filter_spam_words(test_text, "fa", mock_manager)
            
            test_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "healthy": self.is_active and test_result["success"],
                "module": self.module_name,
                "timestamp": datetime.now().isoformat(),
                "test_performance": test_time,
                "patterns_compiled": len(self.compiled_patterns),
                "statistics": self.stats
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "module": self.module_name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            } 