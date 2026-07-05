"""
Test T00000004: SVM (Spam Validation Module) Unit Test
Module(s) Tested: SVM
Description: Tests the SVM's ability to detect and filter spam or malicious content.
Success Criteria: Benign payload passes, spam/malicious payloads are flagged and rejected.
"""

import asyncio
from SVM.svm import SpamValidationModule

async def test_t00000004():
    test_code = "T00000004"
    test_name = "SVM - Spam/Malicious Content Detection"
    results = []
    svm = SpamValidationModule()
    await svm.start()

    # Step 1: Benign payload (should pass)
    benign = {"content": "Hello, this is a normal message."}
    result1 = await svm.check_spam(benign)
    results.append(not result1.get("is_spam", True))

    # Step 2: Spam trigger words (should flag)
    spam = {"content": "Congratulations, you won a free iPhone! Click here."}
    result2 = await svm.check_spam(spam)
    results.append(result2.get("is_spam", False))

    # Step 3: Auto-generated/malicious content (should flag)
    malicious = {"content": "Buy now!!! $$$ http://spam.com"}
    result3 = await svm.check_spam(malicious)
    results.append(result3.get("is_spam", False))

    await svm.stop()
    success = all(results)
    return {
        "success": success,
        "test_code": test_code,
        "test_name": test_name,
        "message": "All SVM spam/malicious detection scenarios passed" if success else "Some SVM spam/malicious detection scenarios failed",
        "details": {
            "steps": results,
            "step_results": [result1, result2, result3]
        }
    }

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(test_t00000004())
    import pprint
    pprint.pprint(result) 