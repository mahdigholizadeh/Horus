# Error Handling Quick Reference Guide

## 🚀 Quick Start

### 1. Add Required Imports
```python
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler
```

### 2. Initialize in __init__
```python
def __init__(self):
    self.error_manager = ErrorManagementModule()
    # Remove hardcoded error_codes dictionary
    # Error codes now generated dynamically by EMM
```

### 3. Add Required Methods
```python
def log_error(self, error_message: str, class_name: str = "UnknownClass", 
              function_name: str = "UnknownFunction", sub_function: str = "001"):
    return self.error_manager.log_error_with_generation(
        "YOUR_MODULE_NAME", class_name, function_name, error_message, sub_function
    )

def generate_error_code(self, class_name: str = "UnknownClass", 
                       function_name: str = "UnknownFunction", 
                       sub_function: str = "001") -> str:
    return self.error_manager.generate_error_code("YOUR_MODULE_NAME", class_name, function_name, sub_function)

async def handle_exception(self, exception: Exception, class_name: str = "UnknownClass", 
                          function_name: str = "UnknownFunction", context: dict = None):
    error_message = str(exception)
    error_code = self.log_error(error_message, class_name, function_name)
    
    if hasattr(exception, 'status_code') or 'api' in error_message.lower():
        return await self.handle_api_error(error_message, getattr(exception, 'status_code', None), context)
    
    return {
        "success": False,
        "error_code": error_code,
        "error_message": error_message,
        "timestamp": datetime.now().isoformat()
    }

async def handle_api_error(self, error_response: str, status_code: int = None, context: dict = None) -> dict:
    try:
        result = await api_error_handler.handle_api_error(error_response, status_code, context)
        self.error_manager.log_error_with_generation(
            "YOUR_MODULE_NAME", "YOUR_MODULE_NAME", "handle_api_error",
            f"API Error: {result.get('api_error_type', 'unknown')}", context=result
        )
        await api_error_handler.send_error_report_to_ccu(result)
        return result
    except Exception as e:
        self.error_manager.log_error_with_generation(
            "YOUR_MODULE_NAME", "YOUR_MODULE_NAME", "handle_api_error",
            f"Error handling API error: {str(e)}"
        )
        return {"success": False, "error": str(e)}
```

## 📝 Common Usage Patterns

### Basic Error Logging
```python
# Log an error
error_code = self.log_error("Database connection failed", "DatabaseManager", "connect")

# Generate error code
error_code = self.generate_error_code("UserManager", "authenticate", "001")
```

### Exception Handling
```python
try:
    result = await self.process_data(data)
except Exception as e:
    error_result = await self.handle_exception(e, "DataProcessor", "process_data", {
        "data_type": type(data)
    })
    return error_result
```

### API Error Handling
```python
if response.status in [401, 403, 429, 500, 503]:
    error_text = await response.text()
    error_result = await self.handle_api_error(error_text, response.status, {
        "attempt": attempt,
        "max_retries": config.max_retries
    })
    
    if error_result.get("retry_recommended", False) and attempt < config.max_retries - 1:
        retry_delay = error_result.get("retry_delay", 2 ** attempt)
        await asyncio.sleep(retry_delay)
        continue
    else:
        raise Exception(f"API error: {error_result.get('error_details', {}).get('error_message', error_text)}")
```

## 🔧 Module Codes

| Module | Code | Module | Code |
|--------|------|--------|------|
| GIDVM | 01 | EMM | 16 |
| PBRPM | 02 | MSM | 17 |
| AACM | 03 | SMSM | 18 |
| FBWM | 04 | SMCM | 19 |
| FDM | 05 | JFAIM | 1A |
| PRM | 06 | OCMIM | 1B |
| RTRMM | 07 | BAAIM | 10 |
| RLM | 08 | SAAIM | 11 |
| MMM | 09 | AAAIM | 0F |
| DRM | 0A | FAIM | 0B |
| BTM | 0C | IFCM | 0D |
| ECM | 0E | SODVM | 12 |
| TMM | 15 | FOM | 13 |
| DCMM | 14 | | |

## 🚨 API Error Types

### Quick Reference
- `401_incorrect_key` - Wrong API key
- `429_rate_limit` - Rate limit exceeded
- `503_engine_overloaded` - Server overloaded
- `503_slow_down` - Too many requests
- `500_server_error` - Internal server error

### Recovery Strategies
- **Rate Limits**: Exponential backoff, retry
- **Server Errors**: Exponential backoff, retry
- **Authentication**: No retry, manual intervention
- **Quota Exceeded**: No retry, billing intervention

## 🏗️ Module-Specific Patterns

### File-Based Modules (FOM, SODVM, FBWM)
```python
# Handle file operation errors
try:
    with open(file_path, 'w') as f:
        json.dump(data, f)
except PermissionError as e:
    self.log_error(f"Permission denied writing to {file_path}", "FileManager", "write_file")
except OSError as e:
    self.log_error(f"OS error writing to {file_path}: {e}", "FileManager", "write_file")
```

### Memory Management Modules (MMM)
```python
# Lightweight error handling for memory operations
try:
    result = self.memory_intensive_operation()
except MemoryError as e:
    await self.spill_critical_data()  # Immediate action
    self.log_error("Memory error during operation", "MemoryManager", "intensive_operation")
```

### API Communication Modules (AACM, BAAIM, SAAIM, AAAIM)
```python
# Retry logic with exponential backoff
for attempt in range(max_retries):
    try:
        response = await self.make_api_call()
        break
    except aiohttp.ClientResponseError as e:
        if e.status == 429 and attempt < max_retries - 1:
            retry_delay = 2 ** attempt
            await asyncio.sleep(retry_delay)
            continue
        else:
            await self.handle_api_error(str(e), e.status, {"attempt": attempt})
            raise
```

### Database Modules (DCMM)
```python
# Transaction and connection error handling
try:
    async with self.db.transaction():
        await self.execute_query(query)
except asyncpg.DeadlockDetectedError as e:
    self.log_error("Database deadlock detected", "DatabaseManager", "execute_transaction")
    # Implement deadlock resolution
except asyncpg.ConnectionDoesNotExistError as e:
    self.log_error("Database connection lost", "DatabaseManager", "execute_transaction")
    await self.reconnect()
```

### Monitoring Modules (MSM, SMSM, SMCM)
```python
# Non-blocking error handling for monitoring
try:
    await self.collect_metrics()
except Exception as e:
    # Don't let monitoring errors break the system
    self.log_error(f"Monitoring error: {e}", "MonitoringManager", "collect_metrics")
    await self.fallback_monitoring()  # Continue with degraded monitoring
```

## ✅ Checklist

- [ ] Added EMM imports
- [ ] Initialized error_manager in __init__
- [ ] Removed hardcoded error_codes dictionary
- [ ] Added log_error method
- [ ] Added generate_error_code method
- [ ] Added handle_exception method
- [ ] Added handle_api_error method
- [ ] Updated error logging calls
- [ ] Updated API error handling
- [ ] Tested error code generation
- [ ] Tested error logging
- [ ] Tested exception handling
- [ ] Tested API error handling
- [ ] Updated tests to use dynamic error codes

## 🐛 Troubleshooting

### Common Issues

1. **Import Error**: Ensure `from EMM.emm import ErrorManagementModule`
2. **Hardcoded Codes**: Remove `self.error_codes` dictionary
3. **API Errors**: Use `handle_api_error` for status codes 401, 403, 429, 500, 503
4. **Async Issues**: Ensure `handle_exception` and `handle_api_error` are async
5. **Test Failures**: Update tests to use dynamic error codes instead of hardcoded ones
6. **Memory Leaks**: Keep error messages concise (< 1000 chars)
7. **Circular Imports**: Use lazy imports if needed

### Testing

```python
# Test error handling
error_code = self.generate_error_code("TestClass", "test_function")
print(f"Generated: {error_code}")

log_result = self.log_error("Test error", "TestClass", "test_function")
print(f"Logged: {log_result}")

# Test API error handling
test_error = '{"error": {"message": "Rate limit exceeded", "type": "rate_limit_error"}}'
result = await self.handle_api_error(test_error, 429)
print(f"API Error: {result['api_error_type']}")

# Test module code verification
error_code = self.generate_error_code("TestClass", "test_function")
expected_module_code = "10"  # For BAAIM
assert error_code[6:8] == expected_module_code, f"Expected {expected_module_code}, got {error_code[6:8]}"
```

## 📊 Statistics

```python
# Get EMM statistics
emm_stats = self.error_manager.get_error_statistics()
print(f"Total errors: {emm_stats['total_errors']}")

# Get API error handler statistics
api_stats = api_error_handler.get_statistics()
print(f"API errors: {api_stats['total_errors']}")
print(f"Recovery rate: {api_stats['recovery_rate']}%")
```

## 🔄 Migration from Old System

### Before (Old System)
```python
# Hardcoded error codes
self.error_codes = {
    "API_CALL_ERROR": "01010310001",
    "MODEL_NOT_FOUND": "01010310002"
}

# Generic error logging
self.error_manager.log_error_with_generation("MODULE", "UnknownClass", "UnknownFunction", error_msg)

# Tests expecting hardcoded codes
assert "API_CALL_ERROR" in module.error_codes
```

### After (New System)
```python
# Dynamic error codes
# Error codes now generated dynamically by EMM

# Specific error logging
self.log_error(error_msg, "SpecificClass", "specific_function")

# Tests using dynamic codes
error_code = module.generate_error_code("TestClass", "test_function")
assert len(error_code) == 16
assert error_code[6:8] == "10"  # Module code verification
```

---

**Need Help?** See the full documentation: `ERROR_HANDLING_DOCUMENTATION.md` 