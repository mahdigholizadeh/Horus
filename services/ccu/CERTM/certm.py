"""
Certificate Management Module (CERTM) for CCU

This module handles centralized SSL/TLS certificate management:
- Loads certificates from different environments
- Distributes certificates to all microservices
- Monitors certificate expiry
- Supports hot-reload of certificates
- Manages certificate validation and security
"""

import asyncio
import logging
import json
import ssl
import os
import base64
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.hazmat.backends import default_backend
import hashlib


class CertificateInfo:
    """Certificate information container."""
    def __init__(self, cert_path: str, key_path: str):
        self.cert_path = cert_path
        self.key_path = key_path
        self.cert_content = ""
        self.key_content = ""
        self.cert_hash = ""
        self.key_hash = ""
        self.expires_at = None
        self.subject = ""
        self.issuer = ""
        self.loaded_at = None
        self.is_valid = False


class CertificateManagementModule:
    """
    Certificate Management Module (CERTM)
    
    Manages SSL/TLS certificates for all microservices:
    - Environment-based certificate selection
    - Dynamic certificate distribution
    - Certificate expiry monitoring
    - Hot-reload capability
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the CERTM module."""
        self.logger = logging.getLogger(__name__)
        self.module_name = "CERTM"
        self.is_active = False
        
        # Configuration
        self.config = config.get('certificate_management', {})
        self.certificate_store_path = Path(self.config.get('certificate_store_path', 'certificates/'))
        self.active_environment = self.config.get('active_environment', 'development')
        
        # Certificate storage
        self.certificates = {}
        self.certificate_info = {}
        
        # Services to distribute to
        self.target_services = self.config.get('distribution_settings', {}).get('services', [])
        
        # Statistics
        self.stats = {
            'certificates_loaded': 0,
            'distributions_sent': 0,
            'distribution_failures': 0,
            'last_distribution': None,
            'expiry_warnings': 0
        }
        
        # Create certificate directory structure
        self._create_certificate_directories()
        
        self.logger.info(f"{self.module_name} initialized for environment: {self.active_environment}")
    
    def _create_certificate_directories(self):
        """Create certificate directory structure."""
        try:
            self.certificate_store_path.mkdir(parents=True, exist_ok=True)
            
            # Create environment subdirectories
            for env in ['dev', 'staging', 'prod']:
                env_path = self.certificate_store_path / env
                env_path.mkdir(exist_ok=True)
            
            self.logger.info("Certificate directories created")
            
        except Exception as e:
            self.logger.error(f"Failed to create certificate directories: {e}")
    
    async def start(self):
        """Start the CERTM module."""
        try:
            self.is_active = True
            
            # Load certificates for active environment
            await self.load_certificates()
            
            # Start certificate monitoring
            asyncio.create_task(self._monitor_certificate_expiry())
            
            self.logger.info(f"{self.module_name} started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start {self.module_name}: {e}")
            raise
    
    async def stop(self):
        """Stop the CERTM module."""
        try:
            self.is_active = False
            self.logger.info(f"{self.module_name} stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to stop {self.module_name}: {e}")
            raise
    
    async def load_certificates(self, environment: str = None) -> bool:
        """Load certificates for specified environment."""
        try:
            env = environment or self.active_environment
            env_config = self.config.get('certificate_sources', {}).get(env, {})
            
            if not env_config:
                self.logger.warning(f"No certificate configuration found for environment: {env}")
                return False
            
            cert_path = Path(env_config.get('cert_path', ''))
            key_path = Path(env_config.get('key_path', ''))
            
            # Check if certificate files exist
            if not cert_path.exists():
                self.logger.error(f"Certificate file not found: {cert_path}")
                return False
            
            if not key_path.exists():
                self.logger.error(f"Private key file not found: {key_path}")
                return False
            
            # Load certificate and key content
            cert_info = CertificateInfo(str(cert_path), str(key_path))
            
            # Read certificate content
            with open(cert_path, 'r') as f:
                cert_info.cert_content = f.read()
            
            # Read key content
            with open(key_path, 'r') as f:
                cert_info.key_content = f.read()
            
            # Calculate hashes for change detection
            cert_info.cert_hash = hashlib.sha256(cert_info.cert_content.encode()).hexdigest()
            cert_info.key_hash = hashlib.sha256(cert_info.key_content.encode()).hexdigest()
            
            # Parse certificate for metadata
            await self._parse_certificate_metadata(cert_info)
            
            # Store certificate info
            self.certificates[env] = cert_info
            self.certificate_info[env] = {
                'cert_path': str(cert_path),
                'key_path': str(key_path),
                'cert_hash': cert_info.cert_hash,
                'key_hash': cert_info.key_hash,
                'expires_at': cert_info.expires_at.isoformat() if cert_info.expires_at else None,
                'subject': cert_info.subject,
                'issuer': cert_info.issuer,
                'loaded_at': datetime.now().isoformat(),
                'is_valid': cert_info.is_valid
            }
            
            self.stats['certificates_loaded'] += 1
            self.logger.info(f"Certificates loaded successfully for environment: {env}")
            
            # Auto-distribute if enabled
            if self.config.get('auto_distribute', True):
                await self.distribute_certificates()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load certificates: {e}")
            return False
    
    async def _parse_certificate_metadata(self, cert_info: CertificateInfo):
        """Parse certificate to extract metadata."""
        try:
            # Parse the certificate
            cert_bytes = cert_info.cert_content.encode()
            certificate = x509.load_pem_x509_certificate(cert_bytes, default_backend())
            
            # Extract information
            cert_info.expires_at = certificate.not_valid_after
            cert_info.subject = certificate.subject.rfc4514_string()
            cert_info.issuer = certificate.issuer.rfc4514_string()
            cert_info.loaded_at = datetime.now()
            
            # Check if certificate is valid
            now = datetime.now()
            cert_info.is_valid = (
                certificate.not_valid_before <= now <= certificate.not_valid_after
            )
            
            self.logger.debug(f"Certificate metadata parsed: expires {cert_info.expires_at}")
            
        except Exception as e:
            self.logger.error(f"Failed to parse certificate metadata: {e}")
            cert_info.is_valid = False
    
    async def distribute_certificates(self, target_services: List[str] = None) -> Dict[str, bool]:
        """Distribute certificates to target services."""
        try:
            services = target_services or self.target_services
            results = {}
            
            # Get active certificate
            active_cert = self.certificates.get(self.active_environment)
            if not active_cert:
                self.logger.error(f"No certificate loaded for active environment: {self.active_environment}")
                return {}
            
            # Prepare certificate data for distribution
            cert_data = {
                'environment': self.active_environment,
                'cert_content': active_cert.cert_content,
                'key_content': active_cert.key_content,
                'cert_hash': active_cert.cert_hash,
                'key_hash': active_cert.key_hash,
                'expires_at': active_cert.expires_at.isoformat() if active_cert.expires_at else None,
                'distributed_at': datetime.now().isoformat()
            }
            
            # Distribute to each service
            for service_name in services:
                try:
                    result = await self._send_certificate_to_service(service_name, cert_data)
                    results[service_name] = result
                    
                    if result:
                        self.stats['distributions_sent'] += 1
                    else:
                        self.stats['distribution_failures'] += 1
                        
                except Exception as e:
                    self.logger.error(f"Failed to distribute certificate to {service_name}: {e}")
                    results[service_name] = False
                    self.stats['distribution_failures'] += 1
            
            self.stats['last_distribution'] = datetime.now()
            
            success_count = sum(1 for success in results.values() if success)
            self.logger.info(f"Certificate distribution completed: {success_count}/{len(services)} services updated")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to distribute certificates: {e}")
            return {}
    
    async def _send_certificate_to_service(self, service_name: str, cert_data: Dict[str, Any]) -> bool:
        """Send certificate data to a specific service."""
        try:
            # This would integrate with the existing service interaction modules
            # For example, sending via WebSocket through RLAIM, RCMIM, etc.
            
            # Prepare the configuration update message
            config_update = {
                'type': 'certificate_update',
                'service': service_name,
                'timestamp': datetime.now().isoformat(),
                'certificate_data': {
                    'ssl_configuration': {
                        'enabled': True,
                        'certificate_source': 'ccu_managed',
                        'cert_content': cert_data['cert_content'],
                        'key_content': cert_data['key_content'],
                        'cert_hash': cert_data['cert_hash'],
                        'key_hash': cert_data['key_hash'],
                        'expires_at': cert_data['expires_at'],
                        'distributed_at': cert_data['distributed_at']
                    }
                }
            }
            
            # This is where you would integrate with existing interaction modules
            # For now, we'll simulate the distribution
            self.logger.info(f"Certificate data prepared for {service_name}")
            
            # In a real implementation, you would use:
            # - RLAIM for RLA service
            # - RCMIM for RCM service
            # - etc.
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send certificate to {service_name}: {e}")
            return False
    
    async def switch_environment(self, new_environment: str) -> bool:
        """Switch to a different certificate environment."""
        try:
            if new_environment == self.active_environment:
                self.logger.info(f"Already using environment: {new_environment}")
                return True
            
            # Load certificates for new environment
            success = await self.load_certificates(new_environment)
            if success:
                self.active_environment = new_environment
                self.logger.info(f"Switched to certificate environment: {new_environment}")
                return True
            else:
                self.logger.error(f"Failed to switch to environment: {new_environment}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error switching certificate environment: {e}")
            return False
    
    async def reload_certificates(self) -> bool:
        """Reload certificates from disk."""
        try:
            return await self.load_certificates()
        except Exception as e:
            self.logger.error(f"Failed to reload certificates: {e}")
            return False
    
    async def _monitor_certificate_expiry(self):
        """Monitor certificate expiry and send warnings."""
        while self.is_active:
            try:
                warning_days = self.config.get('certificate_validation', {}).get('expiry_warning_days', 30)
                critical_days = 7  # Critical warning at 7 days
                
                for env, cert_info in self.certificates.items():
                    if cert_info.expires_at:
                        days_until_expiry = (cert_info.expires_at - datetime.now()).days
                        
                        # Send different levels of alerts based on time remaining
                        if days_until_expiry <= 0:
                            await self._send_expiry_alert(env, cert_info, "EXPIRED", days_until_expiry)
                        elif days_until_expiry <= critical_days:
                            await self._send_expiry_alert(env, cert_info, "CRITICAL", days_until_expiry)
                        elif days_until_expiry <= warning_days:
                            await self._send_expiry_alert(env, cert_info, "WARNING", days_until_expiry)
                
                # Check every 24 hours
                await asyncio.sleep(86400)
                
            except Exception as e:
                self.logger.error(f"Error monitoring certificate expiry: {e}")
                await asyncio.sleep(3600)  # Retry in 1 hour
    
    async def _send_expiry_alert(self, environment: str, cert_info: CertificateInfo, severity: str, days_remaining: int):
        """Send certificate expiry alert."""
        try:
            alert_message = {
                'alert_type': 'certificate_expiry',
                'severity': severity,
                'environment': environment,
                'days_remaining': days_remaining,
                'expires_at': cert_info.expires_at.isoformat() if cert_info.expires_at else None,
                'subject': cert_info.subject,
                'certificate_path': cert_info.cert_path,
                'timestamp': datetime.now().isoformat()
            }
            
            # Log the alert
            if severity == "EXPIRED":
                self.logger.critical(f"🚨 CERTIFICATE EXPIRED! Environment: {environment}, Expired: {abs(days_remaining)} days ago")
            elif severity == "CRITICAL":
                self.logger.critical(f"🚨 CERTIFICATE CRITICAL! Environment: {environment}, Expires in: {days_remaining} days")
            elif severity == "WARNING":
                self.logger.warning(f"⚠️ CERTIFICATE WARNING! Environment: {environment}, Expires in: {days_remaining} days")
            
            self.stats['expiry_warnings'] += 1
            
            # Here you could integrate with external alerting systems
            # For example: Slack, email, SMS, monitoring dashboards
            await self._send_alert_to_external_systems(alert_message)
            
        except Exception as e:
            self.logger.error(f"Failed to send expiry alert: {e}")
    
    async def _send_alert_to_external_systems(self, alert_message: Dict[str, Any]):
        """Send alerts to external monitoring systems."""
        try:
            # This is where you would integrate with external systems
            # Examples:
            
            # 1. Send to webhook (Slack, Teams, Discord)
            # await self._send_webhook_alert(alert_message)
            
            # 2. Send email alert
            # await self._send_email_alert(alert_message)
            
            # 3. Write to monitoring file for external pickup
            await self._write_monitoring_file(alert_message)
            
        except Exception as e:
            self.logger.error(f"Failed to send alert to external systems: {e}")
    
    async def _write_monitoring_file(self, alert_message: Dict[str, Any]):
        """Write alert to monitoring file for external systems to pickup."""
        try:
            monitoring_dir = Path("certificates/monitoring")
            monitoring_dir.mkdir(exist_ok=True)
            
            alert_file = monitoring_dir / f"cert_alert_{int(datetime.now().timestamp())}.json"
            
            with open(alert_file, 'w') as f:
                json.dump(alert_message, f, indent=2)
            
            self.logger.info(f"Alert written to monitoring file: {alert_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to write monitoring file: {e}")
    
    def get_certificate_info(self, environment: str = None) -> Dict[str, Any]:
        """Get certificate information for an environment."""
        env = environment or self.active_environment
        return self.certificate_info.get(env, {})
    
    def get_all_certificate_info(self) -> Dict[str, Any]:
        """Get information about all loaded certificates."""
        return {
            'active_environment': self.active_environment,
            'certificates': self.certificate_info,
            'statistics': self.stats,
            'last_check': datetime.now().isoformat()
        }
    
    async def validate_certificate_file(self, cert_path: str) -> Dict[str, Any]:
        """Validate a certificate file."""
        try:
            cert_path = Path(cert_path)
            
            if not cert_path.exists():
                return {'valid': False, 'error': 'Certificate file not found'}
            
            with open(cert_path, 'r') as f:
                cert_content = f.read()
            
            # Parse certificate
            cert_bytes = cert_content.encode()
            certificate = x509.load_pem_x509_certificate(cert_bytes, default_backend())
            
            # Extract information
            now = datetime.now()
            is_valid = certificate.not_valid_before <= now <= certificate.not_valid_after
            days_until_expiry = (certificate.not_valid_after - now).days
            
            return {
                'valid': True,
                'is_current': is_valid,
                'not_before': certificate.not_valid_before.isoformat(),
                'not_after': certificate.not_valid_after.isoformat(),
                'days_until_expiry': days_until_expiry,
                'subject': certificate.subject.rfc4514_string(),
                'issuer': certificate.issuer.rfc4514_string()
            }
            
        except Exception as e:
            return {'valid': False, 'error': str(e)}
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the CERTM module."""
        return {
            'module': self.module_name,
            'is_active': self.is_active,
            'active_environment': self.active_environment,
            'certificates_loaded': len(self.certificates),
            'target_services': self.target_services,
            'statistics': self.stats,
            'certificate_info': self.certificate_info
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            # Check if active certificate is valid
            active_cert_valid = False
            expiry_status = "unknown"
            
            active_cert = self.certificates.get(self.active_environment)
            if active_cert and active_cert.expires_at:
                days_until_expiry = (active_cert.expires_at - datetime.now()).days
                active_cert_valid = active_cert.is_valid and days_until_expiry > 0
                expiry_status = f"{days_until_expiry} days"
            
            return {
                'healthy': self.is_active and active_cert_valid,
                'module': self.module_name,
                'timestamp': datetime.now().isoformat(),
                'active_environment': self.active_environment,
                'certificate_valid': active_cert_valid,
                'certificate_expiry': expiry_status,
                'statistics': self.stats
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'module': self.module_name,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            } 