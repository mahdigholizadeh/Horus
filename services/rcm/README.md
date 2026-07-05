# RCM ( Requests Cache Manager) Microservice - Modular Architecture

A comprehensive Python-based  Requests Cache Manager microservice built with a modular architecture, featuring priority-based request handling, asynchronous API interaction, and robust file processing workflows.

## Overview

The RCM microservice has been completely refactored into a modular architecture where each distinct function is encapsulated within its own module. This improves maintainability, scalability, and comprehensibility. The system is activated and deactivated by the Central Control Unit (CCU) and supports seamless interaction with other microservices.

## Architecture Principles

- **Modularization**: Each module is placed in its own dedicated folder with the acronym as the folder name
- **Request Tracking**: Every request has a unique Request ID that persists throughout the entire processing pipeline
- **Internal Workflow Control**: All interactions between modules are orchestrated by the Internal Flow Control Module (IFCM)
- **Object-Oriented Programming**: Extensive use of OOP principles for clean, reusable, and well-structured code
- **Comprehensive Documentation**: All code is thoroughly commented with detailed explanations

## Main Entry Point

The main entry point is `RCM_main.py`, which serves as the central controller responsible for:
- Initialization of all modules
- Testing and monitoring
- Interfacing with the CCU via the External Control Module (ECM)
- Orchestrating the modular architecture

## Module Specifications

### Core Processing Modules

#### 1. Get Input Data and Verification Module (GIDVM)
- **Function**: Listens for incoming JSON request files from the TPP block
- **Logic**: Verifies data integrity and stores files in priority-specific folders
- **Location**: `GIDVM/gidvm.py`

#### 2. Priority-based Request Processing Module (PBRPM)
- **Function**: Fetches and processes request files according to their assigned priority level
- **Location**: `PBRPM/pbrpm.py`

#### 3. Asynchronous API Communication Module (AACM)
- **Function**: Manages all interactions with the OpenAI API using async/await patterns
- **Location**: `AACM/aacm.py`

#### 4. File-based Workflow Module (FBWM)
- **Function**: Processes JSON request files, routes to correct workflows, cleans up temporary files
- **Location**: `FBWM/fbwm.py`

#### 5. File Detection Module (FDM)
- **Function**: Actively monitors input directories for new JSON files
- **Location**: `FDM/fdm.py`

#### 6. Priority Routing Module (PRM)
- **Function**: Routes incoming files to appropriate processing queues based on priority_flag
- **Location**: `PRM/prm.py`

#### 7. Request Tracking and Response Mapping Module (RTRMM)
- **Function**: Tracks requests and maps API responses back to original requests using unique Request ID
- **Location**: `RTRMM/rtrmm.py`

### Resource Management Modules

#### 8. Rate Limiting Module (RLM)
- **Function**: Implements configurable rate-limiting and automatic retry mechanisms
- **Location**: `RLM/rlm.py`

#### 9. Memory Management Module (MMM)
- **Function**: Monitors RAM usage and spills overflow data to disk when threshold is exceeded
- **Location**: `MMM/mmm.py`

#### 10. Disk Restoration Module (DRM)
- **Function**: Restores cached or queued data from disk back into memory when resources become available
- **Location**: `DRM/drm.py`

### Control and Integration Modules

#### 11. FastAPI Integration Module (FAIM)
- **Function**: Provides RESTful API endpoints for managing and monitoring the RCM service
- **Location**: `FAIM/faim.py`

#### 12. Background Tasks Module (BTM)
- **Function**: Runs automated, periodic tasks such as cleanup and maintenance operations
- **Location**: `BTM/btm.py`

#### 13. Internal Flow Control Module (IFCM)
- **Function**: Core workflow engine that orchestrates the entire lifecycle of a request
- **Responsibilities**: 
  - Manages step-by-step processing of each request by unique ID
  - Invokes other modules in correct sequence
  - Handles data flow between modules
  - Implements comprehensive error handling and recovery logic
  - Monitors status of each active request
- **Location**: `IFCM/ifcm.py`

#### 14. External Control Module (ECM)
- **Function**: Primary interface between RCM microservice and Central Control Unit (CCU)
- **Capabilities**:
  - Service Control: Activate/deactivate RCM service
  - Real-time Monitoring & Logging: Stream comprehensive logs to CCU
  - Request Forwarding: Forward output to next microservice (JFA)
  - Configuration Management: Dynamic API key and rate limit updates
  - Remote Test Execution: Trigger predefined tests with 8-character codes
  - Reset Functionality: Reset specific modules or entire RCM
  - Database Access: Query RCM databases
  - Port Configuration: Change OpenAI API ports
  - System Message Injection: Inject system messages into active conversations
  - Model Switching: Change API model for specific conversations
  - Error Reporting: Transmit detailed error logs to CCU
  - Monitoring Data: Stream MSM data to CCU
  - Automatic Code Generation: Generate new error codes when codebase changes
- **Location**: `ECM/ecm.py`

### API Interaction Modules

#### 15. Agentic API Activation and Interaction Module (AAAIM)
- **Function**: Interacts with OpenAI's "Agent" models
- **Configuration**: 
  - Default Agent ID: `"asst_lQCwiQAJcycDj7YqHBafyWtT"`
  - Allows override for specific requests
- **Location**: `AAAIM/aaaim.py`

#### 16. Basic API Activation and Interaction Module (BAAIM)
- **Function**: Standard, non-agentic interactions with OpenAI API
- **Configuration**:
  - Default model: `"gpt-4.1-nano"`
  - Provides mechanism to override API_KEY and model name
- **Location**: `BAAIM/baaim.py`

#### 17. Special API Activation and Interaction Module (SAAIM)
- **Function**: Interacts with custom-trained OpenAI models
- **Configuration**:
  - Stores default values for `DEFAULT_SPECIAL_API_KEY` and `DEFAULT_SPECIAL_API_MODEL_ID`
  - Accepts `SPECIAL_API_KEY` and `SPECIAL_API_MODEL_ID` as input
- **Location**: `SAAIM/saaim.py`

### Output and Verification Modules

#### 18. Set Output Data and Verification Module (SODVM)
- **Function**: Verifies integrity of JSON responses from API
- **Location**: `SODVM/sodvm.py`

#### 19. File Output Module (FOM)
- **Function**: Saves processed responses and error logs to appropriate output directories
- **Location**: `FOM/fom.py`

### Database and Management Modules

#### 20. Database Control and Management Module (DCMM)
- **Function**: Centralized module for all database operations
- **Responsibilities**:
  - Creating new databases
  - Querying, inserting, updating, and deleting records
  - Managing all database files stored within DCMM/ folder
- **Location**: `DCMM/dcmm.py`

#### 21. Test Management Module (TMM)
- **Function**: Stores and manages all test scripts for RCM microservice
- **Requirements**:
  - Each test script has unique 8-character code (T0000001, T0000002, etc.)
  - All test executions logged in dedicated database managed by DCMM
  - Each log entry includes test code, timestamp, and full output
- **Location**: `TMM/tmm.py`

#### 22. Error Management Module (EMM)
- **Function**: Manages all aspects of error detection, logging, and recovery
- **Error Code Structure**: 16-character hexadecimal string
  - Server Code (2 chars): 01
  - Macroservice Code (2 chars): 01
  - Microservice Code (2 chars): 03 (RCM)
  - Module Code (2 chars): 01-FF (hex value for module)
  - Class Code (2 chars): 01-FF (unique within module)
  - Function Code (3 chars): 001-FFF (unique within class)
  - Sub-function Code (3 chars): 001-FFF (specific errors within function)
- **Error Message Format**: "Error on server code = <server_code> on Macro service code = <macro_code> on Micro service code = <micro_code> on Module code = <module_code> occurred. The error is: <descriptive message>"
- **Automatic Code Generation**: Script to scan codebase for changes and generate new error codes
- **Location**: `EMM/emm.py`

### Monitoring and Control Modules

#### 23. Monitoring System Module (MSM)
- **Function**: Gathers and reports monitoring data
- **Responsibilities**:
  - Polls status and performance statistics of all modules every 10 seconds
  - Reports network traffic, connection statuses, and resource utilization
  - Calculates and reports token usage (4 characters = 1 token)
  - Output includes: input_tokens, output_tokens, system_tokens, total_tokens
- **Location**: `MSM/msm.py`

#### 24. System Message Subjoin Module (SMSM)
- **Function**: Allows CCU to intervene in conversations by injecting system-level messages
- **Logic**: Receives message and Request ID from CCU, edits conversation history
- **Location**: `SMSM/smsm.py`

#### 25. System Model Changer Module (SMCM)
- **Function**: Allows CCU to change underlying API model or interaction module
- **Logic**: If model is changed, entire conversation history must be resent to new model
- **Location**: `SMCM/smcm.py`

### Handoff Modules

#### 26. JFA Interaction Module (JFAIM)
- **Function**: Manages handoff of processed data to JFA (JSON Fulfillment & Analysis) block
- **Logic**: When API returns completed JSON template, extracts data and creates new file
- **Location**: `JFAIM/jfaim.py`

#### 27. OCM Interaction Module (OCMIM)
- **Function**: Manages handoff of user-facing responses to OCM (Output Control Manager) block
- **Logic**: When API returns direct response for user, creates JSON file with response and Request ID
- **Location**: `OCMIM/ocmim.py`

## Request Workflow

1. **Input Reception**: GIDVM receives JSON request files from TPP
2. **File Detection**: FDM monitors for new files and triggers processing
3. **Priority Routing**: PRM routes files based on priority_flag (A, B, C, D)
4. **Workflow Orchestration**: IFCM manages the entire request lifecycle
5. **API Interaction**: BAAIM/AAAIM/SAAIM handle API calls based on request type
6. **Response Processing**: SODVM verifies response integrity
7. **Output Generation**: FOM saves responses, JFAIM/OCMIM handle handoffs
8. **Monitoring**: MSM tracks performance and reports to CCU

## Testing Framework

The RCM microservice includes a comprehensive testing framework with 46 test cases:

### Unit Tests (T0000001-T0000046)
- **T0000001**: GIDVM - Successful Ingestion & Sorting
- **T0000002**: GIDVM - Invalid JSON Rejection
- **T0000003**: PBRPM - Priority Queue Processing
- **T0000004**: AACM - Successful Async API Call
- **T0000005**: RTRMM - Response to Request ID Mapping
- **T0000006**: RLM - Rate Limit Enforcement
- **T0000007**: MMM & DRM - Memory Spill-to-Disk & Restore
- **T0000008**: BAAIM - Default & Override API Usage
- **T0000009**: AAAIM - Default & Override Agent Usage
- **T0000010**: SAAIM - Special API Call
- **T0000011**: SODVM - JSON Verification
- **T0000012**: DCMM - Full CRUD Operations
- **T0000013**: TMM - Test Execution and Logging
- **T0000014**: EMM - Error Code Generation & Logging
- **T0000015**: MSM - System Monitoring Report
- **T0000016**: MSM - Token Calculation
- **T0000017**: SMSM - System Message Injection
- **T0000018**: SMCM - API Model Change
- **T0000019**: JFAIM - Handoff to JFA
- **T0000020**: OCMIM - Handoff to OCM
- **T0000021**: ECM - CCU Command Reception
- **T0000027**: RLM - Retry Mechanism on Failure
- **T0000028**: FAIM - API Endpoint Verification
- **T0000029**: BTM - Automated Cleanup Task
- **T0000030**: EMM - Error Code Auto-Generation
- **T0000031**: ECM - Dynamic Rate Limit Update
- **T0000032**: ECM - Module Reset Command
- **T0000033**: ECM - Remote DB Query
- **T0000040**: Human Interaction Benchmark
- **T0000041**: FDM - File Detection Module
- **T0000042**: FBWM - File-based Workflow Module
- **T0000043**: PRM - Priority Routing Module
- **T0000044**: FOM - File Output Module
- **T0000045**: BTM - Background Tasks Module Comprehensive
- **T0000046**: FAIM - FastAPI Integration Module Comprehensive

### Integration Tests (T0000022-T0000039)
- **T0000022**: Workflow: Standard Successful Request
- **T0000023**: Workflow: JFA Template Fulfillment
- **T0000024**: Workflow: Error Handling & Recovery
- **T0000025**: Workflow: CCU Remote Control - API Key Change
- **T0000026**: Workflow: CCU Remote Control - Test Execution
- **T0000034**: Workflow: High-Load Stress Test
- **T0000035**: Workflow: Mid-Conversation Model Switch
- **T0000036**: Workflow: Mid-Conversation System Message Injection
- **T0000037**: Workflow: End-to-End Failure, Retry, and Reporting
- **T0000038**: Workflow: Complex CCU Remote Control
- **T0000039**: Workflow: Concurrent Request Integrity

## Installation and Usage

### Prerequisites
- Python 3.8+
- Required packages listed in `requirements.txt`

### Installation
1. Install dependencies:
```bash
pip install -r requirements.txt
```

### Usage

#### Command Line Interface
```bash
# Run FastAPI server (default)
python RCM_main.py

# Activate the microservice
python RCM_main.py --activate

# Deactivate the microservice
python RCM_main.py --deactivate

# Check status
python RCM_main.py --status

# Start file processing workflow
python RCM_main.py --process

# Run test workflow
python RCM_main.py --test

# Run comprehensive test suite
python RCM_main.py --comprehensive-test

# Run specific test
python RCM_main.py --test-run T0000001

# Get monitoring data
python RCM_main.py --monitoring

# Show priority ports
python RCM_main.py --ports
```

#### API Endpoints
The FastAPI server provides the following endpoints:
- `GET /status` - Get service status
- `GET /metrics` - Get performance metrics
- `GET /health` - Health check
- `POST /activate` - Activate service
- `POST /deactivate` - Deactivate service
- `POST /test/{test_code}` - Run specific test

## Configuration

The system can be configured through:
- Environment variables
- Configuration files
- CCU remote commands via ECM
- API endpoints

## Error Handling

All errors are managed by the EMM module with:
- 16-character hexadecimal error codes
- Structured error messages
- Automatic recovery strategies
- Comprehensive logging

## Monitoring

The MSM module provides:
- Real-time performance metrics
- Resource utilization monitoring
- Token usage tracking
- System health reporting

## Contributing

When adding new functionality:
1. Create a new module following the naming convention
2. Implement the required interface methods
3. Add comprehensive tests to TMM
4. Update this README with module documentation
5. Ensure all code is thoroughly commented