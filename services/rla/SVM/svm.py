"""
Spam Validation Module (SVM) for RLA Microservice

This module handles spam detection and validation:
- Content-based spam detection
- Pattern matching
- Behavioral analysis
- Spam scoring
"""

import logging
from typing import Dict, Any
from datetime import datetime
import re


class SpamValidationModule:
    """Spam Validation Module for detecting spam content."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.module_name = "SVM"
        self.is_active = False
        
    async def start(self):
        self.is_active = True
        self.logger.info(f"{self.module_name} started")
        
    async def stop(self):
        self.is_active = False
        self.logger.info(f"{self.module_name} stopped")
        
    async def check_spam(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check if content is spam or malicious."""
        content = request_data.get("content", "")
        reasons = []
        score = 0.0
        # Spam trigger words/phrases
        spam_triggers = [
            "free", "win", "winner", "click here", "buy now", "congratulations", "prize", "urgent", "limited time", "offer", "guaranteed", "act now", "risk free", "exclusive deal", "money back", "no obligation", "call now", "order now", "as seen on", "apply now", "don't delete", "this isn't spam", "!!!", "$$$"
        ]
        # Malicious patterns (URLs, excessive punctuation, etc.)
        url_pattern = re.compile(r"https?://|www\\.|\.com|\.ru|\.cn|\.tk|\.info|\.biz|\.xyz", re.IGNORECASE)
        # Check for spam triggers
        lowered = content.lower()
        for trigger in spam_triggers:
            if trigger in lowered:
                reasons.append(f"Spam trigger word/phrase detected: '{trigger}'")
                score += 0.5
        # Check for URLs
        if url_pattern.search(content):
            reasons.append("URL detected in content")
            score += 0.5
        # Check for excessive punctuation or symbols
        if content.count("!") > 3 or content.count("$") > 2:
            reasons.append("Excessive punctuation or symbols detected")
            score += 0.5
        # If any reason found, flag as spam
        is_spam = len(reasons) > 0
        return {
            "is_spam": is_spam,
            "reasons": reasons,
            "score": min(score, 1.0),
            "timestamp": datetime.now().isoformat()
        }
    
    def get_status(self) -> Dict[str, Any]:
        return {"module": self.module_name, "is_active": self.is_active}
    
    async def health_check(self) -> Dict[str, Any]:
        return {"healthy": self.is_active, "module": self.module_name} 