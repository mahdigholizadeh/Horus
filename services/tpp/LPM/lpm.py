"""
Language Processing Module (LPM) for TPP Microservice

This module handles language detection and processing:
- Automatic language detection for Persian, English, Arabic, Urdu
- Script analysis and text classification
- Language-specific text processing
- Multi-language support utilities
"""

import logging
import asyncio
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import unicodedata


class LanguageProcessingModule:
    """
    Language Processing Module
    
    Handles language detection, script analysis, and language-specific
    processing for multi-language text filtering.
    """
    
    def __init__(self):
        """Initialize the LPM module."""
        self.logger = logging.getLogger(__name__)
        self.module_name = "LPM"
        self.is_active = False
        
        # Unicode ranges for different scripts
        self.script_ranges = {
            "persian": {
                "range": (0x0600, 0x06FF),  # Arabic block (includes Persian)
                "additional": [(0xFB50, 0xFDFF), (0xFE70, 0xFEFF)],  # Arabic presentation forms
                "letters": r"[\u0600-\u06FF]",
                "common_chars": ["ا", "ب", "پ", "ت", "ث", "ج", "چ", "ح", "خ", "د", "ذ", "ر", "ز", "ژ", "س", "ش", "ص", "ض", "ط", "ظ", "ع", "غ", "ف", "ق", "ک", "گ", "ل", "م", "ن", "و", "ه", "ی"]
            },
            "arabic": {
                "range": (0x0600, 0x06FF),  # Arabic block
                "additional": [(0xFB50, 0xFDFF), (0xFE70, 0xFEFF)],
                "letters": r"[\u0600-\u06FF]",
                "common_chars": ["ا", "ب", "ت", "ث", "ج", "ح", "خ", "د", "ذ", "ر", "ز", "س", "ش", "ص", "ض", "ط", "ظ", "ع", "غ", "ف", "ق", "ك", "ل", "م", "ن", "و", "ه", "ي"]
            },
            "urdu": {
                "range": (0x0600, 0x06FF),  # Arabic block (Urdu uses similar script)
                "additional": [(0xFB50, 0xFDFF), (0xFE70, 0xFEFF)],
                "letters": r"[\u0600-\u06FF]",
                "common_chars": ["ا", "ب", "پ", "ت", "ٹ", "ث", "ج", "چ", "ح", "خ", "د", "ڈ", "ذ", "ر", "ڑ", "ز", "ژ", "س", "ش", "ص", "ض", "ط", "ظ", "ع", "غ", "ف", "ق", "ک", "گ", "ل", "م", "ن", "ں", "و", "ہ", "ھ", "ی", "ے"]
            },
            "english": {
                "range": (0x0020, 0x007F),  # Basic Latin
                "additional": [(0x00A0, 0x00FF)],  # Latin-1 supplement
                "letters": r"[a-zA-Z]",
                "common_chars": ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z"]
            }
        }
        
        # Language-specific patterns
        self.language_patterns = {
            "persian": {
                "definite_indicators": ["است", "هست", "بود", "باشد", "که", "را", "به", "از", "در", "با", "برای"],
                "common_words": ["این", "آن", "من", "تو", "او", "ما", "شما", "آنها", "و", "یا", "اما", "چون"],
                "endings": ["ان", "ات", "ها", "تان", "شان", "ش", "ت", "م"],
                "unique_chars": ["پ", "چ", "ژ", "گ", "ک", "ی"]
            },
            "arabic": {
                "definite_indicators": ["هو", "هي", "هذا", "هذه", "التي", "الذي", "إلى", "من", "في", "على", "عن"],
                "common_words": ["أن", "من", "إلى", "في", "على", "عن", "مع", "أو", "لا", "نعم", "هل"],
                "endings": ["ة", "ات", "ين", "ون", "ها", "هم", "هن"],
                "unique_chars": ["ك", "ي", "ء", "ؤ", "ئ"]
            },
            "urdu": {
                "definite_indicators": ["ہے", "ہیں", "تھا", "تھی", "ہوں", "ہو", "کا", "کی", "کو", "نے", "میں", "سے"],
                "common_words": ["اور", "یہ", "وہ", "کہ", "جو", "کیا", "کرنا", "میں", "تم", "وہ", "ہم"],
                "endings": ["یں", "یں", "گا", "گی", "گے", "تا", "تی", "تے"],
                "unique_chars": ["ٹ", "ڈ", "ڑ", "ں", "ھ", "ے"]
            },
            "english": {
                "definite_indicators": ["the", "and", "or", "but", "is", "are", "was", "were", "have", "has", "had"],
                "common_words": ["this", "that", "these", "those", "with", "from", "they", "them", "their", "there"],
                "endings": ["ing", "ed", "tion", "ment", "ly", "ness", "ful", "less"],
                "unique_chars": []  # No unique characters for English
            }
        }
        
        # Detection statistics
        self.detection_stats = {
            "total_detections": 0,
            "language_counts": {
                "persian": 0,
                "arabic": 0,
                "urdu": 0,
                "english": 0,
                "mixed": 0,
                "unknown": 0
            },
            "accuracy_rate": 0.0,
            "average_confidence": 0.0,
            "detection_time": 0.0
        }
        
        # Compiled regex patterns
        self.compiled_patterns = {}
        
        self.logger.info(f"{self.module_name} initialized successfully")
    
    async def start(self):
        """Start the LPM module."""
        try:
            self.is_active = True
            
            # Compile regex patterns
            await self._compile_patterns()
            
            self.logger.info(f"{self.module_name} started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start {self.module_name}: {e}")
            raise
    
    async def stop(self):
        """Stop the LPM module."""
        try:
            self.is_active = False
            self.logger.info(f"{self.module_name} stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to stop {self.module_name}: {e}")
            raise
    
    async def _compile_patterns(self):
        """Compile regex patterns for performance."""
        try:
            for script_name, script_info in self.script_ranges.items():
                pattern = script_info["letters"]
                self.compiled_patterns[script_name] = re.compile(pattern)
            
            # Additional patterns
            self.compiled_patterns["whitespace"] = re.compile(r"\s+")
            self.compiled_patterns["punctuation"] = re.compile(r"[^\w\s]")
            
            self.logger.info("Language detection patterns compiled successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to compile patterns: {e}")
            raise
    
    async def detect_language(self, text: str) -> Dict[str, Any]:
        """
        Detect the language of the given text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Language detection result
        """
        try:
            start_time = datetime.now()
            
            # Clean and prepare text
            clean_text = self._clean_text(text)
            
            if not clean_text:
                return self._create_detection_result("unknown", 0.0, "Empty text")
            
            # Analyze script distribution
            script_analysis = await self._analyze_script_distribution(clean_text)
            
            # Analyze language patterns
            pattern_analysis = await self._analyze_language_patterns(clean_text)
            
            # Determine primary language
            language_scores = await self._calculate_language_scores(script_analysis, pattern_analysis)
            
            # Select best match
            detected_language, confidence = self._select_best_language(language_scores)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Create result
            result = {
                "language": detected_language,
                "confidence": confidence,
                "script_analysis": script_analysis,
                "pattern_analysis": pattern_analysis,
                "language_scores": language_scores,
                "processing_time": processing_time,
                "text_length": len(text),
                "clean_text_length": len(clean_text),
                "timestamp": datetime.now().isoformat()
            }
            
            # Update statistics
            await self._update_detection_stats(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error detecting language: {e}")
            return self._create_detection_result("unknown", 0.0, f"Error: {str(e)}")
    
    def _clean_text(self, text: str) -> str:
        """Clean text for analysis."""
        try:
            # Remove excessive whitespace
            clean_text = re.sub(r"\s+", " ", text.strip())
            
            # Remove URLs, emails, and other noise
            clean_text = re.sub(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+", "", clean_text)
            clean_text = re.sub(r"\S+@\S+", "", clean_text)
            
            # Remove numbers and special characters for analysis
            clean_text = re.sub(r"[0-9]+", "", clean_text)
            
            return clean_text.strip()
            
        except Exception as e:
            self.logger.error(f"Error cleaning text: {e}")
            return text
    
    async def _analyze_script_distribution(self, text: str) -> Dict[str, Any]:
        """Analyze the distribution of different scripts in the text."""
        try:
            char_count = len(text)
            if char_count == 0:
                return {}
            
            script_counts = {}
            
            for char in text:
                unicode_cat = unicodedata.category(char)
                char_code = ord(char)
                
                # Check which script this character belongs to
                for script_name, script_info in self.script_ranges.items():
                    main_range = script_info["range"]
                    additional_ranges = script_info.get("additional", [])
                    
                    in_range = (main_range[0] <= char_code <= main_range[1])
                    
                    if not in_range:
                        for add_range in additional_ranges:
                            if add_range[0] <= char_code <= add_range[1]:
                                in_range = True
                                break
                    
                    if in_range:
                        script_counts[script_name] = script_counts.get(script_name, 0) + 1
                        break
            
            # Calculate percentages
            script_percentages = {}
            for script, count in script_counts.items():
                script_percentages[script] = (count / char_count) * 100
            
            return {
                "character_count": char_count,
                "script_counts": script_counts,
                "script_percentages": script_percentages,
                "dominant_script": max(script_percentages, key=script_percentages.get) if script_percentages else "unknown"
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing script distribution: {e}")
            return {}
    
    async def _analyze_language_patterns(self, text: str) -> Dict[str, Any]:
        """Analyze language-specific patterns in the text."""
        try:
            words = text.lower().split()
            word_count = len(words)
            
            if word_count == 0:
                return {}
            
            pattern_scores = {}
            
            for language, patterns in self.language_patterns.items():
                score = 0
                matches = {
                    "definite_indicators": 0,
                    "common_words": 0,
                    "endings": 0,
                    "unique_chars": 0
                }
                
                # Check definite indicators
                for indicator in patterns["definite_indicators"]:
                    if indicator in words:
                        matches["definite_indicators"] += 1
                        score += 10  # High weight for definite indicators
                
                # Check common words
                for common_word in patterns["common_words"]:
                    if common_word in words:
                        matches["common_words"] += 1
                        score += 5
                
                # Check word endings
                for word in words:
                    for ending in patterns["endings"]:
                        if word.endswith(ending):
                            matches["endings"] += 1
                            score += 2
                
                # Check unique characters
                for char in patterns["unique_chars"]:
                    if char in text:
                        matches["unique_chars"] += 1
                        score += 3
                
                pattern_scores[language] = {
                    "score": score,
                    "matches": matches,
                    "normalized_score": score / word_count if word_count > 0 else 0
                }
            
            return {
                "word_count": word_count,
                "pattern_scores": pattern_scores,
                "top_pattern_match": max(pattern_scores, key=lambda x: pattern_scores[x]["score"]) if pattern_scores else "unknown"
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing language patterns: {e}")
            return {}
    
    async def _calculate_language_scores(self, script_analysis: Dict[str, Any], pattern_analysis: Dict[str, Any]) -> Dict[str, float]:
        """Calculate final language scores combining script and pattern analysis."""
        try:
            language_scores = {}
            
            # Get script percentages
            script_percentages = script_analysis.get("script_percentages", {})
            
            # Get pattern scores
            pattern_scores = pattern_analysis.get("pattern_scores", {})
            
            # Calculate combined scores for each language
            for language in ["persian", "arabic", "urdu", "english"]:
                script_score = script_percentages.get(language, 0)
                pattern_score = pattern_scores.get(language, {}).get("normalized_score", 0) * 10
                
                # Weight: 60% script, 40% patterns
                combined_score = (script_score * 0.6) + (pattern_score * 0.4)
                
                language_scores[language] = combined_score
            
            return language_scores
            
        except Exception as e:
            self.logger.error(f"Error calculating language scores: {e}")
            return {}
    
    def _select_best_language(self, language_scores: Dict[str, float]) -> Tuple[str, float]:
        """Select the best language match."""
        try:
            if not language_scores:
                return "unknown", 0.0
            
            # Find the language with highest score
            best_language = max(language_scores, key=language_scores.get)
            best_score = language_scores[best_language]
            
            # Convert score to confidence (0-1)
            confidence = min(best_score / 100, 1.0)
            
            # Set minimum confidence threshold
            if confidence < 0.3:
                return "unknown", confidence
            
            # Map to standard language codes
            language_mapping = {
                "persian": "fa",
                "arabic": "ar",
                "urdu": "ur",
                "english": "en"
            }
            
            return language_mapping.get(best_language, best_language), confidence
            
        except Exception as e:
            self.logger.error(f"Error selecting best language: {e}")
            return "unknown", 0.0
    
    def _create_detection_result(self, language: str, confidence: float, error: str = None) -> Dict[str, Any]:
        """Create a detection result."""
        result = {
            "language": language,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat()
        }
        
        if error:
            result["error"] = error
        
        return result
    
    async def _update_detection_stats(self, result: Dict[str, Any]):
        """Update detection statistics."""
        try:
            self.detection_stats["total_detections"] += 1
            
            language = result["language"]
            if language in self.detection_stats["language_counts"]:
                self.detection_stats["language_counts"][language] += 1
            else:
                self.detection_stats["language_counts"]["unknown"] += 1
            
            # Update averages
            total = self.detection_stats["total_detections"]
            current_avg_conf = self.detection_stats["average_confidence"]
            new_confidence = result["confidence"]
            self.detection_stats["average_confidence"] = (
                (current_avg_conf * (total - 1) + new_confidence) / total
            )
            
            current_avg_time = self.detection_stats["detection_time"]
            new_time = result["processing_time"]
            self.detection_stats["detection_time"] = (
                (current_avg_time * (total - 1) + new_time) / total
            )
            
        except Exception as e:
            self.logger.error(f"Error updating detection stats: {e}")
    
    async def batch_detect(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Detect languages for multiple texts."""
        try:
            results = []
            
            for text in texts:
                result = await self.detect_language(text)
                results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error in batch detection: {e}")
            raise
    
    async def get_supported_languages(self) -> List[str]:
        """Get list of supported languages."""
        return ["fa", "ar", "ur", "en"]
    
    async def is_language_supported(self, language: str) -> bool:
        """Check if a language is supported."""
        supported = await self.get_supported_languages()
        return language in supported
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the LPM module."""
        return {
            "module": self.module_name,
            "is_active": self.is_active,
            "supported_languages": ["fa", "ar", "ur", "en"],
            "detection_stats": self.detection_stats,
            "compiled_patterns": len(self.compiled_patterns),
            "timestamp": datetime.now().isoformat()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            # Test with sample texts
            test_texts = {
                "persian": "این یک متن فارسی است",
                "english": "This is an English text",
                "arabic": "هذا نص عربي",
                "urdu": "یہ اردو متن ہے"
            }
            
            health_results = {}
            all_healthy = True
            
            for lang, text in test_texts.items():
                try:
                    result = await self.detect_language(text)
                    health_results[lang] = {
                        "detected": result["language"],
                        "confidence": result["confidence"],
                        "healthy": result["confidence"] > 0.5
                    }
                    
                    if result["confidence"] <= 0.5:
                        all_healthy = False
                        
                except Exception as e:
                    health_results[lang] = {
                        "error": str(e),
                        "healthy": False
                    }
                    all_healthy = False
            
            return {
                "healthy": all_healthy and self.is_active,
                "module": self.module_name,
                "timestamp": datetime.now().isoformat(),
                "test_results": health_results,
                "detection_stats": self.detection_stats
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "module": self.module_name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            } 