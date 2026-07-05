# JFA Microservice Test Suite

This directory contains comprehensive test scripts for the JFA (JSON File Analyzer) microservice, implementing all test cases from the JFA Microservice Test Sheet.

## Test Structure

The test suite consists of **18 test cases** organized into two categories:

### Unit Tests (T00000001-T0000014)
Individual module functionality testing covering all 14 JFA modules:

1. **T00000001**: JDPM (JSON Data Processing Module) Unit Test
2. **T00000002**: TVM (Template Validation Module) Unit Test
3. **T00000003**: BDM (Binary Data Module) Unit Test
4. **T00000004**: DAM (Data Analysis Module) Unit Test
5. **T00000005**: IPM (Input Processing Module) Unit Test
6. **T00000006**: OPM (Output Processing Module) Unit Test
7. **T00000007**: FIM (File Interface Module) Unit Test
8. **T00000008**: ECM (External Control Module) Unit Test
9. **T00000009**: ARM (API Request Module) Unit Test
10. **T00000010**: CIM (Configuration Interface Module) Unit Test
11. **T00000011**: EMM (Error Management Module) Unit Test
12. **T00000012**: MSM (Monitoring System Module) Unit Test
13. **T00000013**: BTM (Background Tasks Module) Unit Test
14. **T00000014**: TMM (Test Management Module) Unit Test

### Integration & E2E Tests (T0000015-T0000018)
End-to-end workflow and API integration testing:

15. **T00000015**: API Test - Batch Processing Endpoint
16. **T00000016**: E2E Happy Path Scenario
17. **T00000017**: E2E Pipeline Failure (Validation Stage)
18. **T00000018**: Security Test - API Key Authentication

## Files

- `test_t00000001.py` - `test_t00000018.py`: Individual test scripts
- `test_suite.py`: Comprehensive test suite runner
- `tmm.py`: Test Management Module (existing)
- `README.md`: This documentation

## Running Tests

### Prerequisites

1. Ensure all JFA modules are properly installed and accessible
2. Install required dependencies:
   ```bash
   pip install aiohttp uvicorn websockets
   ```

### Running All Tests

```bash
cd services/jfa/TMM
python test_suite.py
```

### Running Specific Test Categories

```python
from test_suite import JFATestSuite

# Run only unit tests
test_suite = JFATestSuite()
results = await test_suite.run_unit_tests()

# Run only integration tests
results = await test_suite.run_integration_tests()

# Run a specific test
result = await test_suite.run_specific_test("test_t00000001")
```

### Running Individual Tests

```bash
# Run a specific test
python -c "
import asyncio
import test_t00000001
result = asyncio.run(test_t00000001.test_t00000001())
print(result)
"
```

## Test Results

Each test returns a standardized result structure:

```python
{
    "success": bool,           # Test passed/failed
    "test_code": str,          # Test identifier (e.g., "T00000001")
    "test_name": str,          # Human-readable test name
    "message": str,            # Success/failure message
    "details": dict,           # Detailed test results
    "execution_time": float,   # Test execution time in seconds
    "timestamp": str           # ISO timestamp
}
```

## Test Coverage

### Module Unit Tests (T00000001-T0000014)

Each unit test validates:
- Module initialization and startup
- Core functionality
- Error handling
- Configuration management
- Health checks
- Module-specific features

### API & Integration Tests (T00000015-T0000018)

These tests validate:
- API endpoint functionality
- End-to-end processing pipelines
- Error handling and recovery
- Security features
- Cross-module integration

## Key Test Scenarios

### JDPM (T00000001)
- Valid JSON template processing
- Depth and size limit enforcement
- Key normalization
- Error handling for invalid JSON

### TVM (T00000002)
- Business rule validation
- Schema validation
- Required field checking
- Solar energy system specific rules

### BDM (T00000003)
- Binary data generation
- Compression and checksum validation
- Size limit enforcement
- File persistence

### DAM (T00000004)
- Statistical analysis
- Anomaly detection
- Quality scoring
- Decision making

### IPM (T00000005)
- Input sanitization
- Security validation
- Injection attack detection
- Data preprocessing

### OPM (T00000006)
- Output formatting
- JFA_flag generation
- Metadata encapsulation
- Response structure validation

### FIM (T00000007)
- File I/O operations
- Data persistence
- Binary file handling
- File integrity validation

### ECM (T00000008)
- CCU WebSocket communication
- Service registration
- Auto-reconnection
- Command processing

### ARM (T00000009)
- API endpoint routing
- HTTP request handling
- Response formatting
- Error status codes

### CIM (T00000010)
- Configuration loading
- Environment variable override
- Configuration validation
- Dynamic updates

### EMM (T00000011)
- Error code generation
- Centralized error handling
- Error logging
- Recovery strategies

### MSM (T00000012)
- System metrics collection
- Performance monitoring
- Resource tracking
- Health reporting

### BTM (T00000013)
- Background task scheduling
- Task execution
- File cleanup
- Non-blocking operations

### TMM (T00000014)
- Test framework validation
- Test discovery
- Result collection
- Test execution

### API Tests (T00000015-T00000018)
- Batch processing endpoints
- End-to-end workflows
- Pipeline failure handling
- Security authentication

## Configuration

### Environment Variables

Some tests may require specific environment variables:

```bash
export JFA_LOG_LEVEL=DEBUG
export JFA_API_KEY=test-api-key
```

### Test Data

Tests use generic Horus request templates to validate JFA core functionality.

## Troubleshooting

### Common Issues

1. **Module Import Errors**: Ensure all JFA modules are in the Python path
2. **API Server Issues**: Check if port 8001 is available for API tests
3. **WebSocket Connection**: Ensure CCU mock server can start on port 11491
4. **File Permissions**: Ensure write permissions for temporary files

### Debug Mode

Run tests with verbose output:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Integration with CI/CD

The test suite can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run JFA Tests
  run: |
    cd services/jfa/TMM
    python test_suite.py
```

## Test Results Export

Test results are automatically exported to JSON files with timestamps:

```
jfa_test_results_20240115_143022.json
```

## Contributing

When adding new tests:

1. Follow the naming convention: `test_t000000XX.py`
2. Implement the standard result structure
3. Add test metadata to `test_suite.py`
4. Update this README with test descriptions

## Support

For issues with the test suite, check:
1. Module dependencies and imports
2. Network connectivity for API tests
3. File system permissions
4. Python environment compatibility 