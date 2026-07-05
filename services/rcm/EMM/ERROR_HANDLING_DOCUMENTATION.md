# Comprehensive Error Handling System Documentation

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Error Code System](#error-code-system)
4. [API Error Handling](#api-error-handling)
5. [Module Integration](#module-integration)
6. [Usage Examples](#usage-examples)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)
9. [API Reference](#api-reference)
10. [Module-Specific Patterns](#module-specific-patterns)
11. [Common Issues & Solutions](#common-issues--solutions)
12. [Advanced Integration](#advanced-integration)

---

## Overview

The Comprehensive Error Handling System is a centralized error management solution for the RCM microservice architecture. It provides:

- **Dynamic Error Code Generation**: 16-character hexadecimal error codes
- **Centralized Error Logging**: All errors logged through EMM
- **API Error Mapping**: OpenAI API errors mapped to internal codes
- **Automated Recovery**: Intelligent retry and recovery strategies
- **CCU Reporting**: Automatic error reports sent to Central Control Unit

### Key Features

✅ **EMM Integration**: All modules use centralized error management  
✅ **Hardcoded Code Removal**: Dynamic error code generation  
✅ **API Error Handling**: Comprehensive OpenAI API error support  
✅ **Recovery Strategies**: Automated recovery for each error type  
✅ **CCU Reporting**: Real-time error reporting to CCU  
✅ **Dual Error Code System**: Internal hex codes + API readable codes  

---

## Architecture

### Core Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   EMM Module    │    │ API Error Handler│    │   CCU Reports   │
│                 │    │                  │    │                 │
│ • Error Codes   │◄──►│ • Error Mapping  │◄──►│ • Error Reports │
│ • Error Logging │    │ • Recovery Logic │    │ • Statistics    │
│ • Statistics    │    │ • Retry Logic    │    │ • Monitoring    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         ▲                       ▲                       ▲
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    RCM Modules                                  │
│                                                                 │
│  BAAIM  SAAIM  AAAIM  JFAIM  OCMIM  AACM  ...                  │
│    │      │      │      │      │      │                        │
│    └──────┴──────┴──────┴──────┴──────┴────────────────────────┘
```

### Error Flow

1. **Error Occurs** → Module detects error
2. **Error Logging** → EMM logs error with generated code
3. **Error Analysis** → API Error Handler analyzes error type
4. **Recovery Attempt** → Automated recovery strategy applied
5. **CCU Report** → Error report sent to Central Control Unit
6. **Statistics Update** → Error statistics updated

---

## Error Code System

### Internal Error Codes (16-char hex)

**Format**: `[Server][Macro][Micro][Module][Class][Function][Sub-function]`

**Example**: `0101031600010001`

- **Server Code**: `01` - Main server
- **Macro Service**: `01` - RCM service
- **Micro Service**: `03` - Error Management
- **Module Code**: `16` - EMM module
- **Class Code**: `0001` - Specific class
- **Function Code**: `0001` - Specific function

### API Error Codes (Human-readable)

**Format**: `API_[STATUS]_[TYPE]`

**Examples**:
- `API_401_AUTH` - Authentication error
- `API_429_RATE` - Rate limit error
- `API_503_OVERLOAD` - Server overload error

### Module Codes

| Module | Code | Description |
|--------|------|-------------|
| GIDVM | 01 | Get Input Data and Verification |
| PBRPM | 02 | Priority Based Request Processing |
| AACM | 03 | Asynchronous API Communication |
| FBWM | 04 | File Based Workflow |
| FDM | 05 | File Detection |
| PRM | 06 | Priority Routing |
| RTRMM | 07 | Request Tracking and Response Mapping |
| RLM | 08 | Rate Limiting |
| MMM | 09 | Memory Management |
| DRM | 0A | Disk Restoration |
| FAIM | 0B | Fast API Integration |
| BTM | 0C | Background Tasks |
| IFCM | 0D | Internal Flow Control |
| ECM | 0E | External Control |
| AAAIM | 0F | Agentic API Activation |
| BAAIM | 10 | Basic API Activation |
| SAAIM | 11 | Special API Activation |
| SODVM | 12 | Set Output Data and Verification |
| FOM | 13 | File Output |
| DCMM | 14 | Database Control and Management |
| TMM | 15 | Test Management |
| EMM | 16 | Error Management |
| MSM | 17 | Monitoring System |
| SMSM | 18 | System Message Subjoin |
| SMCM | 19 | System Model Changer |
| JFAIM | 1A | JFA Interaction |
| OCMIM | 1B | OCM Interaction |

---

## API Error Handling

### Supported Error Types

#### Authentication Errors (401)
- **INVALID_AUTHENTICATION**: Invalid authentication credentials
- **INCORRECT_API_KEY**: Incorrect API key provided
- **NOT_ORGANIZATION_MEMBER**: Not a member of organization

#### Authorization Errors (403)
- **COUNTRY_NOT_SUPPORTED**: Country/region not supported

#### Rate Limit Errors (429)
- **RATE_LIMIT_REACHED**: Rate limit exceeded
- **QUOTA_EXCEEDED**: Quota exceeded

#### Server Errors (500, 503)
- **SERVER_ERROR**: Internal server error
- **ENGINE_OVERLOADED**: Engine overloaded
- **SLOW_DOWN**: Slow down request

#### Python Library Errors
- **API_CONNECTION_ERROR**: Connection issues
- **API_TIMEOUT_ERROR**: Request timeout
- **AUTHENTICATION_ERROR**: Authentication issues
- **BAD_REQUEST_ERROR**: Invalid request
- **RATE_LIMIT_ERROR**: Rate limiting
- **INTERNAL_SERVER_ERROR**: Server errors

### Recovery Strategies

| Error Type | Retry Strategy | Max Retries | Base Delay | Max Delay |
|------------|----------------|-------------|------------|-----------|
| Rate Limit | Exponential backoff | 3 | 5s | 60s |
| Server Error | Exponential backoff | 3 | 2s | 30s |
| Engine Overloaded | Exponential backoff | 5 | 10s | 120s |
| Slow Down | Exponential backoff | 3 | 15s | 300s |
| Connection Error | Exponential backoff | 3 | 1s | 10s |
| Timeout Error | Exponential backoff | 2 | 2s | 10s |
| Quota Exceeded | No retry | 1 | 0s | 0s |
| Authentication | No retry | 0 | 0s | 0s |

---

## Module Integration

### Required Methods

All modules must implement these error handling methods:

```python
def log_error(self, error_message: str, class_name: str = "UnknownClass", 
              function_name: str = "UnknownFunction", sub_function: str = "001"):
    """Log an error using EMM."""
    return self.error_manager.log_error_with_generation(
        "MODULE_NAME", 
        class_name, 
        function_name, 
        error_message, 
        sub_function
    )

def generate_error_code(self, class_name: str = "UnknownClass", 
                       function_name: str = "UnknownFunction", 
                       sub_function: str = "001") -> str:
    """Generate an error code using EMM."""
    return self.error_manager.generate_error_code("MODULE_NAME", class_name, function_name, sub_function)

async def handle_exception(self, exception: Exception, class_name: str = "UnknownClass", 
                          function_name: str = "UnknownFunction", context: dict = None):
    """Handle exceptions with comprehensive logging and recovery."""
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
    """Handle API errors using the centralized API error handler."""
    try:
        result = await api_error_handler.handle_api_error(error_response, status_code, context)
        self.error_manager.log_error_with_generation(
            "MODULE_NAME",
            "MODULE_NAME",
            "handle_api_error",
            f"API Error: {result.get('api_error_type', 'unknown')}",
            context=result
        )
        await api_error_handler.send_error_report_to_ccu(result)
        return result
    except Exception as e:
        self.error_manager.log_error_with_generation(
            "MODULE_NAME",
            "MODULE_NAME",
            "handle_api_error",
            f"Error handling API error: {str(e)}"
        )
        return {"success": False, "error": str(e)}
```

### Required Imports

```python
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler
```

### Module Initialization

```python
def __init__(self):
    self.error_manager = ErrorManagementModule()
    # Remove hardcoded error_codes dictionary
    # Error codes now generated dynamically by EMM
```

---

## Usage Examples

### Basic Error Logging

```python
# Log a simple error
error_code = self.log_error("Database connection failed", "DatabaseManager", "connect")

# Generate error code without logging
error_code = self.generate_error_code("UserManager", "authenticate", "001")
```

### Exception Handling

```python
try:
    result = await self.make_api_call()
except Exception as e:
    error_result = await self.handle_exception(e, "APIManager", "make_api_call", {
        "endpoint": "/chat/completions",
        "model": "gpt-4"
    })
    return error_result
```

### API Error Handling

```python
# Handle API errors in HTTP requests
if response.status in [401, 403, 429, 500, 503]:
    error_text = await response.text()
    error_result = await self.handle_api_error(error_text, response.status, {
        "attempt": attempt,
        "max_retries": config.max_retries,
        "model": config.model
    })
    
    if error_result.get("retry_recommended", False) and attempt < config.max_retries - 1:
        retry_delay = error_result.get("retry_delay", 2 ** attempt)
        await asyncio.sleep(retry_delay)
        continue
    else:
        raise Exception(f"API error: {error_result.get('error_details', {}).get('error_message', error_text)}")
```

### System-Wide Error Handling (RCM_main.py)

```python
# Handle system-wide errors
def handle_system_error(self, error: Exception, context: str = "Unknown"):
    return self.modules['EMM'].log_error_with_generation(
        "RCM_MAIN",
        "RCM",
        context,
        str(error)
    )

# Handle API errors system-wide
async def handle_api_error_system_wide(self, error_response: str, status_code: int = None):
    return await api_error_handler.handle_api_error(error_response, status_code)
```

---

## Best Practices

### 1. Error Logging

✅ **Do**:
```python
# Use descriptive error messages
self.log_error("Failed to connect to database: connection timeout", "DatabaseManager", "connect")

# Include context in error messages
self.log_error(f"API request failed for model {model}: {error}", "APIManager", "make_request")
```

❌ **Don't**:
```python
# Avoid generic error messages
self.log_error("Error occurred", "UnknownClass", "UnknownFunction")

# Don't log sensitive information
self.log_error(f"API key {api_key} is invalid", "AuthManager", "validate")
```

### 2. Exception Handling

✅ **Do**:
```python
try:
    result = await self.process_data(data)
except ValueError as e:
    # Handle specific exceptions
    return await self.handle_exception(e, "DataProcessor", "process_data", {"data_type": type(data)})
except Exception as e:
    # Handle general exceptions
    return await self.handle_exception(e, "DataProcessor", "process_data")
```

❌ **Don't**:
```python
try:
    result = await self.process_data(data)
except Exception as e:
    # Don't ignore exceptions
    pass
```

### 3. API Error Handling

✅ **Do**:
```python
# Use centralized API error handling
if response.status in [401, 403, 429, 500, 503]:
    error_result = await self.handle_api_error(error_text, response.status, context)
    # Follow retry recommendations
    if error_result.get("retry_recommended", False):
        # Implement retry logic
```

❌ **Don't**:
```python
# Don't implement custom retry logic
if response.status == 429:
    await asyncio.sleep(5)  # Fixed delay
    # Retry without considering error handler recommendations
```

### 4. Error Code Generation

✅ **Do**:
```python
# Use meaningful class and function names
error_code = self.generate_error_code("UserAuthentication", "validate_credentials", "001")
```

❌ **Don't**:
```python
# Don't use generic names
error_code = self.generate_error_code("Class", "function", "001")
```

---

## Module-Specific Patterns

### File-Based Modules (FOM, SODVM, FBWM)

**Special Considerations:**
- File operations can fail due to permissions, disk space, or file locks
- Use specific error context for file operations
- Include file paths in error messages (but sanitize sensitive paths)

```python
# Good: File operation error handling
try:
    with open(file_path, 'w') as f:
        json.dump(data, f)
except PermissionError as e:
    self.log_error(f"Permission denied writing to {file_path}", "FileManager", "write_file")
except OSError as e:
    self.log_error(f"OS error writing to {file_path}: {e}", "FileManager", "write_file")
```

### Memory Management Modules (MMM)

**Special Considerations:**
- Memory errors can cascade quickly
- Use lightweight error handling to avoid memory overhead
- Prioritize critical memory operations

```python
# Good: Memory-aware error handling
try:
    # Critical memory operation
    result = self.memory_intensive_operation()
except MemoryError as e:
    # Immediate spill to disk
    await self.spill_critical_data()
    self.log_error("Memory error during operation", "MemoryManager", "intensive_operation")
```

### API Communication Modules (AACM, BAAIM, SAAIM, AAAIM)

**Special Considerations:**
- Network timeouts and connection issues
- Rate limiting and quota management
- API version compatibility

```python
# Good: API error handling with retry logic
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

**Special Considerations:**
- Connection pooling and transaction management
- Deadlock detection and resolution
- Data integrity constraints

```python
# Good: Database error handling
try:
    async with self.db.transaction():
        await self.execute_query(query)
except asyncpg.DeadlockDetectedError as e:
    self.log_error("Database deadlock detected", "DatabaseManager", "execute_transaction")
    # Implement deadlock resolution strategy
except asyncpg.ConnectionDoesNotExistError as e:
    self.log_error("Database connection lost", "DatabaseManager", "execute_transaction")
    await self.reconnect()
```

### Monitoring Modules (MSM, SMSM, SMCM)

**Special Considerations:**
- Avoid error loops in monitoring systems
- Graceful degradation when monitoring fails
- Non-blocking error reporting

```python
# Good: Monitoring error handling
try:
    await self.collect_metrics()
except Exception as e:
    # Don't let monitoring errors break the system
    self.log_error(f"Monitoring error: {e}", "MonitoringManager", "collect_metrics")
    # Continue with degraded monitoring
    await self.fallback_monitoring()
```

---

## Common Issues & Solutions

### 1. Import Errors

**Problem**: `ModuleNotFoundError: No module named 'EMM'`

**Solution**: Ensure proper import paths and module structure
```python
# Correct import
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler
```

### 2. Circular Import Dependencies

**Problem**: Modules importing each other causing circular dependencies

**Solution**: Use lazy imports or dependency injection
```python
# Lazy import approach
def get_error_manager(self):
    if not hasattr(self, '_error_manager'):
        from EMM.emm import ErrorManagementModule
        self._error_manager = ErrorManagementModule()
    return self._error_manager
```

### 3. Async/Sync Method Mismatches

**Problem**: Calling async methods from sync contexts or vice versa

**Solution**: Ensure proper async/await usage
```python
# Correct async error handling
async def handle_exception(self, exception: Exception, ...):
    # Async method implementation
    pass

# Correct sync error handling
def log_error(self, error_message: str, ...):
    # Sync method implementation
    pass
```

### 4. Error Code Collisions

**Problem**: Multiple modules generating the same error codes

**Solution**: Use unique module codes and proper naming
```python
# Each module has a unique code in the error code system
# PRM = 06, OCMIM = 1B, FOM = 13, etc.
```

### 5. Memory Leaks in Error Handling

**Problem**: Error handling code consuming too much memory

**Solution**: Use lightweight error handling and cleanup
```python
# Lightweight error handling
def log_error(self, error_message: str, ...):
    # Keep error messages concise
    if len(error_message) > 1000:
        error_message = error_message[:1000] + "..."
    return self.error_manager.log_error_with_generation(...)
```

### 6. Test Failures After Integration

**Problem**: Tests expecting hardcoded error codes fail after removal

**Solution**: Update tests to use dynamic error codes
```python
# Old test (will fail)
assert "API_CALL_ERROR" in module.error_codes

# New test (will pass)
error_code = module.generate_error_code("TestClass", "test_function")
assert len(error_code) == 16  # Verify format
assert error_code[6:8] == "10"  # Verify module code for BAAIM
```

---

## Advanced Integration

### Custom Error Types

For modules with specific error requirements, you can extend the error handling:

```python
class CustomErrorHandler:
    def __init__(self, module_name: str):
        self.module_name = module_name
        self.error_manager = ErrorManagementModule()
    
    async def handle_custom_error(self, error_type: str, context: dict = None):
        """Handle module-specific errors."""
        error_code = self.error_manager.generate_error_code(
            self.module_name, "CustomErrorHandler", error_type
        )
        
        # Module-specific error handling logic
        if error_type == "DATABASE_CONNECTION":
            # Handle database connection errors
            pass
        elif error_type == "FILE_PERMISSION":
            # Handle file permission errors
            pass
        
        return {
            "success": False,
            "error_code": error_code,
            "error_type": error_type,
            "context": context
        }
```

### Error Recovery Strategies

Implement custom recovery strategies for specific modules:

```python
class RecoveryManager:
    def __init__(self):
        self.recovery_strategies = {
            "database": self._recover_database,
            "file_system": self._recover_file_system,
            "api": self._recover_api,
            "memory": self._recover_memory
        }
    
    async def _recover_database(self, error_context: dict):
        """Recover from database errors."""
        # Implement database recovery logic
        pass
    
    async def _recover_file_system(self, error_context: dict):
        """Recover from file system errors."""
        # Implement file system recovery logic
        pass
    
    async def _recover_api(self, error_context: dict):
        """Recover from API errors."""
        # Implement API recovery logic
        pass
    
    async def _recover_memory(self, error_context: dict):
        """Recover from memory errors."""
        # Implement memory recovery logic
        pass
```

### Performance Monitoring

Monitor error handling performance:

```python
class ErrorPerformanceMonitor:
    def __init__(self):
        self.error_times = {}
        self.error_counts = {}
    
    def start_error_timer(self, error_type: str):
        """Start timing an error operation."""
        self.error_times[error_type] = time.time()
    
    def end_error_timer(self, error_type: str):
        """End timing an error operation."""
        if error_type in self.error_times:
            duration = time.time() - self.error_times[error_type]
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
            return duration
        return 0
    
    def get_error_stats(self):
        """Get error handling statistics."""
        return {
            "error_counts": self.error_counts,
            "average_times": self._calculate_average_times()
        }
```

---

## Troubleshooting

### Common Issues

#### 1. "no such group" Error in Integration Script

**Problem**: Regex parsing fails for certain module structures.

**Solution**: Manually update the module using the patterns shown in this documentation.

#### 2. Hardcoded Error Codes Still Present

**Problem**: Some modules still have `self.error_codes` dictionaries.

**Solution**: Remove the dictionary and replace with:
```python
# Error codes now generated dynamically by EMM
```

#### 3. API Error Handling Not Working

**Problem**: API errors not being handled by centralized handler.

**Solution**: Ensure the module has:
- `from EMM.api_error_handler import api_error_handler`
- `handle_api_error` method implemented
- Proper status code checking in HTTP requests

#### 4. EMM Import Errors

**Problem**: Module cannot import EMM.

**Solution**: Ensure the module has:
- `from EMM.emm import ErrorManagementModule`
- `self.error_manager = ErrorManagementModule()` in `__init__`

### Debugging

#### Check Error Logs

```python
# Get EMM statistics
emm_stats = self.modules['EMM'].get_error_statistics()
print(f"Total errors: {emm_stats['total_errors']}")
print(f"Errors by module: {emm_stats['errors_by_module']}")
```

#### Check API Error Handler Statistics

```python
# Get API error handler statistics
api_stats = api_error_handler.get_statistics()
print(f"API errors: {api_stats['total_errors']}")
print(f"Recovery rate: {api_stats['recovery_rate']}%")
```

#### Test Error Handling

```python
# Test error code generation
error_code = self.generate_error_code("TestClass", "test_function")
print(f"Generated error code: {error_code}")

# Test error logging
log_result = self.log_error("Test error message", "TestClass", "test_function")
print(f"Error logged: {log_result}")
```

---

## API Reference

### ErrorManagementModule

#### Methods

- `log_error_with_generation(module_name, class_name, function_name, error_message, sub_function="001")`
- `generate_error_code(module_name, class_name, function_name, sub_function="001")`
- `get_error_statistics()`
- `get_error_logs()`

### APIErrorHandler

#### Methods

- `parse_api_error(error_response, status_code=None)`
- `handle_api_error(error_response, status_code=None, context=None)`
- `send_error_report_to_ccu(error_result)`
- `get_statistics()`

#### Error Types

- `APIErrorType.INVALID_AUTHENTICATION`
- `APIErrorType.RATE_LIMIT_REACHED`
- `APIErrorType.SERVER_ERROR`
- `APIErrorType.ENGINE_OVERLOADED`
- And more...

### Module Error Handling Methods

#### Required Methods

- `log_error(error_message, class_name, function_name, sub_function)`
- `generate_error_code(class_name, function_name, sub_function)`
- `handle_exception(exception, class_name, function_name, context)`
- `handle_api_error(error_response, status_code, context)`

---

## Migration Guide

### From Old Error Handling to New System

#### Step 1: Update Imports

```python
# Old
from EMM.emm import ErrorManagementModule

# New
from EMM.emm import ErrorManagementModule
from EMM.api_error_handler import api_error_handler
```

#### Step 2: Remove Hardcoded Error Codes

```python
# Old
self.error_codes = {
    "API_CALL_ERROR": "01010310001",
    "MODEL_NOT_FOUND": "01010310002",
    # ...
}

# New
# Error codes now generated dynamically by EMM
```

#### Step 3: Update Error Logging

```python
# Old
self.error_manager.log_error_with_generation("MODULE", "UnknownClass", "UnknownFunction", error_msg)

# New
self.log_error(error_msg, "SpecificClass", "specific_function")
```

#### Step 4: Add Error Handling Methods

Add the four required error handling methods to your module class.

#### Step 5: Update API Error Handling

Replace custom API error handling with centralized handler calls.

#### Step 6: Update Tests

Update any tests that reference hardcoded error codes:

```python
# Old test
assert "API_CALL_ERROR" in module.error_codes

# New test
error_code = module.generate_error_code("TestClass", "test_function")
assert len(error_code) == 16
```

---

## Conclusion

The Comprehensive Error Handling System provides a robust, centralized solution for error management across the RCM microservice architecture. By following this documentation and implementing the required methods, all modules will have consistent error handling, automated recovery, and comprehensive reporting capabilities.

### Key Benefits Achieved

1. **Centralized Error Management**: All errors logged through EMM with consistent formatting
2. **Dynamic Error Codes**: No more hardcoded error codes, all generated dynamically
3. **API Error Integration**: Comprehensive handling of OpenAI API errors with recovery strategies
4. **CCU Reporting**: Automatic error reports sent to Central Control Unit
5. **Module-Specific Patterns**: Tailored error handling for different module types
6. **Performance Monitoring**: Built-in performance tracking for error handling operations
7. **Test Compatibility**: Updated testing patterns for the new error handling system

### Next Steps

1. **Complete Module Updates**: Continue updating remaining modules with hardcoded error codes
2. **Comprehensive Testing**: Run full test suite to verify all integrations work correctly
3. **Performance Optimization**: Monitor and optimize error handling performance
4. **Documentation Maintenance**: Keep documentation updated as new patterns emerge

For additional support or questions, refer to the test files and integration examples provided in the codebase. 