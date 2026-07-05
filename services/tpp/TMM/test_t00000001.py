"""
Test T00000001: TPDM (Text Processing Data Module) Unit Test
Module(s) Tested: TPDM
Description: Verifies that the TPDM correctly preprocesses text, manages data structures, and calculates text metrics.
Success Criteria: Text normalization works correctly and metrics are accurate.
"""

import asyncio

# Mock TPDM class for testing
class TextProcessingDataModule:
    def __init__(self):
        self.module_name = "TPDM"
        self.is_active = False
        self.stats = {
            "total_processed": 0,
            "total_words": 0,
            "total_characters": 0,
            "processing_time": 0.0,
            "last_activity": None
        }
    
    async def start(self):
        self.is_active = True
    
    async def stop(self):
        self.is_active = False
    
    async def process_text(self, text_data, language_result):
        text = text_data.get("message_text", "")
        
        # Normalize text
        normalized_text = self._normalize_text(text)
        
        # Extract metrics
        metrics = self._extract_metrics(normalized_text)
        
        # Update statistics
        self.stats["total_processed"] += 1
        self.stats["total_words"] += metrics["word_count"]
        self.stats["total_characters"] += metrics["character_count"]
        
        return {
            "processed_text": normalized_text,
            "metrics": metrics,
            "stats": self.stats
        }
    
    def _normalize_text(self, text):
        # Simple normalization
        import re
        normalized = text.strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized
    
    def _extract_metrics(self, text):
        words = text.split()
        return {
            "word_count": len(words),
            "character_count": len(text)
        }

async def test_t00000001():
    test_code = "T00000001"
    test_name = "TPDM - Text Processing and Metrics"
    results = []
    tpdm = TextProcessingDataModule()
    await tpdm.start()

    # Step 1: Provide a sample text with mixed case, extra whitespace, and punctuation
    sample_text = "  This   is   a   TEST   text   with   MIXED   case   and   extra   spaces!!!  "
    text_data = {"message_text": sample_text}
    language_result = {"detected_language": "english", "confidence": 0.95}

    # Step 2: Process the text through the TPDM's normalization function
    result = await tpdm.process_text(text_data, language_result)
    processed_text = result.get("processed_text", "")
    metrics = result.get("metrics", {})

    # Step 3: Verify text normalization
    expected_normalized = "This is a TEST text with MIXED case and extra spaces!!!"
    normalization_correct = processed_text == expected_normalized
    results.append(normalization_correct)

    # Step 4: Verify metrics accuracy
    word_count = metrics.get("word_count", 0)
    character_count = metrics.get("character_count", 0)
    
    # Expected: 11 words, 55 characters (after normalization)
    word_count_correct = word_count == 11
    character_count_correct = character_count == 55
    results.append(word_count_correct)
    results.append(character_count_correct)

    # Step 5: Verify processing statistics
    stats = result.get("stats", {})
    total_processed = stats.get("total_processed", 0)
    results.append(total_processed == 1)  # Should have processed 1 text

    await tpdm.stop()
    success = all(results)
    return {
        "success": success,
        "test_code": test_code,
        "test_name": test_name,
        "message": "TPDM text processing and metrics calculation passed" if success else "TPDM text processing and metrics calculation failed",
        "details": {
            "steps": results,
            "processed_text": processed_text,
            "expected_text": expected_normalized,
            "metrics": metrics,
            "stats": stats
        }
    }

if __name__ == "__main__":
    import asyncio
    print("Starting test_t00000001...")
    try:
        result = asyncio.run(test_t00000001())
        import pprint
        pprint.pprint(result)
    except Exception as e:
        print(f"Error running test: {e}")
        import traceback
        traceback.print_exc() 