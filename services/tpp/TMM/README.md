# TPP Microservice Test Suite

This directory contains the comprehensive test suite for the Text Processing and Purification (TPP) microservice, implemented following the same pattern as the RLA microservice test suite.

## Test Structure

The test suite is organized into the following categories:

### Module Unit Tests (T00000001 - T00000013)
Individual module tests that validate the core functionality of each of the 13 specialized modules in isolation:

- **T00000001**: TPDM (Text Processing Data Module) - Text preprocessing and metrics
- **T00000002**: SWM (Spam Word Management Module) - Multi-language spam word management
- **T00000003**: FTM (Filter Text Module) - Spam word filtering with order preservation
- **T00000004**: LPM (Language Processing Module) - Multi-language detection
- **T00000005**: IPM (Input Processing Module) - Input validation and security
- **T00000006**: OPM (Output Processing Module) - Output formatting and legacy support
- **T00000007**: FIM (File Interface Module) - File format support
- **T00000008**: ECM (External Control Module) - CCU communication hub
- **T00000009**: ARM (API Request Module) - API request routing
- **T00000010**: CIM (Configuration Interface Module) - Configuration management
- **T00000011**: EMM (Error Management Module) - Error handling and logging
- **T00000012**: MSM (Monitoring System Module) - Performance metrics collection
- **T00000013**: TMM (Test Management Module) - Integrated testing framework

### API Endpoint & Integration Tests (T00000014 - T00000015)
Tests for API endpoints and integration scenarios:

- **T00000014**: API Test - Process Text Endpoint
- **T00000015**: API Test - Manage Spam Lists

### CCU Integration & E2E Scenarios (T00000016 - T00000018)
End-to-end tests and CCU integration scenarios:

- **T00000016**: E2E Happy Path (Persian Text)
- **T00000017**: E2E Spam Filtering Path (English Text)
- **T00000018**: E2E CCU Command - Update Filter Strictness

## Running the Tests

### Individual Test Execution
```bash
# Run a specific test
python test_t00000001.py

# Run the test suite
python test_suite.py
```

### Test Suite Execution
```bash
# Run all tests
python test_suite.py
```

## Test Dependencies

The tests require the following dependencies:
- `asyncio` - For asynchronous test execution
- `aiohttp` - For HTTP API testing
- `websockets` - For WebSocket communication testing
- `json` - For JSON data handling
- `tempfile` - For temporary file operations
- `os` - For environment variable manipulation

## Test Configuration

Tests are designed to be resilient to service availability:
- If the TPP service is not running, tests will gracefully handle connection errors
- Tests include fallback logic for expected limitations
- All tests return structured results with success/failure indicators

## Test Results Format

Each test returns a standardized result format:
```json
{
    "success": true/false,
    "test_code": "T000000XX",
    "test_name": "Test Description",
    "message": "Success/failure message",
    "details": {
        "steps": [true, false, true, ...],
        "additional_data": "..."
    }
}
```

## Integration with TMM

The Test Management Module (TMM) provides:
- Test discovery and execution
- Result aggregation and reporting
- Test statistics and history
- Performance monitoring
- Integration with the broader microservice architecture

## Notes

- Tests follow the same naming convention as RLA: `test_t000000XX.py`
- All tests are asynchronous and use `asyncio`
- Tests include comprehensive error handling and graceful degradation
- The test suite is designed to be run independently or as part of the larger system 