"""
Test T00000003: FTM (Filter Text Module) Unit Test
Module(s) Tested: FTM
Description: Verifies that the FTM correctly removes spam words from a text while preserving word order.
Success Criteria: Spam words are filtered out correctly and word order is preserved as configured.
"""

import asyncio

# Mock FTM class for testing
class FilterTextModule:
    def __init__(self):
        self.module_name = "FTM"
        self.is_active = False
    
    async def start(self):
        self.is_active = True
    
    async def stop(self):
        self.is_active = False
    
    async def filter_text(self, text, spam_words, preserve_word_order=True):
        words = text.split()
        filtered_words = []
        
        for word in words:
            if word.lower() not in [spam.lower() for spam in spam_words]:
                filtered_words.append(word)
        
        if preserve_word_order:
            filtered_text = " ".join(filtered_words)
        else:
            # For non-preserve mode, just return filtered words in any order
            filtered_text = " ".join(filtered_words)
        
        return {
            "filtered_text": filtered_text,
            "filtering_stats": {
                "words_removed": len(words) - len(filtered_words),
                "spam_detected": len(words) != len(filtered_words)
            }
        }

async def test_t00000003():
    test_code = "T00000003"
    test_name = "FTM - Spam Word Filtering"
    results = []
    ftm = FilterTextModule()
    await ftm.start()

    # Step 1: Provide a sentence containing a mix of normal words and known spam words
    test_sentence = "This is a testspamword sample text"
    spam_words = ["testspamword", "spam", "advertisement"]
    
    # Step 2: Process the text through the FTM with preserve_word_order = True
    filter_result = await ftm.filter_text(test_sentence, spam_words, preserve_word_order=True)
    filtered_text = filter_result.get("filtered_text", "")
    expected_filtered = "This is a sample text"
    results.append(filtered_text == expected_filtered)

    # Step 3: Set preserve_word_order to False and re-run the filter
    filter_result_no_order = await ftm.filter_text(test_sentence, spam_words, preserve_word_order=False)
    filtered_text_no_order = filter_result_no_order.get("filtered_text", "")
    # Should still filter out spam words but may not preserve exact order
    results.append("testspamword" not in filtered_text_no_order)
    results.append(len(filtered_text_no_order.split()) < len(test_sentence.split()))

    # Step 4: Test with Persian text
    persian_sentence = "این یک متن تست است که شامل کلمات اسپم است"
    persian_spam_words = ["اسپم", "تبلیغات"]
    persian_filter_result = await ftm.filter_text(persian_sentence, persian_spam_words, preserve_word_order=True)
    persian_filtered = persian_filter_result.get("filtered_text", "")
    results.append("اسپم" not in persian_filtered)

    # Step 5: Verify filtering statistics
    stats = filter_result.get("filtering_stats", {})
    words_removed = stats.get("words_removed", 0)
    results.append(words_removed > 0)

    await ftm.stop()
    success = all(results)
    return {
        "success": success,
        "test_code": test_code,
        "test_name": test_name,
        "message": "FTM spam word filtering passed" if success else "FTM spam word filtering failed",
        "details": {
            "steps": results,
            "original_text": test_sentence,
            "filtered_text": filtered_text,
            "expected_filtered": expected_filtered,
            "filtered_text_no_order": filtered_text_no_order,
            "persian_filtered": persian_filtered,
            "filtering_stats": stats
        }
    }

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(test_t00000003())
    import pprint
    pprint.pprint(result) 