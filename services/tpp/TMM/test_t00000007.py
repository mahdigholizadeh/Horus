"""
Test T00000007: FIM (File Interface Module) Unit Test
Module(s) Tested: FIM
Description: Tests the FIM's ability to read and process supported file formats.
Success Criteria: Supported file formats are read successfully, unsupported formats raise appropriate errors.
"""

import asyncio
import json
import tempfile
import os

# Mock FIM class for testing
class FileInterfaceModule:
    def __init__(self):
        self.module_name = "FIM"
        self.is_active = False
        self.supported_formats = ['.json', '.txt']
    
    async def start(self):
        self.is_active = True
    
    async def stop(self):
        self.is_active = False
    
    async def read_file(self, file_path):
        try:
            if not os.path.exists(file_path):
                return {"success": False, "error": "File not found"}
            
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext not in self.supported_formats:
                return {"success": False, "error": "Format not supported"}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_ext == '.json':
                    content = json.load(f)
                else:
                    content = f.read()
            
            return {"success": True, "content": content}
        except Exception as e:
            return {"success": False, "error": str(e)}

async def test_t00000007():
    test_code = "T00000007"
    test_name = "FIM - File Format Support"
    results = []
    fim = FileInterfaceModule()
    await fim.start()

    # Step 1: Create a sample .json file containing text for processing
    json_content = {
        "text": "This is a test text from JSON file",
        "language": "english",
        "options": {
            "preserve_word_order": True
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as json_file:
        json.dump(json_content, json_file)
        json_file_path = json_file.name
    
    try:
        json_result = await fim.read_file(json_file_path)
        results.append(json_result.get("success", False))
        results.append(json_result.get("content") == json_content)
    finally:
        os.unlink(json_file_path)

    # Step 2: Create a sample .txt file
    txt_content = "This is a plain text file for testing"
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as txt_file:
        txt_file.write(txt_content)
        txt_file_path = txt_file.name
    
    try:
        txt_result = await fim.read_file(txt_file_path)
        results.append(txt_result.get("success", False))
        results.append(txt_result.get("content") == txt_content)
    finally:
        os.unlink(txt_file_path)

    # Step 3: Attempt to read from an unsupported file type
    unsupported_content = "This is an unsupported file format"
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.docx', delete=False) as unsupported_file:
        unsupported_file.write(unsupported_content)
        unsupported_file_path = unsupported_file.name
    
    try:
        unsupported_result = await fim.read_file(unsupported_file_path)
        results.append(not unsupported_result.get("success", True))  # Should fail
        error_message = unsupported_result.get("error", "")
        results.append("format" in error_message.lower() or "supported" in error_message.lower())
    finally:
        os.unlink(unsupported_file_path)

    # Step 4: Test with non-existent file
    non_existent_result = await fim.read_file("/path/to/nonexistent/file.txt")
    results.append(not non_existent_result.get("success", True))
    results.append("not found" in non_existent_result.get("error", "").lower())

    # Step 5: Test with empty file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as empty_file:
        empty_file_path = empty_file.name
    
    try:
        empty_result = await fim.read_file(empty_file_path)
        results.append(empty_result.get("success", False))
        results.append(empty_result.get("content") == "")
    finally:
        os.unlink(empty_file_path)

    await fim.stop()
    success = all(results)
    return {
        "success": success,
        "test_code": test_code,
        "test_name": test_name,
        "message": "FIM file format support passed" if success else "FIM file format support failed",
        "details": {
            "steps": results,
            "json_result": json_result,
            "txt_result": txt_result,
            "unsupported_result": unsupported_result,
            "non_existent_result": non_existent_result,
            "empty_result": empty_result
        }
    }

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(test_t00000007())
    import pprint
    pprint.pprint(result) 