# CCU (Central Control Unit) Microservice

A comprehensive Python-based Central Control Unit microservice that serves as the brain and central command center of the entire service architecture. The CCU orchestrates all dependent microservices and manages the complete lifecycle of incoming requests with enterprise-grade SSL/TLS certificate management.

## Overview

The CCU (Central Control Unit) is engineered as the primary orchestrator, bearing full responsibility for managing and tracking the entire lifecycle of incoming requests—from initial reception to final egress from the system. It controls all processing workflows, ensures complete functional integrity and stability of the service ecosystem, and provides centralized SSL/TLS certificate management for all microservices.

## Architecture

The CCU implements a highly modular architecture with **13 internal modules** and 6 interaction modules:

### Internal Modules

1. **RTM (Request Tracking Module)** - Core orchestration logic for request workflow management
2. **MSMM (MicroServices Monitoring Module)** - Health monitoring and fault tolerance
3. **SRMM (Server Resources Monitor Module)** - System resource monitoring and backpressure
4. **CEIM (Central Error Investigation Module)** - Centralized error handling and investigation
5. **CMM (Central Monitoring Module)** - Log aggregation and real-time streaming
6. **GMM (Graphical Monitoring Module)** - Web dashboard for system observability
7. **SMM (Setting Modification Module)** - Centralized configuration management
8. **DBM (Database Backup Module)** - Automated database backups
9. **IMSMM (Internal MicroService Manager Module)** - Self-monitoring and health checks
10. **CTMM (Central Test Management Module)** - Automated testing framework
11. **NMM (Network Monitoring Module)** - Network connectivity monitoring
12. **CERTM (Certificate Management Module)** - **NEW**: Enterprise SSL/TLS certificate management
13. **IMSMM (Internal MicroService Manager Module)** - Internal service management

### Interaction Modules

1. **RLAIM (RLA Interaction Module)** - Request Limit Analyzer interface with certificate distribution
2. **TPPIM (TPP Interaction Module)** - Text Preprocessing interface
3. **RCMIM (RCM Interaction Module)** - Request Cache Manager interface
4. **JFAIM (JFA Interaction Module)** - JSON File Analyzer interface
5. **TDIM (TD Interaction Module)** - Task Divider interface
6. **OCMIM (OCM Interaction Module)** - Output Cache Manager interface

## Key Features

### Core Responsibilities

- **Request Ingestion and Workflow Management**: Handles new and existing request IDs with stateful interactions
- **Microservice Orchestration**: Coordinates six specialized microservices in correct sequence
- **End-to-End Monitoring**: Tracks real-time status of every request through the pipeline
- **Health Monitoring**: Monitors microservice health with Circuit Breaker pattern
- **Resource Management**: Monitors system resources and applies backpressure when needed
- **Real-time Observability**: Provides live graphical dashboard similar to glances
- **Configuration Management**: Centralized configuration for all microservices
- **Database Backup**: Automated backup and disaster recovery
- **Dynamic Configuration**: Hot-reload configuration without service restart
- **🆕 SSL/TLS Certificate Management**: Enterprise-grade certificate distribution and management

### Advanced Features

- **Request ID Format**: `wsrid_0x<12-digit-hex>` with sequential structure
- **Backpressure Control**: Automatic request throttling at 90% CPU/memory usage
- **Circuit Breaker**: Prevents cascading failures across services
- **HMAC Security**: Optional message authentication for request integrity
- **Fault Tolerance**: Automated service recovery and restart capabilities
- **Performance Monitoring**: Real-time metrics and historical data
- **Error Investigation**: Automated error pattern detection and recovery
- **🆕 Certificate Hot-Reload**: Dynamic certificate updates without service restart
- **🆕 Environment-Specific Certificates**: Support for dev/staging/production environments
- **🆕 Certificate Expiry Monitoring**: Automated monitoring with 30/7-day warnings
- **🆕 Certificate Health Checks**: Comprehensive certificate validation and status tracking

### 🆕 SSL/TLS Certificate Management Features

The CERTM module provides enterprise-grade certificate management:

#### **Multi-Environment Support**
- **Development**: Localhost certificates for development
- **Staging**: Pre-production certificate testing
- **Production**: Production-ready certificates (Ubuntu 24, AWS, etc.)

#### **Dynamic Certificate Operations**
- **Hot-Reload**: Update certificates without service downtime
- **Environment Switching**: Seamless switching between certificate environments
- **Centralized Distribution**: Automatic certificate distribution to all microservices
- **Validation**: Real-time certificate validation and integrity checks

#### **Monitoring & Alerting**
- **Expiry Monitoring**: Daily certificate expiry checks with tiered alerts
- **Health Monitoring**: Continuous certificate health and validity monitoring
- **Alert Levels**: WARNING (30 days), CRITICAL (7 days), EXPIRED (immediate)
- **External Integration**: File-based alerts for external monitoring systems

#### **Security & Compliance**
- **Secure Storage**: Certificates stored securely with hash verification
- **Access Control**: Environment-specific certificate access control
- **Audit Trail**: Complete certificate operation logging and tracking
- **Backup & Recovery**: Automated certificate backup and rollback capabilities

## Directory Structure

```
CCU/
├── ccu.py                 # Main entry point
├── ccu_setting/          # Configuration files
│   ├── ccu_setting.json
│   ├── rla_setting.json
│   ├── tpp_setting.json
│   ├── rcm_setting.json
│   ├── jfa_setting.json
│   ├── td_setting.json
│   └── ocm_setting.json
├── 🆕 certificates/      # Certificate Management Structure
│   ├── dev/              # Development certificates (localhost)
│   │   ├── cert.pem
│   │   └── key.pem
│   ├── staging/          # Staging certificates
│   │   ├── cert.pem
│   │   └── key.pem
│   ├── prod/             # Production certificates (Ubuntu 24, etc.)
│   │   ├── cert.pem
│   │   └── key.pem
│   └── monitoring/       # Certificate monitoring alerts
├── RTM/                  # Request Tracking Module
│   └── rtm.py
├── MSMM/                 # MicroServices Monitoring Module
│   └── msmm.py
├── SRMM/                 # Server Resources Monitor Module
│   └── srmm.py
├── CEIM/                 # Central Error Investigation Module
│   └── ceim.py
├── CMM/                  # Central Monitoring Module
│   └── cmm.py
├── GMM/                  # Graphical Monitoring Module
│   └── gmm.py
├── SMM/                  # Setting Modification Module
│   └── smm.py
├── DBM/                  # Database Backup Module
│   └── dbm.py
├── IMSMM/                # Internal MicroService Manager Module
│   └── imsmm.py
├── CTMM/                 # Central Test Management Module
│   └── ctmm.py
├── NMM/                  # Network Monitoring Module
│   └── nmm.py
├── 🆕 CERTM/            # Certificate Management Module
│   └── certm.py
├── RLAIM/                # RLA Interaction Module (Enhanced with cert distribution)
│   └── rlaim.py
├── TPPIM/                # TPP Interaction Module
│   └── tppim.py
├── RCMIM/                # RCM Interaction Module
│   └── rcmim.py
├── JFAIM/                # JFA Interaction Module
│   └── jfaim.py
├── TDIM/                 # TD Interaction Module
│   └── tdim.py
├── OCMIM/                # OCM Interaction Module
│   └── ocmim.py
├── 🆕 test_certificate_system.py  # Certificate system testing
├── logs/                 # Log files
├── temp/                 # Temporary files
├── cache/                # Cache files
├── error/                # Error files
└── README.md             # This file
```

## Request Processing Pipeline

### Standard Workflow

1. **Request Reception** → RTM inspects request_id
2. **Workflow Routing** → New requests create new workflows, existing requests resume
3. **Service Orchestration** → Sequential processing through:
   - **RLA** (Request Limit Analyzer) - Gateway validation with HTTPS/SSL
   - **TPP** (Text Preprocessing) - Text filtering and cleaning
   - **RCM** (Request Cache Manager) - AI/ML processing
   - **JFA** (JSON File Analyzer) - Template analysis
   - **TD** (Task Divider) - Solar calculations (if required)
   - **OCM** (Output Cache Manager) - Output processing
4. **Response Delivery** → Final response returned to client

### Request ID Structure

```
Format: wsrid_0x<12-digit-hex-number>
Example: wsrid_0x000000000001

Security Note: This predictable structure is vulnerable to replay attacks.
Recommended: Implement HMAC with shared secret key for authentication.
```

## Installation and Setup

### Prerequisites

- Python 3.8+
- SQLite3
- SSL/TLS certificates (for production deployment)
- Required Python packages (install via pip)

### Installation Steps

1. **Clone or navigate to the CCU directory**
   ```bash
   cd services/ccu
   ```

2. **Install dependencies**
   ```bash
   pip install asyncio logging sqlite3 psutil websockets aiohttp requests
   pip install aiohttp-cors jinja2 aiofiles chart.js cryptography
   ```

3. **Create required directories**
   ```bash
   mkdir -p logs temp cache error
   mkdir -p certificates/{dev,staging,prod,monitoring}
   ```

4. **🆕 Set up SSL/TLS certificates**
   ```bash
   # For development (localhost certificates)
   cp your-dev-cert.pem certificates/dev/cert.pem
   cp your-dev-key.pem certificates/dev/key.pem
   
   # For production (Ubuntu 24, AWS, etc.)
   cp your-prod-cert.pem certificates/prod/cert.pem
   cp your-prod-key.pem certificates/prod/key.pem
   ```

5. **Configure services**
   - Edit `ccu_setting/ccu_setting.json` for main configuration
   - Update service-specific configurations in `ccu_setting/`
   - Configure certificate management settings

### Configuration

#### Main Configuration (`ccu_setting/ccu_setting.json`)

```json
{
    "service_name": "CCU",
    "core_settings": {
        "max_concurrent_requests": 10,
        "request_timeout": 300,
        "backpressure_threshold": {
            "cpu_usage": 90,
            "memory_usage": 90
        }
    },
    "🆕 certificate_management": {
        "enabled": true,
        "certificate_store_path": "certificates/",
        "active_environment": "development",
        "certificate_sources": {
            "development": {
                "cert_path": "certificates/dev/cert.pem",
                "key_path": "certificates/dev/key.pem",
                "description": "Development localhost certificates"
            },
            "production": {
                "cert_path": "certificates/prod/cert.pem",
                "key_path": "certificates/prod/key.pem",
                "description": "Production Ubuntu 24 certificates"
            }
        },
        "certificate_validation": {
            "verify_expiry": true,
            "expiry_warning_days": 30,
            "auto_renewal": false
        },
        "distribution_settings": {
            "services": ["RLA", "TPP", "RCM", "JFA", "TD", "OCM"],
            "push_on_change": true,
            "retry_attempts": 3
        }
    },
    "graphical_monitoring": {
        "enabled": true,
        "port": 11489,
        "host": "0.0.0.0"
    },
    "security": {
        "enable_hmac": true,
        "hmac_secret_key": "your-secret-key-here",
        "enable_ssl": true,
        "ssl_cert_path": "certificates/server.crt",
        "ssl_key_path": "certificates/server.key"
    }
}
```

#### Service Configurations

Each dependent service has its own configuration file with SSL support:

- `rla_setting.json` - Request Limit Analyzer settings with SSL configuration
- `tpp_setting.json` - Text Preprocessing settings
- `rcm_setting.json` - Request Cache Manager settings (includes API keys)
- `jfa_setting.json` - JSON File Analyzer settings
- `td_setting.json` - Task Divider settings
- `ocm_setting.json` - Output Cache Manager settings

#### 🆕 RLA SSL Configuration (`ccu_setting/rla_setting.json`)

```json
{
    "service_name": "RLA",
    "🆕 ssl_configuration": {
        "enabled": true,
        "certificate_source": "ccu_managed",
        "local_cert_path": "certs/cert.pem",
        "local_key_path": "certs/key.pem",
        "cert_content": "",
        "key_content": "",
        "auto_reload": true,
        "verification_mode": "optional",
        "supported_protocols": ["TLSv1.2", "TLSv1.3"]
    }
}
```

## Usage

### Starting the CCU Service

```bash
python ccu.py
```

### Command Line Options

```bash
python ccu.py --help                 # Show help
python ccu.py --config-file custom.json  # Use custom config
python ccu.py --port 8080            # Override default port
python ccu.py --debug                # Enable debug mode
python ccu.py --no-dashboard         # Disable web dashboard
```

### 🆕 Certificate Management Commands

#### Testing Certificate System
```bash
# Run comprehensive certificate tests
python test_certificate_system.py

# Run interactive certificate management
python test_certificate_system.py --interactive
```

#### Certificate Operations
```bash
# Switch certificate environment
curl -X POST http://localhost:8080/api/certificate/switch \
  -H "Content-Type: application/json" \
  -d '{"environment": "production"}'

# Check certificate status
curl http://localhost:8080/api/certificate/status

# Reload certificates
curl -X POST http://localhost:8080/api/certificate/reload

# Get certificate information
curl http://localhost:8080/api/certificate/info
```

### Web Dashboard

Access the real-time monitoring dashboard at:
```
http://localhost:11489
```

The dashboard now provides:
- Real-time system resource monitoring
- Service health status
- Request statistics and throughput
- Error logs and alerts
- Performance charts and trends
- **🆕 Certificate status and expiry monitoring**
- **🆕 SSL/TLS connection status for all services**

### API Endpoints

The CCU exposes several API endpoints for integration:

```bash
# Health check
GET /health

# Service status
GET /status

# Request processing
POST /process_request
{
    "request_id": "wsrid_0x000000000001",
    "data": "request_data"
}

# Get request status
GET /request_status/{request_id}

# Configuration management
POST /config/reload
PUT /config/update

# 🆕 Certificate Management APIs
GET /api/certificate/status           # Certificate status
GET /api/certificate/info            # Certificate information
POST /api/certificate/switch         # Switch environment
POST /api/certificate/reload         # Reload certificates
POST /api/certificate/validate       # Validate certificates
GET /api/certificate/health          # Certificate health check
```

## 🆕 Certificate Management Operations

### Environment Management

#### Development Environment
```bash
# Automatically uses localhost certificates
# Perfect for local development and testing
Active Environment: development
Certificate Path: certificates/dev/cert.pem
Certificate Key: certificates/dev/key.pem
```

#### Production Environment
```bash
# Switch to production certificates (Ubuntu 24, AWS, etc.)
curl -X POST http://localhost:8080/api/certificate/switch \
  -d '{"environment": "production"}'

# Verify switch was successful
curl http://localhost:8080/api/certificate/status
```

### Certificate Lifecycle

#### Adding New Certificates
```bash
# 1. Copy certificates to appropriate environment
cp new-cert.pem certificates/prod/cert.pem
cp new-key.pem certificates/prod/key.pem

# 2. Reload certificates
curl -X POST http://localhost:8080/api/certificate/reload

# 3. Verify certificates are loaded
curl http://localhost:8080/api/certificate/info
```

#### Certificate Monitoring
```bash
# Check certificate expiry status
curl http://localhost:8080/api/certificate/health

# Monitor certificate alerts
ls -la certificates/monitoring/cert_alert_*.json
```

#### Hot-Reload Certificates
```bash
# Certificates are automatically distributed to all services
# No service restart required!
curl -X POST http://localhost:8080/api/certificate/reload
```

### Certificate Security Features

#### Certificate Validation
- **Real-time validation**: Certificates validated on load and periodically
- **Expiry checking**: Automatic monitoring with multi-level alerts
- **Integrity verification**: Hash-based certificate change detection
- **Environment isolation**: Certificates isolated by environment

#### Certificate Distribution
- **Automatic Distribution**: Certificates automatically pushed to all microservices
- **Hot-Reload**: Services receive new certificates without restart
- **Fallback Handling**: Graceful fallback if certificate distribution fails
- **Retry Logic**: Automatic retry for failed certificate distributions

## Monitoring and Observability

### System Metrics

The CCU continuously monitors:
- CPU usage and load average
- Memory usage and available memory
- Disk usage and I/O operations
- Network connectivity and latency
- Active connections and throughput
- **🆕 Certificate status and expiry dates**
- **🆕 SSL/TLS connection health across all services**

### Service Health

Each dependent service is monitored for:
- Service availability and response time
- Error rates and failure patterns
- Resource usage and performance
- Circuit breaker status
- **🆕 SSL certificate status and validity**
- **🆕 Certificate expiry warnings and alerts**

### 🆕 Certificate Monitoring

The CERTM module provides comprehensive certificate monitoring:

#### **Certificate Health Checks**
- **Daily Expiry Checks**: Automated daily certificate expiry monitoring
- **Real-time Validation**: Continuous certificate validity checking
- **Environment Tracking**: Monitor certificates across all environments
- **Distribution Status**: Track certificate distribution to all services

#### **Alert Levels**
- **WARNING (30 days)**: ⚠️ Certificate expires within 30 days
- **CRITICAL (7 days)**: 🚨 Certificate expires within 7 days  
- **EXPIRED**: 🚨 Certificate has already expired

#### **Monitoring Outputs**
- **Log Alerts**: Certificate alerts in main CCU logs
- **Monitoring Files**: JSON alert files in `certificates/monitoring/`
- **Dashboard Integration**: Certificate status in web dashboard
- **API Status**: Certificate health via `/api/certificate/health`

### Error Management

The CEIM module provides:
- Centralized error collection and analysis
- Pattern detection and investigation
- Automated recovery strategies
- Error severity classification
- Real-time error reporting
- **🆕 Certificate-related error tracking and resolution**

### Performance Tracking

- Request processing times
- Service response times
- Throughput metrics
- Resource utilization trends
- Error rates and patterns
- **🆕 Certificate operations performance**
- **🆕 SSL/TLS handshake metrics**

## Security Considerations

### Request ID Security

The current sequential request ID format is vulnerable to replay attacks. Implement HMAC:

```python
import hmac
import hashlib

def generate_secure_request_id(payload, secret_key):
    signature = hmac.new(
        secret_key.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"wsrid_{signature[:12]}"
```

### 🆕 SSL/TLS Certificate Security

#### **Certificate Storage Security**
- **Secure File Permissions**: Certificate files protected with appropriate file permissions
- **Environment Isolation**: Certificates isolated by environment (dev/staging/prod)
- **Hash Verification**: Certificate integrity verified using SHA-256 hashes
- **Secure Transport**: Certificates distributed securely via encrypted WebSocket connections

#### **Certificate Access Control**
- **Environment-Based Access**: Services only receive certificates for their target environment
- **Authenticated Distribution**: Certificate distribution requires service authentication
- **Audit Logging**: All certificate operations logged for security auditing
- **Rollback Capability**: Ability to rollback to previous certificates if needed

#### **Certificate Validation**
- **Expiry Validation**: Automatic certificate expiry validation before distribution
- **Format Validation**: Certificate format and structure validation
- **Chain Validation**: Certificate chain validation for CA-signed certificates
- **Revocation Checking**: Support for certificate revocation list (CRL) checking

### Network Security

- Use HTTPS for all external communications
- Implement proper authentication and authorization
- Validate all input data
- Use secure configuration management
- Regular security audits and updates
- **🆕 Centralized SSL/TLS certificate management**
- **🆕 Automated certificate rotation and updates**

## Operational Procedures

### Daily Operations

1. **Monitor Dashboard**
   - Check system health at http://localhost:11489
   - Review error logs and alerts
   - Monitor resource usage trends
   - **🆕 Check certificate expiry status**
   - **🆕 Review SSL/TLS connection health**

2. **Check Service Status**
   ```bash
   curl http://localhost:8080/status
   curl http://localhost:8080/api/certificate/status  # 🆕 Certificate status
   ```

3. **Review Performance Metrics**
   - Request processing times
   - Service response times
   - Error rates
   - **🆕 Certificate operation performance**

### 🆕 Certificate Maintenance

#### **Daily Certificate Checks**
```bash
# Check certificate status across all environments
curl http://localhost:8080/api/certificate/health

# Review certificate expiry warnings
tail -f logs/ccu.log | grep -i certificate

# Check monitoring alerts
ls -la certificates/monitoring/cert_alert_*.json
```

#### **Certificate Updates**
```bash
# 1. Deploy new certificates to appropriate environment
cp new-cert.pem certificates/prod/cert.pem
cp new-key.pem certificates/prod/key.pem

# 2. Validate certificates before applying
curl -X POST http://localhost:8080/api/certificate/validate \
  -d '{"cert_path": "certificates/prod/cert.pem"}'

# 3. Apply new certificates (hot-reload)
curl -X POST http://localhost:8080/api/certificate/reload

# 4. Verify all services received new certificates
curl http://localhost:8080/api/certificate/status
```

#### **Environment Switching for Deployment**
```bash
# Switch to production environment for deployment
curl -X POST http://localhost:8080/api/certificate/switch \
  -H "Content-Type: application/json" \
  -d '{"environment": "production"}'

# Verify all services are using production certificates
curl http://localhost:8080/api/certificate/info
```

### Maintenance

1. **Configuration Updates**
   - Edit configuration files in `ccu_setting/`
   - Reload configuration: `curl -X POST http://localhost:8080/config/reload`
   - **🆕 Update certificate configurations via CERTM module**

2. **Database Maintenance**
   - Automatic backups run every 60 minutes
   - Manual backup: Access DBM module via API

3. **Log Management**
   - Logs automatically rotate at 100MB
   - Historical data retained for 30 days
   - Compression enabled for old logs
   - **🆕 Certificate operation logs tracked separately**

4. **🆕 Certificate Maintenance**
   - **Expiry Monitoring**: Automated daily certificate expiry checks
   - **Certificate Backup**: Certificates included in automated backup process
   - **Alert Management**: Certificate alerts archived in monitoring directory
   - **Environment Cleanup**: Old certificate files cleaned up automatically

### Troubleshooting

#### Common Issues

1. **Service Not Starting**
   - Check configuration files for syntax errors
   - Verify all dependencies are installed
   - Check port availability
   - **🆕 Verify certificate files exist and are readable**

2. **High Resource Usage**
   - Monitor resource metrics in dashboard
   - Check for memory leaks or high CPU usage
   - Review error logs for patterns

3. **Request Processing Failures**
   - Check dependent service health
   - Review error logs in CEIM
   - Verify network connectivity
   - **🆕 Check SSL/TLS certificate validity**

4. **Dashboard Not Accessible**
   - Check GMM configuration
   - Verify port 11489 is not blocked
   - Check firewall settings

5. **🆕 Certificate Issues**
   ```bash
   # Check certificate validity
   curl http://localhost:8080/api/certificate/validate
   
   # Check certificate expiry
   curl http://localhost:8080/api/certificate/health
   
   # Reload certificates if corrupted
   curl -X POST http://localhost:8080/api/certificate/reload
   
   # Switch to backup environment
   curl -X POST http://localhost:8080/api/certificate/switch \
     -d '{"environment": "development"}'
   ```

6. **🆕 SSL/TLS Connection Issues**
   ```bash
   # Check service SSL status
   curl https://localhost:3781/health  # RLA HTTPS health check
   
   # Verify certificate distribution
   curl http://localhost:8080/api/certificate/status
   
   # Test certificate system
   python test_certificate_system.py --interactive
   ```

#### 🆕 Certificate Debugging

```bash
# Enable certificate debug logging
export CERT_DEBUG=1
python ccu.py --debug

# Check certificate file permissions
ls -la certificates/*/

# Validate certificate manually
openssl x509 -in certificates/prod/cert.pem -text -noout

# Test certificate system comprehensively
python test_certificate_system.py
```

#### Debugging

Enable debug mode:
```bash
python ccu.py --debug
```

Check logs:
```bash
tail -f logs/ccu.log
tail -f logs/ccu.log | grep -i certificate  # 🆕 Certificate-specific logs
```

Monitor resource usage:
```bash
# Built-in resource monitoring
curl http://localhost:8080/metrics
curl http://localhost:8080/api/certificate/health  # 🆕 Certificate health
```

## Development

### Adding New Modules

1. Create module directory: `mkdir NEW_MODULE`
2. Implement module class with required methods:
   - `__init__(self)`
   - `async def start(self)`
   - `async def stop(self)`
   - `def get_status(self)`

3. Register module in `ccu.py`:
   ```python
   from NEW_MODULE.new_module import NewModule
   self.internal_modules['NEW_MODULE'] = NewModule()
   ```

### 🆕 Certificate-Aware Development

When developing new modules that require SSL/TLS:

1. **Register for Certificate Updates**:
   ```python
   # In your module initialization
   def setup_certificate_callbacks(self):
       async def cert_update_handler(cert_data):
           await self.update_ssl_certificates(cert_data)
       
       ccu.modules['CCM'].register_callback("on_cert_update", cert_update_handler)
   ```

2. **Implement Certificate Handling**:
   ```python
   async def update_ssl_certificates(self, cert_data):
       # Update SSL context with new certificates
       # Restart SSL connections if needed
       # Log certificate update success/failure
   ```

### Testing

The CTMM module provides comprehensive testing:
- Unit tests for individual modules
- Integration tests for workflows
- Performance tests for load handling
- Health check tests for monitoring
- **🆕 Certificate management tests**
- **🆕 SSL/TLS connection tests**

#### 🆕 Certificate Testing

```bash
# Test certificate system functionality
python test_certificate_system.py

# Interactive certificate testing
python test_certificate_system.py --interactive

# Test certificate in specific environment
python -c "
import asyncio
from CERTM.certm import CertificateManagementModule
config = {'certificate_management': {'active_environment': 'production'}}
certm = CertificateManagementModule(config)
asyncio.run(certm.start())
print(certm.get_status())
"
```

### Contributing

1. Follow the modular architecture pattern
2. Implement proper error handling
3. Add comprehensive logging
4. Include unit tests
5. Update documentation
6. **🆕 Ensure SSL/TLS compatibility for network-facing modules**
7. **🆕 Implement certificate update handlers where applicable**

## Performance Specifications

### Resource Requirements

- **Memory**: Base usage < 100MB, < 10MB per request
- **CPU**: Idle < 5%, processing < 50%, peak < 80%
- **Disk**: Logs < 1GB, cache < 500MB, temp < 200MB, **🆕 certificates < 50MB**
- **Network**: Support for 1000+ concurrent connections with SSL/TLS

### Scalability

- **Horizontal Scaling**: Load balancing with health checks
- **Vertical Scaling**: Configurable resource limits
- **Clustering**: Shared storage with coordination
- **Auto-scaling**: Based on resource utilization
- **🆕 Certificate Scaling**: Centralized certificate distribution to unlimited services

### Performance Targets

- **Request Processing**: < 5 seconds average
- **Service Response**: < 2 seconds for health checks
- **Dashboard Update**: 5-second refresh rate
- **Error Detection**: < 30 seconds for critical errors
- **🆕 Certificate Distribution**: < 10 seconds to all services
- **🆕 Certificate Validation**: < 2 seconds per certificate
- **🆕 SSL Handshake**: < 1 second average

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For technical support and questions:
- Check the troubleshooting section
- Review error logs in the dashboard
- Monitor service health metrics
- **🆕 Check certificate status via API**
- **🆕 Review certificate monitoring alerts**
- Contact the development team

## Changelog

### Version 1.1.0 (Certificate Management Update)
- **🆕 Added CERTM (Certificate Management Module)**
- **🆕 Enterprise SSL/TLS certificate management**
- **🆕 Multi-environment certificate support (dev/staging/prod)**
- **🆕 Certificate hot-reload without service restart**
- **🆕 Automated certificate expiry monitoring and alerting**
- **🆕 Certificate distribution to all microservices**
- **🆕 Certificate health checks and validation**
- **🆕 Interactive certificate testing suite**
- **🆕 Enhanced RLA with dynamic SSL certificate support**
- **🆕 Certificate-related troubleshooting and debugging tools**
- **🆕 Comprehensive certificate API endpoints**
- **🆕 Certificate security and access control**

### Version 1.0.0 (Initial Release)
- Core CCU orchestration engine
- 12 internal modules implemented
- 6 interaction modules for service integration
- Real-time web dashboard
- Comprehensive monitoring and alerting
- Automated backup and recovery
- Security enhancements with HMAC support
- Complete documentation and setup guides 