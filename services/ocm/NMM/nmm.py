"""
Network Management Module (NMM) for OCM

This module handles all network communications for the OCM microservice:
- HTTPS communication with external web servers
- SSL/TLS certificate management and hot-reload
- Connection pooling and management  
- Custom acknowledgment protocol implementation
- Health monitoring of network connections
- Port configuration and management
"""

import asyncio
import logging
import ssl
import aiohttp
import json
import tempfile
import os
import hashlib
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import time
import struct

class NetworkManagementModule:
    """Network Management Module for handling HTTPS communications and SSL management."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the NMM module."""
        self.logger = logging.getLogger(__name__)
        self.module_name = "NMM"
        self.config = config
        self.is_active = False
        
        # Network configuration
        self.network_config = config.get('network', {})
        self.web_server_host = self.network_config.get('web_server_host', 'localhost')
        self.web_server_port = self.network_config.get('web_server_port', 443)
        self.web_server_endpoint = self.network_config.get('web_server_endpoint', '/api/data')
        
        # SSL configuration - following RLA pattern
        self.ssl_config = {
            'enabled': self.network_config.get('ssl_enabled', True),
            'certificate_source': 'ccu_managed',
            'cert_content': '',
            'key_content': '',
            'cert_hash': '',
            'key_hash': '',
            'expires_at': None,
            'distributed_at': None,
            'temp_cert_file': None,
            'temp_key_file': None,
            'last_update': None
        }
        
        # Connection pooling
        self.connection_pool = None
        self.session = None
        self.ssl_context = None
        
        # Custom acknowledgment protocol
        self.ack_protocol = {
            'enabled': config.get('acknowledgment_protocol', {}).get('enabled', True),
            'timeout': config.get('acknowledgment_protocol', {}).get('timeout', 30),
            'retry_attempts': config.get('acknowledgment_protocol', {}).get('retry_attempts', 3),
            'checksum_validation': config.get('acknowledgment_protocol', {}).get('checksum_validation', True)
        }
        
        # Connection health monitoring
        self.health_monitoring = {
            'enabled': True,
            'check_interval': 60,
            'timeout': 10,
            'failure_threshold': 3,
            'consecutive_failures': 0,
            'last_health_check': None,
            'is_healthy': True
        }
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'ssl_handshake_errors': 0,
            'connection_timeouts': 0,
            'acknowledgment_failures': 0,
            'certificate_updates': 0,
            'ssl_context_recreations': 0,
            'bytes_sent': 0,
            'bytes_received': 0,
            'average_response_time': 0,
            'last_activity': None
        }
        
        # Background tasks
        self.background_tasks = set()
        
        self.logger.info(f"{self.module_name} initialized")
    
    async def start(self):
        """Start the NMM module."""
        try:
            self.is_active = True
            
            # Initialize SSL context (skip if no certificates available)
            if self.ssl_config['enabled']:
                try:
                    await self._create_ssl_context()
                except Exception as e:
                    self.logger.warning(f"SSL context creation failed (certificates may not be available yet): {e}")
                    # Continue without SSL for now
            
            # Create HTTP session with connection pooling
            await self._create_http_session()
            
            # Start background monitoring tasks
            self._start_background_tasks()
            
            self.logger.info(f"{self.module_name} started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start {self.module_name}: {e}")
            raise
    
    async def stop(self):
        """Stop the NMM module."""
        try:
            self.is_active = False
            
            # Cancel background tasks
            for task in self.background_tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for tasks to complete
            if self.background_tasks:
                await asyncio.gather(*self.background_tasks, return_exceptions=True)
            
            # Close HTTP session
            if self.session:
                await self.session.close()
            
            # Clean up temporary certificate files
            await self._cleanup_temp_cert_files()
            
            self.logger.info(f"{self.module_name} stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping {self.module_name}: {e}")
    
    def _start_background_tasks(self):
        """Start background monitoring tasks."""
        # Health monitoring task
        task = asyncio.create_task(self._health_monitor_loop())
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)
        
        # Connection maintenance task
        task = asyncio.create_task(self._connection_maintenance_loop())
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)
    
    async def update_ssl_certificates(self, cert_data: Dict[str, Any]) -> bool:
        """
        Update SSL certificates from CCU - following RLA pattern.
        
        Args:
            cert_data: Dictionary containing certificate data from CCU
            
        Returns:
            bool: True if certificates were updated successfully
        """
        try:
            self.logger.info("Updating SSL certificates from CCU")
            
            # Validate certificate data
            if not cert_data.get('cert_content') or not cert_data.get('key_content'):
                self.logger.error("Invalid certificate data received")
                return False
            
            # Check if certificates have changed
            new_cert_hash = cert_data.get('cert_hash', '')
            new_key_hash = cert_data.get('key_hash', '')
            
            if (new_cert_hash == self.ssl_config.get('cert_hash') and 
                new_key_hash == self.ssl_config.get('key_hash')):
                self.logger.info("Certificates unchanged, skipping update")
                return True
            
            # Update SSL configuration
            self.ssl_config.update({
                'cert_content': cert_data['cert_content'],
                'key_content': cert_data['key_content'],
                'cert_hash': new_cert_hash,
                'key_hash': new_key_hash,
                'expires_at': cert_data.get('expires_at'),
                'distributed_at': cert_data.get('distributed_at'),
                'last_update': datetime.now().isoformat()
            })
            
            # Recreate SSL context with new certificates
            success = await self._create_ssl_context()
            
            if success:
                # Recreate HTTP session with new SSL context
                await self._recreate_http_session()
                
                self.stats['certificate_updates'] += 1
                self.logger.info("SSL certificates updated successfully")
                
                return True
            else:
                self.logger.error("Failed to create SSL context with new certificates")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to update SSL certificates: {e}")
            return False
    
    async def _create_ssl_context(self) -> bool:
        """Create SSL context from certificate content - following RLA pattern."""
        try:
            if not self.ssl_config.get('cert_content') or not self.ssl_config.get('key_content'):
                self.logger.warning("No certificate content available, SSL disabled")
                self.ssl_context = None
                return False
            
            # Clean up old temp files
            await self._cleanup_temp_cert_files()
            
            # Create temporary certificate files
            cert_temp = tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False)
            key_temp = tempfile.NamedTemporaryFile(mode='w', suffix='.key', delete=False)
            
            # Write certificate content to temporary files
            cert_temp.write(self.ssl_config['cert_content'])
            cert_temp.close()
            
            key_temp.write(self.ssl_config['key_content'])
            key_temp.close()
            
            # Store temp file paths for cleanup
            self.ssl_config['temp_cert_file'] = cert_temp.name
            self.ssl_config['temp_key_file'] = key_temp.name
            
            # Create SSL context for client connections
            self.ssl_context = ssl.create_default_context()
            self.ssl_context.load_cert_chain(cert_temp.name, key_temp.name)
            
            # Configure SSL context for client use
            self.ssl_context.check_hostname = True
            self.ssl_context.verify_mode = ssl.CERT_REQUIRED
            
            self.stats['ssl_context_recreations'] += 1
            self.logger.info("SSL context created successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create SSL context: {e}")
            self.ssl_context = None
            return False
    
    async def _cleanup_temp_cert_files(self):
        """Clean up temporary certificate files - following RLA pattern."""
        try:
            for file_key in ['temp_cert_file', 'temp_key_file']:
                temp_file = self.ssl_config.get(file_key)
                if temp_file and os.path.exists(temp_file):
                    os.unlink(temp_file)
                    self.ssl_config[file_key] = None
                    
        except Exception as e:
            self.logger.error(f"Failed to cleanup temp cert files: {e}")
    
    async def _create_http_session(self):
        """Create HTTP session with connection pooling."""
        try:
            # Configure connection timeout
            timeout = aiohttp.ClientTimeout(
                total=self.network_config.get('total_timeout', 60),
                connect=self.network_config.get('connect_timeout', 10),
                sock_read=self.network_config.get('read_timeout', 30)
            )
            
            # Configure connection pool - handle SSL context availability
            ssl_context = None
            if self.ssl_config['enabled'] and self.ssl_context:
                ssl_context = self.ssl_context
            
            connector = aiohttp.TCPConnector(
                limit=self.network_config.get('max_connections', 50),
                limit_per_host=self.network_config.get('max_connections_per_host', 10),
                ttl_dns_cache=300,
                use_dns_cache=True,
                ssl=ssl_context
            )
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    'User-Agent': 'OCM/1.0',
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            )
            
            self.logger.info("HTTP session created with connection pooling")
            
        except Exception as e:
            self.logger.error(f"Failed to create HTTP session: {e}")
            raise
    
    async def _recreate_http_session(self):
        """Recreate HTTP session with updated SSL context."""
        try:
            # Close existing session
            if self.session:
                await self.session.close()
                
            # Create new session
            await self._create_http_session()
            
            self.logger.info("HTTP session recreated with updated SSL context")
            
        except Exception as e:
            self.logger.error(f"Failed to recreate HTTP session: {e}")
            raise
    
    async def send_data(self, data: Dict[str, Any], 
                       delivery_options: Dict[str, Any] = None,
                       priority: str = 'C') -> Dict[str, Any]:
        """
        Send data to web server with custom acknowledgment protocol.
        
        Args:
            data: Data to send
            delivery_options: Delivery configuration options
            priority: Priority level (A, B, C, D)
            
        Returns:
            Dict containing delivery result and acknowledgment details
        """
        try:
            if not self.session:
                raise ConnectionError("HTTP session not initialized")
            
            start_time = time.time()
            
            # Prepare request data
            request_data = {
                'data': data,
                'priority': priority,
                'timestamp': datetime.now().isoformat(),
                'request_id': self._generate_request_id(),
                'ocm_service_id': 'OCM_PRIMARY'
            }
            
            # Add checksum if enabled
            if self.ack_protocol['checksum_validation']:
                request_data['checksum'] = self._calculate_checksum(data)
            
            # Construct URL - use HTTP if SSL context not available
            protocol = "https" if (self.ssl_config['enabled'] and self.ssl_context) else "http"
            url = f"{protocol}://{self.web_server_host}:{self.web_server_port}{self.web_server_endpoint}"
            
            # Send request with retry logic
            for attempt in range(self.ack_protocol['retry_attempts'] + 1):
                try:
                    self.logger.info(f"Sending data to {url} (attempt {attempt + 1})")
                    
                    # Use SSL context only if available
                    ssl_context = self.ssl_context if (self.ssl_config['enabled'] and self.ssl_context) else False
                    
                    async with self.session.post(
                        url,
                        json=request_data,
                        ssl=ssl_context
                    ) as response:
                        
                        response_data = await response.json()
                        
                        # Update statistics
                        processing_time = (time.time() - start_time) * 1000
                        self.stats['total_requests'] += 1
                        self.stats['bytes_sent'] += len(json.dumps(request_data).encode())
                        self.stats['bytes_received'] += len(await response.text())
                        self.stats['last_activity'] = datetime.now().isoformat()
                        
                        # Update average response time
                        total = self.stats['total_requests']
                        self.stats['average_response_time'] = (
                            (self.stats['average_response_time'] * (total - 1) + processing_time) / total
                        )
                        
                        if response.status == 200:
                            # Validate acknowledgment if enabled
                            if self.ack_protocol['enabled']:
                                ack_result = self._validate_acknowledgment(response_data, request_data)
                                if not ack_result['valid']:
                                    self.stats['acknowledgment_failures'] += 1
                                    if attempt < self.ack_protocol['retry_attempts']:
                                        self.logger.warning(f"Acknowledgment validation failed, retrying: {ack_result['reason']}")
                                        continue
                                    else:
                                        self.stats['failed_requests'] += 1
                                        return {
                                            'success': False,
                                            'error': f"Acknowledgment validation failed: {ack_result['reason']}",
                                            'response_data': response_data,
                                            'processing_time_ms': processing_time
                                        }
                            
                            self.stats['successful_requests'] += 1
                            return {
                                'success': True,
                                'response_data': response_data,
                                'processing_time_ms': processing_time,
                                'delivery_confirmed': True,
                                'acknowledgment_valid': True if self.ack_protocol['enabled'] else None
                            }
                        else:
                            error_msg = f"HTTP {response.status}: {response_data.get('message', 'Unknown error')}"
                            if attempt < self.ack_protocol['retry_attempts']:
                                self.logger.warning(f"{error_msg}, retrying...")
                                continue
                            else:
                                self.stats['failed_requests'] += 1
                                return {
                                    'success': False,
                                    'error': error_msg,
                                    'http_status': response.status,
                                    'response_data': response_data,
                                    'processing_time_ms': processing_time
                                }
                
                except aiohttp.ClientSSLError as e:
                    self.stats['ssl_handshake_errors'] += 1
                    error_msg = f"SSL handshake error: {e}"
                    if attempt < self.ack_protocol['retry_attempts']:
                        self.logger.warning(f"{error_msg}, retrying...")
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    else:
                        self.stats['failed_requests'] += 1
                        return {
                            'success': False,
                            'error': error_msg,
                            'ssl_error': True,
                            'processing_time_ms': (time.time() - start_time) * 1000
                        }
                
                except aiohttp.ClientTimeout as e:
                    self.stats['connection_timeouts'] += 1
                    error_msg = f"Connection timeout: {e}"
                    if attempt < self.ack_protocol['retry_attempts']:
                        self.logger.warning(f"{error_msg}, retrying...")
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    else:
                        self.stats['failed_requests'] += 1
                        return {
                            'success': False,
                            'error': error_msg,
                            'timeout_error': True,
                            'processing_time_ms': (time.time() - start_time) * 1000
                        }
                
                except Exception as e:
                    error_msg = f"Network error: {e}"
                    if attempt < self.ack_protocol['retry_attempts']:
                        self.logger.warning(f"{error_msg}, retrying...")
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    else:
                        self.stats['failed_requests'] += 1
                        return {
                            'success': False,
                            'error': error_msg,
                            'network_error': True,
                            'processing_time_ms': (time.time() - start_time) * 1000
                        }
            
            # Should not reach here
            self.stats['failed_requests'] += 1
            return {
                'success': False,
                'error': 'Maximum retry attempts exceeded',
                'processing_time_ms': (time.time() - start_time) * 1000
            }
            
        except Exception as e:
            self.logger.error(f"Failed to send data: {e}")
            self.stats['failed_requests'] += 1
            return {
                'success': False,
                'error': str(e),
                'processing_time_ms': (time.time() - time.time()) * 1000
            }
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        return f"ocm_req_{int(time.time() * 1000)}_{id(self)}"
    
    def _calculate_checksum(self, data: Dict[str, Any]) -> str:
        """Calculate SHA-256 checksum of data."""
        try:
            data_str = json.dumps(data, sort_keys=True)
            return hashlib.sha256(data_str.encode()).hexdigest()
        except Exception as e:
            self.logger.error(f"Failed to calculate checksum: {e}")
            return ""
    
    def _validate_acknowledgment(self, response_data: Dict[str, Any], 
                               request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate acknowledgment response."""
        try:
            # Check if acknowledgment is present
            if 'acknowledgment' not in response_data:
                return {'valid': False, 'reason': 'No acknowledgment in response'}
            
            ack_data = response_data['acknowledgment']
            
            # Check request ID match
            if ack_data.get('request_id') != request_data.get('request_id'):
                return {'valid': False, 'reason': 'Request ID mismatch'}
            
            # Check checksum if enabled
            if (self.ack_protocol['checksum_validation'] and 
                'checksum' in request_data):
                
                received_checksum = ack_data.get('received_checksum')
                if received_checksum != request_data['checksum']:
                    return {'valid': False, 'reason': 'Checksum validation failed'}
            
            # Check acknowledgment status
            if ack_data.get('status') != 'confirmed':
                return {'valid': False, 'reason': f"Acknowledgment status: {ack_data.get('status')}"}
            
            return {'valid': True, 'reason': 'Acknowledgment validated successfully'}
            
        except Exception as e:
            return {'valid': False, 'reason': f'Acknowledgment validation error: {e}'}
    
    async def _health_monitor_loop(self):
        """Background task for health monitoring."""
        while self.is_active:
            try:
                await self._perform_health_check()
                await asyncio.sleep(self.health_monitoring['check_interval'])
                
            except Exception as e:
                self.logger.error(f"Error in health monitor loop: {e}")
                await asyncio.sleep(30)
    
    async def _perform_health_check(self):
        """Perform health check on web server connection."""
        try:
            if not self.session:
                self.health_monitoring['is_healthy'] = False
                return
            
            # Simple health check request
            protocol = "https" if self.ssl_config['enabled'] else "http"
            health_url = f"{protocol}://{self.web_server_host}:{self.web_server_port}/health"
            
            async with self.session.get(
                health_url,
                timeout=aiohttp.ClientTimeout(total=self.health_monitoring['timeout']),
                ssl=self.ssl_context if self.ssl_config['enabled'] else False
            ) as response:
                
                if response.status == 200:
                    self.health_monitoring['consecutive_failures'] = 0
                    self.health_monitoring['is_healthy'] = True
                else:
                    self.health_monitoring['consecutive_failures'] += 1
                    
        except Exception as e:
            self.logger.debug(f"Health check failed: {e}")
            self.health_monitoring['consecutive_failures'] += 1
        
        # Update health status based on consecutive failures
        if (self.health_monitoring['consecutive_failures'] >= 
            self.health_monitoring['failure_threshold']):
            self.health_monitoring['is_healthy'] = False
        
        self.health_monitoring['last_health_check'] = datetime.now().isoformat()
    
    async def _connection_maintenance_loop(self):
        """Background task for connection maintenance."""
        while self.is_active:
            try:
                # Check SSL certificate expiry
                await self._check_certificate_expiry()
                
                # Maintenance interval
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Error in connection maintenance loop: {e}")
                await asyncio.sleep(60)
    
    async def _check_certificate_expiry(self):
        """Check SSL certificate expiry and log warnings."""
        try:
            if not self.ssl_config.get('expires_at'):
                return
            
            expires_at = datetime.fromisoformat(self.ssl_config['expires_at'])
            time_to_expiry = expires_at - datetime.now()
            
            if time_to_expiry.days <= 7:
                self.logger.warning(f"SSL certificate expires in {time_to_expiry.days} days")
            elif time_to_expiry.days <= 30:
                self.logger.info(f"SSL certificate expires in {time_to_expiry.days} days")
                
        except Exception as e:
            self.logger.error(f"Error checking certificate expiry: {e}")
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to web server."""
        try:
            test_data = {
                'test': True,
                'timestamp': datetime.now().isoformat(),
                'service': 'OCM'
            }
            
            result = await self.send_data(test_data, priority='D')
            
            return {
                'connection_test': 'passed' if result['success'] else 'failed',
                'result': result,
                'ssl_enabled': self.ssl_config['enabled'],
                'ssl_context_valid': self.ssl_context is not None
            }
            
        except Exception as e:
            return {
                'connection_test': 'failed',
                'error': str(e),
                'ssl_enabled': self.ssl_config['enabled'],
                'ssl_context_valid': self.ssl_context is not None
            }
    
    def get_ssl_status(self) -> Dict[str, Any]:
        """Get SSL certificate status."""
        return {
            'ssl_enabled': self.ssl_config['enabled'],
            'certificate_source': self.ssl_config['certificate_source'],
            'has_certificates': bool(self.ssl_config.get('cert_content')),
            'cert_hash': self.ssl_config.get('cert_hash', '')[:16] + '...' if self.ssl_config.get('cert_hash') else '',
            'expires_at': self.ssl_config.get('expires_at'),
            'last_update': self.ssl_config.get('last_update'),
            'ssl_context_valid': self.ssl_context is not None,
            'temp_files_exist': bool(self.ssl_config.get('temp_cert_file') and os.path.exists(self.ssl_config.get('temp_cert_file', '')))
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        try:
            # Test connection
            connection_test = await self.test_connection()
            
            return {
                'healthy': (self.is_active and 
                           self.health_monitoring['is_healthy'] and
                           connection_test['connection_test'] == 'passed'),
                'module': self.module_name,
                'is_active': self.is_active,
                'session_valid': self.session is not None,
                'ssl_status': self.get_ssl_status(),
                'health_monitoring': self.health_monitoring,
                'connection_test': connection_test,
                'statistics': self.stats,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'module': self.module_name,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the NMM module."""
        return {
            'module': self.module_name,
            'is_active': self.is_active,
            'web_server_config': {
                'host': self.web_server_host,
                'port': self.web_server_port,
                'endpoint': self.web_server_endpoint,
                'protocol': 'HTTPS' if self.ssl_config['enabled'] else 'HTTP'
            },
            'ssl_status': self.get_ssl_status(),
            'health_monitoring': self.health_monitoring,
            'acknowledgment_protocol': self.ack_protocol,
            'statistics': self.stats
        } 