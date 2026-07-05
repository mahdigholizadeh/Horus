"""
Data Receiver Module (DRM) for RLA Microservice

This module handles data reception on port 3781 with SSL/TLS support:
- HTTPS server for secure data reception
- Dynamic SSL certificate management from CCU
- Protocol handling (R1, JSON data, R2)
- Certificate hot-reload capability
"""

import asyncio
import logging
import ssl
import json
import struct
import tempfile
import os
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import hashlib
import aiohttp
from aiohttp import web, web_request
import aiohttp_cors


class DataReceiverModule:
    """Data Receiver Module for handling secure data reception on port 3781."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.module_name = "DRM"
        self.is_active = False
        self.is_listening = False
        
        # SSL configuration
        self.ssl_config = {
            'enabled': True,
            'certificate_source': 'ccu_managed',
            'cert_content': '',
            'key_content': '',
            'cert_hash': '',
            'key_hash': '',
            'expires_at': None,
            'distributed_at': None,
            'temp_cert_file': None,
            'temp_key_file': None
        }
        
        # Network settings
        self.server_config = {
            'host': '0.0.0.0',
            'port': 3781,
            'max_connections': 100,
            'timeout': 30
        }
        
        # Protocol constants
        self.protocol_markers = {
            'handshake_start': 0xBB7F73DF,  # R1
            'handshake_end': 0xBB7578DF,    # R2
            'success_ack': 0xBFFF
        }
        
        # Server instance
        self.app = None
        self.runner = None
        self.site = None
        self.ssl_context = None
        
        # Statistics
        self.stats = {
            'total_connections': 0,
            'successful_receptions': 0,
            'failed_receptions': 0,
            'ssl_handshake_errors': 0,
            'protocol_errors': 0,
            'certificate_updates': 0,
            'last_activity': None
        }
        
        self.logger.info(f"{self.module_name} initialized")
    
    async def start(self):
        """Start the DRM module."""
        try:
            self.is_active = True
            self.logger.info(f"{self.module_name} started")
            
        except Exception as e:
            self.logger.error(f"Failed to start {self.module_name}: {e}")
            raise
    
    async def stop(self):
        """Stop the DRM module."""
        try:
            self.is_active = False
            
            # Stop data listener
            if self.is_listening:
                await self.stop_data_listener()
            
            # Clean up temporary certificate files
            await self._cleanup_temp_cert_files()
            
            self.logger.info(f"{self.module_name} stopped")
            
        except Exception as e:
            self.logger.error(f"Failed to stop {self.module_name}: {e}")
            raise
    
    async def start_data_listener(self, port: int = None, ssl_config: Dict[str, Any] = None):
        """Start data listener on specified port with SSL support."""
        try:
            if port:
                self.server_config['port'] = port
            
            if ssl_config:
                self.ssl_config.update(ssl_config)
            
            # Create aiohttp web application
            self.app = web.Application()
            
            # Add CORS support
            cors = aiohttp_cors.setup(self.app, defaults={
                "*": aiohttp_cors.ResourceOptions(
                    allow_credentials=True,
                    expose_headers="*",
                    allow_headers="*",
                    allow_methods="*"
                )
            })
            
            # Add routes
            self.app.router.add_post('/data', self._handle_data_reception)
            self.app.router.add_get('/health', self._handle_health_check)
            self.app.router.add_post('/activate', self._handle_activation_command)
            self.app.router.add_post('/activate_gateway', self._handle_gateway_activation)
            
            # Add CORS to all routes
            for route in list(self.app.router.routes()):
                cors.add(route)
            
            # Create SSL context if certificates are available
            if self.ssl_config.get('enabled', True):
                await self._create_ssl_context()
            
            # Start the server
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            self.site = web.TCPSite(
                self.runner,
                self.server_config['host'],
                self.server_config['port'],
                ssl_context=self.ssl_context
            )
            
            await self.site.start()
            self.is_listening = True
            
            protocol = "HTTPS" if self.ssl_context else "HTTP"
            self.logger.info(
                f"Data listener started on {protocol}://{self.server_config['host']}:{self.server_config['port']}"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to start data listener: {e}")
            raise
    
    async def stop_data_listener(self):
        """Stop the data listener."""
        try:
            self.logger.info("Stopping data listener...")
            
            self.is_listening = False
            
            if self.site:
                await self.site.stop()
                self.site = None
            
            if self.runner:
                await self.runner.cleanup()
                self.runner = None
            
            self.app = None
            
            self.logger.info("Data listener stopped")
            
        except Exception as e:
            self.logger.error(f"Failed to stop data listener: {e}")
    
    async def update_ssl_certificates(self, cert_data: Dict[str, Any]) -> bool:
        """Update SSL certificates from CCU."""
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
                'distributed_at': cert_data.get('distributed_at')
            })
            
            # If server is running, restart with new certificates
            if self.is_listening:
                self.logger.info("Restarting data listener with new certificates")
                await self.stop_data_listener()
                await self.start_data_listener()
            
            self.stats['certificate_updates'] += 1
            self.logger.info("SSL certificates updated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update SSL certificates: {e}")
            return False
    
    async def _create_ssl_context(self) -> bool:
        """Create SSL context from certificate content."""
        try:
            if not self.ssl_config.get('cert_content') or not self.ssl_config.get('key_content'):
                self.logger.warning("No certificate content available, running without SSL")
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
            
            # Create SSL context
            self.ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            self.ssl_context.load_cert_chain(cert_temp.name, key_temp.name)
            
            self.logger.info("SSL context created successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create SSL context: {e}")
            self.ssl_context = None
            return False
    
    async def _cleanup_temp_cert_files(self):
        """Clean up temporary certificate files."""
        try:
            for file_key in ['temp_cert_file', 'temp_key_file']:
                temp_file = self.ssl_config.get(file_key)
                if temp_file and os.path.exists(temp_file):
                    os.unlink(temp_file)
                    self.ssl_config[file_key] = None
                    
        except Exception as e:
            self.logger.error(f"Failed to cleanup temp cert files: {e}")
    
    async def _handle_data_reception(self, request: web_request.Request) -> web.Response:
        """Handle data reception from clients."""
        try:
            self.stats['total_connections'] += 1
            self.stats['last_activity'] = datetime.now()
            
            client_ip = request.remote
            self.logger.info(f"Data reception request from {client_ip}")
            
            # Read request body
            body_bytes = await request.read()
            
            # Process the data according to RLA protocol
            result = await self._process_rla_protocol(body_bytes)
            
            if result.get('success'):
                self.stats['successful_receptions'] += 1
                return web.json_response({
                    'status': 'success',
                    'validation_flag': result.get('validation_flag', 1),
                    'token_limit_flag': result.get('token_limit_flag', 1),
                    'message': 'Data received and processed successfully'
                })
            else:
                self.stats['failed_receptions'] += 1
                return web.json_response({
                    'status': 'error',
                    'message': result.get('error', 'Data processing failed')
                }, status=400)
                
        except Exception as e:
            self.logger.error(f"Error handling data reception: {e}")
            self.stats['failed_receptions'] += 1
            return web.json_response({
                'status': 'error',
                'message': 'Internal server error'
            }, status=500)
    
    async def _process_rla_protocol(self, data_bytes: bytes) -> Dict[str, Any]:
        """Process data according to RLA protocol (R1 + JSON + R2)."""
        try:
            if len(data_bytes) < 12:  # Minimum: R1(4) + length(4) + R2(4)
                return {'success': False, 'error': 'Insufficient data'}
            
            offset = 0
            
            # Check R1 handshake marker
            r1_marker = struct.unpack('>I', data_bytes[offset:offset+4])[0]
            offset += 4
            
            if r1_marker != self.protocol_markers['handshake_start']:
                self.stats['protocol_errors'] += 1
                return {'success': False, 'error': f'Invalid R1 handshake: 0x{r1_marker:08X}'}
            
            # Get JSON data length
            json_length = struct.unpack('>I', data_bytes[offset:offset+4])[0]
            offset += 4
            
            # Extract JSON data
            if offset + json_length + 4 > len(data_bytes):
                return {'success': False, 'error': 'Incomplete data'}
                
            json_bytes = data_bytes[offset:offset+json_length]
            offset += json_length
            
            # Check R2 handshake marker
            r2_marker = struct.unpack('>I', data_bytes[offset:offset+4])[0]
            
            if r2_marker != self.protocol_markers['handshake_end']:
                self.stats['protocol_errors'] += 1
                return {'success': False, 'error': f'Invalid R2 handshake: 0x{r2_marker:08X}'}
            
            # Parse JSON data
            try:
                json_data = json.loads(json_bytes.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                return {'success': False, 'error': f'Invalid JSON data: {e}'}
            
            # Process the JSON data (validation, limit checking, etc.)
            # This would integrate with other RLA modules
            return {
                'success': True,
                'data': json_data,
                'validation_flag': 1,
                'token_limit_flag': 1
            }
            
        except Exception as e:
            self.logger.error(f"Error processing RLA protocol: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_health_check(self, request: web_request.Request) -> web.Response:
        """Handle health check requests."""
        try:
            health_info = {
                'service': 'RLA-DRM',
                'status': 'healthy' if self.is_active else 'inactive',
                'ssl_enabled': self.ssl_context is not None,
                'certificate_info': {
                    'source': self.ssl_config.get('certificate_source'),
                    'expires_at': self.ssl_config.get('expires_at'),
                    'last_updated': self.ssl_config.get('distributed_at')
                },
                'statistics': self.stats,
                'timestamp': datetime.now().isoformat()
            }
            
            return web.json_response(health_info)
            
        except Exception as e:
            return web.json_response({
                'status': 'error',
                'error': str(e)
            }, status=500)
    
    async def _handle_activation_command(self, request: web_request.Request) -> web.Response:
        """Handle activation command from CCU via ECM."""
        try:
            # Parse activation command
            activation_data = await request.json()
            command = activation_data.get('command')
            
            if command == 'activate':
                self.logger.info("DRM: Received activation command from CCU")
                
                # Get the parent RLA microservice instance and call its activation handler
                # This is a bit of a hack for testing - in real implementation, 
                # this would go through proper ECM routing
                
                # For now, just acknowledge the activation
                response_data = {
                    "status": "activated",
                    "service": "RLA",
                    "endpoints": ["data:3781", "health:3781"],
                    "timestamp": datetime.now().isoformat(),
                    "message": "RLA activated and ready to receive requests"
                }
                
                self.logger.info("DRM: RLA activation acknowledged")
                return web.json_response(response_data)
            else:
                return web.json_response({
                    "status": "error",
                    "message": f"Unknown command: {command}"
                }, status=400)
                
        except Exception as e:
            self.logger.error(f"DRM: Activation command failed: {e}")
            return web.json_response({
                'status': 'error',
                'error': str(e)
            }, status=500)
    
    async def _handle_gateway_activation(self, request: web_request.Request) -> web.Response:
        """Handle gateway activation command from CCU."""
        try:
            # Parse gateway activation command
            activation_data = await request.json()
            command = activation_data.get('command', 'activate_gateway')
            
            self.logger.info("DRM: Received gateway activation command from CCU")
            
            # For now, just acknowledge the gateway activation
            # In a real implementation, this would trigger the RLA main service
            # to activate its gateway services
            
            response_data = {
                "status": "gateway_activated",
                "service": "RLA",
                "gateway": "data_reception",
                "endpoint": f"data:3781",
                "timestamp": datetime.now().isoformat(),
                "message": "RLA data reception gateway activated and ready"
            }
            
            self.logger.info("DRM: RLA gateway activation acknowledged - ready to receive requests")
            return web.json_response(response_data)
                
        except Exception as e:
            self.logger.error(f"DRM: Gateway activation failed: {e}")
            return web.json_response({
                'status': 'error',
                'error': str(e)
            }, status=500)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the DRM module."""
        return {
            'module': self.module_name,
            'is_active': self.is_active,
            'is_listening': self.is_listening,
            'server_config': self.server_config,
            'ssl_config': {
                'enabled': self.ssl_config.get('enabled'),
                'certificate_source': self.ssl_config.get('certificate_source'),
                'has_certificates': bool(self.ssl_config.get('cert_content')),
                'expires_at': self.ssl_config.get('expires_at')
            },
            'statistics': self.stats
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            # Check if SSL context is valid
            ssl_healthy = True
            if self.ssl_config.get('enabled'):
                ssl_healthy = self.ssl_context is not None
            
            return {
                'healthy': self.is_active and ssl_healthy,
                'module': self.module_name,
                'timestamp': datetime.now().isoformat(),
                'listening': self.is_listening,
                'ssl_context_valid': ssl_healthy,
                'statistics': self.stats
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'module': self.module_name,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            } 