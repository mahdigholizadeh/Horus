# OCM (Output Cache Management) Microservice

## Overview

The OCM (Output Cache Management) microservice is the terminal component in the Horus computation pipeline, responsible for processing final generated output and serving as the secure delivery gateway to client-facing web servers. OCM ensures reliable, prioritized, and validated delivery of computation results through HTTPS with comprehensive quality assurance.

## Architecture

OCM follows a modular microservice architecture with 15 specialized modules, each handling specific aspects of output processing and delivery:

### Core Service Components

- **Main Entry Point** (`ocm.py`): Service orchestration and module management
- **CCU Integration**: Seamless integration with Central Control Unit for centralized management

### Communication & Networking

- **ECM (External Control Module)**: WebSocket communication with CCU
- **NMM (Network Management Module)**: HTTPS communication and SSL/TLS management
- **DSM (Data Sender Module)**: Final output transmission and delivery confirmation

### Data Processing & Management

- **RMM (Request Management Module)**: Request lifecycle orchestration with priority queues
- **TDIM (TD Interaction Module)**: Incoming data processing from TD microservice
- **RCMIM (RCM Interaction Module)**: Direct API response handling from RCM
- **DCM (Database Control Module)**: Priority-partitioned database operations

### Report Generation

- **HRPM (HTML Report Producer Module)**: HTML templating and report generation
- **PRFPM (PDF Report Format Producer Module)**: HTML to PDF conversion
- **OCVM (Output Check Validity Module)**: Quality assurance and validation

### System Management

- **BTM (Background Task Module)**: Asynchronous task processing
- **FAIM (FastAPI Integration Module)**: RESTful API endpoints
- **MSM (Monitoring System Module)**: Metrics collection and health monitoring
- **EMM (Error Management Module)**: Centralized error handling and escalation
- **TMM (Test Management Module)**: Comprehensive testing framework

## Key Features

### 🔐 Security & SSL Management
- **CCU-managed SSL certificates** with automatic hot-reload
- **Custom acknowledgment protocol** with checksum validation
- **Security vulnerability scanning** in generated content
- **Secure HTTPS communication** with configurable encryption

### 📊 Priority-Based Processing
- **Four-tier priority system** (A, B, C, D) with bandwidth allocation
- **Priority-partitioned databases** for optimal performance
- **Queue management** with intelligent load balancing
- **Guaranteed delivery** with retry logic and acknowledgment

### 📄 Report Generation Pipeline
- **Dynamic HTML templating** with Jinja2 integration
- **Multi-format PDF generation** (WeasyPrint, ReportLab, Chromium)
- **Quality assurance validation** before delivery
- **Custom template support** with metadata extraction

### 📈 Monitoring & Analytics
- **Real-time metrics collection** with Prometheus-style monitoring
- **Health checks** for all modules and dependencies
- **Performance analytics** with latency and throughput tracking
- **Comprehensive logging** with structured JSON format

### 🧪 Testing Framework
- **Unit, integration, and E2E tests** with parallel execution
- **Built-in module health tests** for continuous monitoring
- **Test reporting** with HTML and JSON output formats
- **Coverage analysis** and performance benchmarking

## Installation & Setup

### Prerequisites

- Python 3.8+
- Required Python packages (install via `pip install -r requirements.txt`):
  - `fastapi>=0.68.0`
  - `uvicorn>=0.15.0`
  - `websockets>=10.0`
  - `jinja2>=3.0.0`
  - `psutil>=5.8.0`
  - `aiohttp>=3.8.0`

### Optional Dependencies

For enhanced PDF generation:
```bash
pip install weasyprint reportlab
```

For improved testing:
```bash
pip install pytest pytest-asyncio coverage
```

### Directory Structure

```
OCM/
├── OCM_MAIN/
│   └── ocm/
│       └── ocm/
│           ├── ocm.py                 # Main service entry point
│           ├── config/
│           │   └── ocm_config.json   # Configuration file
│           ├── BTM/
│           │   └── btm.py            # Background Task Module
│           ├── ECM/
│           │   └── ecm.py            # External Control Module
│           ├── RMM/
│           │   └── rmm.py            # Request Management Module
│           ├── NMM/
│           │   └── nmm.py            # Network Management Module
│           ├── DSM/
│           │   └── dsm.py            # Data Sender Module
│           ├── TDIM/
│           │   └── tdim.py           # TD Interaction Module
│           ├── RCMIM/
│           │   └── rcmim.py          # RCM Interaction Module
│           ├── DCM/
│           │   └── dcm.py            # Database Control Module
│           ├── HRPM/
│           │   └── hrpm.py           # HTML Report Producer Module
│           ├── PRFPM/
│           │   └── prfpm.py          # PDF Report Format Producer Module
│           ├── OCVM/
│           │   └── ocvm.py           # Output Check Validity Module
│           ├── FAIM/
│           │   └── faim.py           # FastAPI Integration Module
│           ├── MSM/
│           │   └── msm.py            # Monitoring System Module
│           ├── EMM/
│           │   └── emm.py            # Error Management Module
│           └── TMM/
│               └── tmm.py            # Test Management Module
├── OCM_CONFIGURATION_PLAN.md         # Detailed configuration guide
└── README.md                         # This file
```

## Configuration

OCM uses a comprehensive JSON configuration file located at `config/ocm_config.json`. Key configuration sections include:

### Network Configuration
```json
{
  "network": {
    "output_port": 47812,
    "protocol": "HTTPS",
    "host": "0.0.0.0",
    "max_connections": 500,
    "connection_timeout": 30
  }
}
```

### SSL Configuration
```json
{
  "ssl_configuration": {
    "enabled": true,
    "certificate_source": "ccu_managed",
    "auto_reload": true,
    "verification_mode": "required"
  }
}
```

### Priority Management
```json
{
  "priority_management": {
    "enabled": true,
    "levels": ["A", "B", "C", "D"],
    "bandwidth_allocation": {
      "A": 40,
      "B": 30,
      "C": 20,
      "D": 10
    }
  }
}
```

### Report Generation
```json
{
  "report_generation": {
    "default_template": "templates/default_template.html",
    "output_formats": ["HTML", "PDF"],
    "pdf_settings": {
      "page_size": "A4",
      "orientation": "portrait"
    }
  }
}
```

For complete configuration options, see `OCM_CONFIGURATION_PLAN.md`.

## Usage

### Starting the Service

```bash
cd services/ocm
python ocm.py
```

### API Endpoints

OCM provides a comprehensive REST API through the FAIM module:

#### Health & Status
- `GET /health` - Service health check
- `GET /status` - Detailed service status
- `GET /metrics` - Prometheus-style metrics

#### Task Management
- `POST /tasks` - Create background task
- `GET /tasks/{task_id}` - Get task information
- `DELETE /tasks/{task_id}` - Cancel task

#### Report Management
- `POST /reports/status` - Get report status
- `GET /reports/queue` - Queue status

#### Module Management
- `GET /modules` - All module status
- `GET /modules/{module_name}` - Specific module status

#### SSL Certificate Management
- `GET /ssl/status` - SSL certificate status

### Python API Usage

```python
import asyncio
from ocm import OCMService

async def main():
    # Initialize OCM service
    ocm = OCMService("config/ocm_config.json")
    
    # Start service
    await ocm.start()
    
    # Service will run until interrupted
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await ocm.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

## Module Integration

### CCU Communication (ECM)

```python
# ECM handles WebSocket communication with CCU
ecm = ExternalControlModule(config)
await ecm.start()

# Send heartbeat to CCU
await ecm.send_heartbeat({
    'service': 'OCM',
    'timestamp': datetime.now().isoformat(),
    'status': 'running'
})
```

### Report Generation (HRPM + PRFPM)

```python
# Generate HTML report
hrpm = HTMLReportProducerModule(config)
report_id = await hrpm.generate_report(
    template_id='default',
    data={
        'title': 'Pipeline Report',
        'content': computation_results
    }
)

# Convert to PDF
prfpm = PDFReportFormatProducerModule(config)
pdf_id = await prfpm.generate_pdf_from_report_id(report_id, hrpm)
```

### Quality Validation (OCVM)

```python
# Validate output before delivery
ocvm = OutputCheckValidityModule(config)
validation_report_id = await ocvm.validate_content(
    content=html_report,
    content_type="text/html",
    content_id=report_id
)

# Check if content passed validation
is_valid = await ocvm.is_content_valid(validation_report_id)
```

## Testing

### Running Tests

```bash
# Run all tests
python -c "
import asyncio
from TMM.tmm import TestManagementModule

async def run_tests():
    tmm = TestManagementModule(config)
    await tmm.start()
    session_id = await tmm.run_test_suite()
    print(f'Test session: {session_id}')

asyncio.run(run_tests())
"
```

### Test Types

- **Unit Tests**: Individual module functionality
- **Integration Tests**: Inter-module communication
- **End-to-End Tests**: Complete request lifecycle
- **Performance Tests**: Load and stress testing
- **Security Tests**: Vulnerability scanning

### Built-in Health Tests

OCM includes comprehensive built-in tests:
- Module health checks
- Service integration tests
- CCU communication tests
- Database connectivity tests
- SSL certificate validation

## Monitoring

### Metrics Collection

OCM provides extensive monitoring through MSM:

- **System Metrics**: CPU, memory, disk usage
- **Service Metrics**: Request counts, processing times
- **Module Metrics**: Health status, error rates
- **Performance Metrics**: Latency percentiles, throughput

### Health Monitoring

- **Real-time health checks** for all modules
- **Automated alerting** for critical issues
- **Performance trend analysis**
- **Capacity planning metrics**

### Log Analysis

- **Structured JSON logging** for easy parsing
- **Configurable log levels** per module
- **Log rotation** and archival
- **Error correlation** and analysis

## Security

### SSL/TLS Management

- **CCU-managed certificates** with automatic renewal
- **Hot-reload** capability without service interruption
- **Certificate validation** and expiry monitoring
- **Multiple SSL context support**

### Content Security

- **XSS protection** in generated reports
- **Content sanitization** and validation
- **Input validation** and parameter checking
- **Secure file handling** and storage

### Network Security

- **HTTPS-only communication**
- **Request rate limiting**
- **IP-based access control** (configurable)
- **Secure header implementation**

## Performance Optimization

### Request Processing

- **Priority-based queue management** with A/B/C/D levels
- **Parallel processing** with configurable concurrency
- **Request batching** for improved throughput
- **Intelligent load balancing**

### Database Optimization

- **Priority-partitioned databases** for faster access
- **Connection pooling** and management
- **Query optimization** and indexing
- **Automated backup** and maintenance

### Caching Strategy

- **Multi-level caching** for templates and reports
- **Cache invalidation** and refresh policies
- **Memory-efficient storage** for large files
- **Distributed caching** support

## Troubleshooting

### Common Issues

1. **SSL Certificate Problems**
   - Check CCU connection and certificate delivery
   - Verify certificate paths and permissions
   - Review SSL configuration settings

2. **Database Connection Issues**
   - Verify database file permissions
   - Check disk space availability
   - Review database configuration

3. **Template/PDF Generation Errors**
   - Ensure required dependencies are installed
   - Check template syntax and paths
   - Verify PDF engine availability

4. **Performance Issues**
   - Monitor system resources (CPU, memory)
   - Review priority queue configurations
   - Check network connectivity and latency

### Debugging

Enable debug logging:
```json
{
  "logging": {
    "level": "DEBUG",
    "format": "detailed"
  }
}
```

Use the TMM testing framework:
```python
# Run diagnostic tests
session_id = await tmm.run_test_suite(
    test_types=[TestType.INTEGRATION],
    tags=['health', 'connectivity']
)
```

## Development

### Adding Custom Modules

1. Create module file following the pattern:
```python
class CustomModule:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.is_active = False
    
    async def start(self):
        self.is_active = True
    
    async def stop(self):
        self.is_active = False
    
    async def health_check(self) -> bool:
        return self.is_active
```

2. Register in main OCM service:
```python
self.modules['CUSTOM'] = CustomModule(self.config)
```

### Custom Validators (OCVM)

```python
async def custom_validator(content, content_type, content_id):
    issues = []
    # Add validation logic
    return issues

ocvm.register_custom_validator('my_validator', custom_validator)
```

### Custom Templates (HRPM)

Create HTML templates with metadata:
```html
<!-- TEMPLATE_METADATA
id: custom_template
name: Custom Report Template
type: analysis
description: Custom analysis report template
version: 1.0.0
parameters: ["title", "data", "timestamp"]
-->
<html>
  <head><title>{{ title }}</title></head>
  <body>{{ data | safe }}</body>
</html>
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement changes with tests
4. Run the test suite
5. Submit a pull request

### Code Standards

- Follow PEP 8 style guidelines
- Include comprehensive docstrings
- Add unit tests for new functionality
- Update documentation as needed

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Review the `OCM_CONFIGURATION_PLAN.md` for detailed configuration
- Check the built-in test results for system health
- Use the monitoring endpoints for real-time diagnostics
- Review logs in the `logs/` directory

## Version History

- **v1.0.0**: Initial release with complete module implementation
  - 15 specialized modules
  - CCU integration
  - Comprehensive testing framework
  - Full API coverage
  - Security and monitoring features 