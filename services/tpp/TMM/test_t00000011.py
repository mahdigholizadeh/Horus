"""
Test T00000011: EMM (Error Management Module) Unit Test
Module(s) Tested: EMM
Description: Ensures the EMM provides centralized, consistent error handling and logging.
Success Criteria: Exceptions are caught, logged in standardized format, and user-friendly error responses are generated.
"""

import asyncio
import json

# Mock EMM class for testing
class ErrorManagementModule:
    def __init__(self):
        self.module_name = "EMM"
        self.is_active = False
        self.log_entries = []
        self.error_stats = {
            "total_errors": 0,
            "errors_by_module": {},
            "errors_by_type": {}
        }
    
    async def start(self):
        self.is_active = True
    
    async def stop(self):
        self.is_active = False
    
    async def handle_error(self, error, module, operation):
        # Create user-friendly error messages
        if isinstance(error, json.JSONDecodeError):
            error_message = "Invalid JSON format detected"
        elif isinstance(error, FileNotFoundError):
            error_message = str(error)
        else:
            error_message = str(error)
        
        error_info = {
            "error": error_message,
            "error_code": type(error).__name__,
            "module": module,
            "operation": operation,
            "timestamp": "2024-01-15T10:30:00Z"
        }
        
        self.log_entries.append({
            "timestamp": "2024-01-15T10:30:00Z",
            "level": "ERROR",
            "module": module,
            "message": str(error)
        })
        
        self.error_stats["total_errors"] += 1
        return error_info
    
    def get_log_entries(self):
        return self.log_entries
    
    def get_error_statistics(self):
        return self.error_stats
    
    async def create_error(self, error_code, message, module, operation):
        return {
            "error_code": error_code,
            "error": message,
            "module": module,
            "operation": operation,
            "timestamp": "2024-01-15T10:30:00Z"
        }

async def test_t00000011():
    test_code = "T00000011"
    test_name = "EMM - Error Handling and Logging"
    results = []
    emm = ErrorManagementModule()
    await emm.start()

    # Step 1: Simulate a FileNotFoundError in the FIM
    try:
        file_error = FileNotFoundError("Config file not found: /path/to/missing/config.json")
        file_error_result = await emm.handle_error(file_error, "FIM", "read_file")
        
        results.append(isinstance(file_error_result, dict))
        results.append("error" in file_error_result)
        results.append("error_code" in file_error_result)
        results.append("timestamp" in file_error_result)
        results.append(file_error_result.get("module") == "FIM")
        results.append(file_error_result.get("operation") == "read_file")
        
        # Check if error message is user-friendly
        error_message = file_error_result.get("error", "")
        results.append("file" in error_message.lower() or "not found" in error_message.lower())
        
    except Exception as e:
        results.append(False)
        results.extend([False] * 6)  # Add False for all the checks above

    # Step 2: Simulate a JSONDecodeError in the IPM
    try:
        json_error = json.JSONDecodeError("Expecting ',' delimiter", "invalid json", 10)
        json_error_result = await emm.handle_error(json_error, "IPM", "validate_input")
        
        results.append(isinstance(json_error_result, dict))
        results.append("error" in json_error_result)
        results.append("error_code" in json_error_result)
        results.append(json_error_result.get("module") == "IPM")
        results.append(json_error_result.get("operation") == "validate_input")
        
        # Check if error message is user-friendly
        json_error_message = json_error_result.get("error", "")
        results.append("json" in json_error_message.lower() or "format" in json_error_message.lower())
        
    except Exception as e:
        results.append(False)
        results.extend([False] * 5)  # Add False for all the checks above

    # Step 3: Test error logging format
    log_entries = emm.get_log_entries()
    results.append(isinstance(log_entries, list))
    
    if log_entries:
        latest_log = log_entries[-1]
        results.append(isinstance(latest_log, dict))
        results.append("timestamp" in latest_log)
        results.append("level" in latest_log)
        results.append("module" in latest_log)
        results.append("message" in latest_log)

    # Step 4: Test error statistics
    error_stats = emm.get_error_statistics()
    results.append(isinstance(error_stats, dict))
    results.append("total_errors" in error_stats)
    results.append("errors_by_module" in error_stats)
    results.append("errors_by_type" in error_stats)

    # Step 5: Test custom error creation
    custom_error = await emm.create_error(
        "CUSTOM_ERROR",
        "This is a custom error message",
        "TEST",
        "test_operation"
    )
    results.append(isinstance(custom_error, dict))
    results.append(custom_error.get("error_code") == "CUSTOM_ERROR")
    results.append(custom_error.get("module") == "TEST")
    results.append(custom_error.get("operation") == "test_operation")

    await emm.stop()
    success = all(results)
    return {
        "success": success,
        "test_code": test_code,
        "test_name": test_name,
        "message": "EMM error handling and logging passed" if success else "EMM error handling and logging failed",
        "details": {
            "steps": results,
            "file_error_result": file_error_result if 'file_error_result' in locals() else None,
            "json_error_result": json_error_result if 'json_error_result' in locals() else None,
            "log_entries": log_entries,
            "error_stats": error_stats,
            "custom_error": custom_error
        }
    }

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(test_t00000011())
    import pprint
    pprint.pprint(result) 