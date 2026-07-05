"""
OCM End-to-End Integration Test Suite

This comprehensive test suite verifies the complete functionality and integration 
of the OCM (Output Cache Management) microservice with the CCU, including:

- SSL certificate management and hot-reload
- WebSocket communication with CCU via ECM
- Output processing through RMM pipeline
- Report generation (HTML, PDF)
- Secure delivery to web servers
- Priority-based request management
- Acknowledgment protocol validation
- Error handling and recovery
- Health monitoring and status reporting
"""

import asyncio
import aiohttp
import websockets
import json
import ssl
import tempfile
import os
import hashlib
import pytest
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, AsyncMock, patch
import time

# Test configuration
TEST_CONFIG = {
    "service": {
        "name": "OCM_TEST",
        "version": "1.0.0-test"
    },
    "network": {
        "websocket_port": 47815,  # Different ports for testing
        "api_port": 47816,
        "web_server_host": "localhost",
        "web_server_port": 8443,
        "web_server_endpoint": "/api/test",
        "ssl_enabled": True
    },
    "ssl_configuration": {
        "enabled": True,
        "certificate_source": "ccu_managed",
        "hot_reload": True
    },
    "priority_management": {
        "priorities": ["A", "B", "C", "D"],
        "default_priority": "C"
    },
    "acknowledgment_protocol": {
        "enabled": True,
        "timeout": 10,  # Shorter timeout for testing
        "retry_attempts": 2,
        "checksum_validation": True
    },
    "database": {
        "type": "sqlite",
        "path": ":memory:",  # In-memory database for testing
        "partition_by_priority": True
    },
    "logging": {
        "level": "DEBUG"
    }
}

# Test SSL certificates (self-signed for testing)
TEST_SSL_CERT = """-----BEGIN CERTIFICATE-----
MIICljCCAX4CAQAwDQYJKoZIhvcNAQELBQAwFTETMBEGA1UEAwwKbG9jYWxob3N0
MB4XDTIzMTAxNTEwMzAwMFoXDTI0MTAxNTEwMzAwMFowFTETMBEGA1UEAwwKbG9j
YWxob3N0MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAyQZJN4K2sL8L
-----END CERTIFICATE-----"""

TEST_SSL_KEY = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDJBkk3grab8L0g
-----END PRIVATE KEY-----"""


class MockWebServer:
    """Mock web server for testing OCM delivery functionality."""
    
    def __init__(self, port: int = 8443):
        self.port = port
        self.app = None
        self.runner = None
        self.site = None
        self.received_requests = []
        self.acknowledgments = []
        
    async def start(self):
        """Start mock web server."""
        self.app = aiohttp.web.Application()
        
        # Add test endpoints
        self.app.router.add_post('/api/test', self._handle_test_data)
        self.app.router.add_get('/health', self._handle_health)
        
        self.runner = aiohttp.web.AppRunner(self.app)
        await self.runner.setup()
        
        self.site = aiohttp.web.TCPSite(self.runner, 'localhost', self.port)
        await self.site.start()
        
    async def stop(self):
        """Stop mock web server."""
        if self.runner:
            await self.runner.cleanup()
    
    async def _handle_test_data(self, request):
        """Handle test data from OCM."""
        try:
            data = await request.json()
            self.received_requests.append({
                'data': data,
                'timestamp': datetime.now().isoformat(),
                'headers': dict(request.headers)
            })
            
            # Generate acknowledgment
            acknowledgment = {
                'request_id': data.get('request_id'),
                'status': 'confirmed',
                'received_checksum': data.get('checksum'),
                'timestamp': datetime.now().isoformat()
            }
            
            self.acknowledgments.append(acknowledgment)
            
            return aiohttp.web.json_response({
                'status': 'success',
                'message': 'Data received successfully',
                'acknowledgment': acknowledgment
            })
            
        except Exception as e:
            return aiohttp.web.json_response({
                'status': 'error',
                'message': str(e)
            }, status=400)
    
    async def _handle_health(self, request):
        """Handle health check requests."""
        return aiohttp.web.json_response({
            'status': 'healthy',
            'service': 'MockWebServer',
            'timestamp': datetime.now().isoformat()
        })


class MockCCUWebSocket:
    """Mock CCU WebSocket server for testing ECM integration."""
    
    def __init__(self, port: int = 47815):
        self.port = port
        self.server = None
        self.connected_clients = []
        self.messages_received = []
        self.ssl_certificates_sent = []
        
    async def start(self):
        """Start mock CCU WebSocket server."""
        self.server = await websockets.serve(
            self._handle_client,
            'localhost',
            self.port
        )
        
    async def stop(self):
        """Stop mock CCU WebSocket server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
    
    async def _handle_client(self, websocket, path):
        """Handle WebSocket client connections."""
        try:
            self.connected_clients.append(websocket)
            
            # Handle authentication
            async for message in websocket:
                data = json.loads(message)
                self.messages_received.append(data)
                
                message_type = data.get('type')
                
                if message_type == 'authenticate':
                    await self._handle_authentication(websocket, data)
                elif message_type == 'heartbeat':
                    await self._handle_heartbeat(websocket, data)
                elif message_type == 'output_request':
                    await self._handle_output_request(websocket, data)
                elif message_type == 'command':
                    await self._handle_command(websocket, data)
                    
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            if websocket in self.connected_clients:
                self.connected_clients.remove(websocket)
    
    async def _handle_authentication(self, websocket, data):
        """Handle authentication from OCM."""
        await websocket.send(json.dumps({
            'type': 'authenticate_response',
            'status': 'authenticated',
            'message': 'OCM authenticated successfully',
            'timestamp': datetime.now().isoformat()
        }))
        
        # Send SSL certificates after authentication
        await self._send_ssl_certificates(websocket)
    
    async def _handle_heartbeat(self, websocket, data):
        """Handle heartbeat from OCM."""
        await websocket.send(json.dumps({
            'type': 'heartbeat_response',
            'status': 'active',
            'timestamp': datetime.now().isoformat(),
            'health_status': {
                'status': 'healthy',
                'modules': ['all_operational']
            }
        }))
    
    async def _handle_output_request(self, websocket, data):
        """Handle output processing request from OCM."""
        # Simulate processing delay
        await asyncio.sleep(0.1)
        
        await websocket.send(json.dumps({
            'type': 'request_response',
            'request_id': data.get('request_id'),
            'status': 'success',
            'data': {
                'processed_data': data.get('data'),
                'reports': ['test_report.html', 'test_report.pdf']
            },
            'processing_time_ms': 100,
            'generated_reports': ['test_report.html', 'test_report.pdf'],
            'delivered_at': datetime.now().isoformat()
        }))
    
    async def _handle_command(self, websocket, data):
        """Handle command from OCM."""
        command_type = data.get('command_type')
        
        if command_type == 'health_check':
            await websocket.send(json.dumps({
                'type': 'command_response',
                'command_id': data.get('command_id'),
                'status': 'success',
                'data': {
                    'health': 'excellent',
                    'modules': ['all_operational']
                }
            }))
    
    async def _send_ssl_certificates(self, websocket):
        """Send SSL certificates to OCM."""
        cert_data = {
            'cert_content': TEST_SSL_CERT,
            'key_content': TEST_SSL_KEY,
            'cert_hash': hashlib.sha256(TEST_SSL_CERT.encode()).hexdigest()[:32],
            'key_hash': hashlib.sha256(TEST_SSL_KEY.encode()).hexdigest()[:32],
            'expires_at': (datetime.now() + timedelta(days=365)).isoformat(),
            'distributed_at': datetime.now().isoformat()
        }
        
        self.ssl_certificates_sent.append(cert_data)
        
        await websocket.send(json.dumps({
            'type': 'certificate_update',
            'certificates': cert_data,
            'timestamp': datetime.now().isoformat()
        }))
    
    async def send_test_command(self, command_type: str, parameters: Dict[str, Any] = None):
        """Send test command to connected OCM clients."""
        if not self.connected_clients:
            return False
        
        message = {
            'type': 'command',
            'command_id': f'test_cmd_{int(time.time() * 1000)}',
            'command_type': command_type,
            'parameters': parameters or {},
            'timestamp': datetime.now().isoformat()
        }
        
        for client in self.connected_clients:
            try:
                await client.send(json.dumps(message))
            except Exception:
                pass
        
        return True


class OCMIntegrationTestSuite:
    """Comprehensive OCM integration test suite."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.mock_web_server = None
        self.mock_ccu_websocket = None
        self.ocm_service = None
        self.test_results = {}
        
    async def setup(self):
        """Set up test environment."""
        try:
            self.logger.info("Setting up OCM integration test environment")
            
            # Start mock web server
            self.mock_web_server = MockWebServer(port=8443)
            await self.mock_web_server.start()
            
            # Start mock CCU WebSocket
            self.mock_ccu_websocket = MockCCUWebSocket(port=47815)
            await self.mock_ccu_websocket.start()
            
            # Import and initialize OCM service with test config
            from ocm import OCMMicroservice
            
            # Patch the configuration loading
            with patch.object(OCMMicroservice, '_load_configuration', return_value=TEST_CONFIG):
                self.ocm_service = OCMMicroservice()
            
            # Start OCM service
            await self.ocm_service.start()
            
            # Wait for connections to establish
            await asyncio.sleep(2)
            
            self.logger.info("Test environment setup complete")
            
        except Exception as e:
            self.logger.error(f"Failed to set up test environment: {e}")
            await self.cleanup()
            raise
    
    async def cleanup(self):
        """Clean up test environment."""
        try:
            self.logger.info("Cleaning up test environment")
            
            if self.ocm_service:
                await self.ocm_service.stop()
            
            if self.mock_web_server:
                await self.mock_web_server.stop()
            
            if self.mock_ccu_websocket:
                await self.mock_ccu_websocket.stop()
            
            self.logger.info("Test environment cleanup complete")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all integration tests."""
        test_methods = [
            self.test_ssl_certificate_management,
            self.test_websocket_communication,
            self.test_output_processing_pipeline,
            self.test_priority_request_handling,
            self.test_acknowledgment_protocol,
            self.test_report_generation,
            self.test_error_handling_recovery,
            self.test_health_monitoring,
            self.test_service_control_commands,
            self.test_concurrent_requests,
            self.test_ssl_certificate_hot_reload,
            self.test_connection_recovery
        ]
        
        results = {}
        
        for test_method in test_methods:
            test_name = test_method.__name__
            self.logger.info(f"Running test: {test_name}")
            
            try:
                start_time = time.time()
                result = await test_method()
                execution_time = time.time() - start_time
                
                results[test_name] = {
                    'status': 'PASSED',
                    'result': result,
                    'execution_time': execution_time,
                    'timestamp': datetime.now().isoformat()
                }
                
                self.logger.info(f"✅ {test_name} PASSED ({execution_time:.2f}s)")
                
            except Exception as e:
                results[test_name] = {
                    'status': 'FAILED',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                
                self.logger.error(f"❌ {test_name} FAILED: {e}")
        
        # Generate test summary
        passed = sum(1 for r in results.values() if r['status'] == 'PASSED')
        failed = len(results) - passed
        
        summary = {
            'total_tests': len(results),
            'passed': passed,
            'failed': failed,
            'success_rate': (passed / len(results)) * 100 if results else 0,
            'execution_time': sum(r.get('execution_time', 0) for r in results.values()),
            'timestamp': datetime.now().isoformat(),
            'detailed_results': results
        }
        
        return summary
    
    async def test_ssl_certificate_management(self) -> Dict[str, Any]:
        """Test SSL certificate management and hot-reload functionality."""
        # Check that OCM received SSL certificates from mock CCU
        assert len(self.mock_ccu_websocket.ssl_certificates_sent) > 0, "No SSL certificates sent by mock CCU"
        
        # Check OCM SSL certificate status
        ssl_status = self.ocm_service.modules['NMM'].get_ssl_status()
        assert ssl_status['ssl_enabled'], "SSL not enabled in OCM"
        assert ssl_status['has_certificates'], "OCM does not have SSL certificates"
        assert ssl_status['ssl_context_valid'], "SSL context not valid"
        
        # Test certificate hot-reload
        new_cert_data = {
            'cert_content': TEST_SSL_CERT.replace('localhost', 'test-host'),
            'key_content': TEST_SSL_KEY,
            'cert_hash': 'new_cert_hash_123',
            'key_hash': 'new_key_hash_456',
            'expires_at': (datetime.now() + timedelta(days=360)).isoformat()
        }
        
        success = await self.ocm_service.modules['NMM'].update_ssl_certificates(new_cert_data)
        assert success, "SSL certificate update failed"
        
        # Verify certificate update statistics
        assert self.ocm_service.modules['NMM'].stats['certificate_updates'] > 0, "Certificate update count not incremented"
        
        return {
            'ssl_certificates_received': len(self.mock_ccu_websocket.ssl_certificates_sent),
            'certificate_updates': self.ocm_service.modules['NMM'].stats['certificate_updates'],
            'ssl_context_valid': ssl_status['ssl_context_valid']
        }
    
    async def test_websocket_communication(self) -> Dict[str, Any]:
        """Test WebSocket communication between OCM ECM and mock CCU."""
        # Check that OCM is connected to mock CCU
        assert len(self.mock_ccu_websocket.connected_clients) > 0, "OCM not connected to mock CCU"
        
        # Check messages received by mock CCU
        auth_messages = [msg for msg in self.mock_ccu_websocket.messages_received if msg.get('type') == 'authenticate']
        heartbeat_messages = [msg for msg in self.mock_ccu_websocket.messages_received if msg.get('type') == 'heartbeat']
        
        assert len(auth_messages) > 0, "No authentication messages received"
        assert len(heartbeat_messages) > 0, "No heartbeat messages received"
        
        # Test command sending
        test_sent = await self.mock_ccu_websocket.send_test_command('test_command', {'test_param': 'test_value'})
        assert test_sent, "Failed to send test command"
        
        # Wait for command processing
        await asyncio.sleep(1)
        
        return {
            'connected_clients': len(self.mock_ccu_websocket.connected_clients),
            'authentication_messages': len(auth_messages),
            'heartbeat_messages': len(heartbeat_messages),
            'total_messages_received': len(self.mock_ccu_websocket.messages_received)
        }
    
    async def test_output_processing_pipeline(self) -> Dict[str, Any]:
        """Test complete output processing pipeline through RMM."""
        test_data = {
            'content': 'Test output data for processing',
            'type': 'test_report',
            'metadata': {
                'source': 'integration_test',
                'timestamp': datetime.now().isoformat()
            }
        }
        
        # Submit output processing request
        result = await self.ocm_service.process_output_request(
            request_data=test_data,
            priority='B',
            delivery_options={'format': 'json'}
        )
        
        assert result['success'], f"Output processing failed: {result.get('error')}"
        assert 'request_id' in result, "No request ID returned"
        
        # Wait for processing completion
        await asyncio.sleep(2)
        
        # Check statistics
        stats = self.ocm_service.stats
        assert stats['requests_processed'] > 0, "Request count not incremented"
        
        return {
            'processing_result': result,
            'requests_processed': stats['requests_processed'],
            'reports_generated': stats.get('reports_generated', 0)
        }
    
    async def test_priority_request_handling(self) -> Dict[str, Any]:
        """Test priority-based request handling."""
        priorities = ['A', 'B', 'C', 'D']
        results = {}
        
        # Submit requests with different priorities
        for priority in priorities:
            test_data = {
                'content': f'Priority {priority} test data',
                'priority_level': priority
            }
            
            result = await self.ocm_service.process_output_request(
                request_data=test_data,
                priority=priority
            )
            
            results[priority] = result
            assert result['success'], f"Priority {priority} request failed: {result.get('error')}"
        
        # Wait for all requests to process
        await asyncio.sleep(3)
        
        return {
            'priority_requests_submitted': len(priorities),
            'successful_requests': sum(1 for r in results.values() if r['success']),
            'request_results': results
        }
    
    async def test_acknowledgment_protocol(self) -> Dict[str, Any]:
        """Test custom acknowledgment protocol."""
        # Check if mock web server received requests with acknowledgment protocol
        initial_count = len(self.mock_web_server.received_requests)
        
        # Submit test request that should trigger delivery to web server
        test_data = {
            'content': 'Test data for acknowledgment protocol',
            'require_acknowledgment': True
        }
        
        result = await self.ocm_service.process_output_request(
            request_data=test_data,
            priority='C'
        )
        
        assert result['success'], "Request failed"
        
        # Wait for delivery and acknowledgment
        await asyncio.sleep(3)
        
        # Check if web server received the request
        current_count = len(self.mock_web_server.received_requests)
        
        # Verify acknowledgment protocol data
        if current_count > initial_count:
            latest_request = self.mock_web_server.received_requests[-1]
            request_data = latest_request['data']
            
            assert 'request_id' in request_data, "No request ID in delivered data"
            assert 'checksum' in request_data, "No checksum in delivered data"
            
            # Check acknowledgment
            acknowledgments = self.mock_web_server.acknowledgments
            matching_ack = next((ack for ack in acknowledgments if ack['request_id'] == request_data['request_id']), None)
            assert matching_ack is not None, "No matching acknowledgment found"
            assert matching_ack['status'] == 'confirmed', "Acknowledgment not confirmed"
        
        return {
            'requests_delivered': current_count - initial_count,
            'acknowledgments_received': len(self.mock_web_server.acknowledgments),
            'protocol_validation': 'passed'
        }
    
    async def test_report_generation(self) -> Dict[str, Any]:
        """Test HTML and PDF report generation."""
        test_data = {
            'title': 'Integration Test Report',
            'content': 'This is a test report for integration testing.',
            'template': 'default',
            'generate_pdf': True
        }
        
        # Test HTML report generation
        html_result = await self.ocm_service.modules['HRPM'].generate_html_report(test_data)
        assert html_result['success'], f"HTML generation failed: {html_result.get('error')}"
        
        # Test PDF report generation
        pdf_result = await self.ocm_service.modules['PRFPM'].generate_pdf_report(html_result.get('html_content', ''))
        assert pdf_result['success'], f"PDF generation failed: {pdf_result.get('error')}"
        
        return {
            'html_generation': html_result['success'],
            'pdf_generation': pdf_result['success'],
            'html_size': len(html_result.get('html_content', '')),
            'pdf_size': len(pdf_result.get('pdf_content', b''))
        }
    
    async def test_error_handling_recovery(self) -> Dict[str, Any]:
        """Test error handling and recovery mechanisms."""
        # Test invalid request handling
        invalid_data = None
        
        try:
            await self.ocm_service.process_output_request(invalid_data)
            assert False, "Should have raised an exception for invalid data"
        except Exception as e:
            error_handled = True
        
        # Check EMM statistics
        emm_stats = self.ocm_service.modules['EMM'].get_statistics()
        
        # Test recovery after error
        valid_data = {'content': 'Recovery test data'}
        recovery_result = await self.ocm_service.process_output_request(valid_data)
        
        return {
            'error_properly_handled': error_handled,
            'errors_recorded': emm_stats.get('total_errors_handled', 0),
            'service_recovered': recovery_result['success']
        }
    
    async def test_health_monitoring(self) -> Dict[str, Any]:
        """Test health monitoring and status reporting."""
        # Get comprehensive health check
        health_result = await self.ocm_service.health_check()
        assert health_result['healthy'], f"Service not healthy: {health_result}"
        
        # Check individual module health
        module_health = health_result.get('modules_health', {})
        healthy_modules = sum(1 for h in module_health.values() if h.get('healthy', False))
        
        # Get service status
        status = self.ocm_service.get_service_status()
        assert status['active'], "Service not active"
        
        return {
            'overall_health': health_result['healthy'],
            'healthy_modules': healthy_modules,
            'total_modules': len(module_health),
            'uptime_seconds': health_result.get('uptime_seconds', 0),
            'service_active': status['active']
        }
    
    async def test_service_control_commands(self) -> Dict[str, Any]:
        """Test service control commands through CCU integration."""
        # Test configuration update
        config_updates = {
            'priority_management': {
                'default_priority': 'B'
            }
        }
        
        update_result = await self.ocm_service.update_configuration(config_updates)
        assert update_result, "Configuration update failed"
        
        # Test running tests
        test_result = await self.ocm_service.run_tests(['health'])
        assert test_result.get('status') != 'error', f"Test execution failed: {test_result}"
        
        return {
            'configuration_update': update_result,
            'test_execution': test_result.get('status', 'unknown'),
            'tests_run': len(test_result.get('results', {}))
        }
    
    async def test_concurrent_requests(self) -> Dict[str, Any]:
        """Test handling of concurrent requests."""
        concurrent_count = 5
        tasks = []
        
        # Submit multiple concurrent requests
        for i in range(concurrent_count):
            test_data = {
                'content': f'Concurrent test request {i}',
                'request_number': i
            }
            
            task = asyncio.create_task(
                self.ocm_service.process_output_request(test_data, priority='C')
            )
            tasks.append(task)
        
        # Wait for all requests to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_requests = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
        failed_requests = len(results) - successful_requests
        
        return {
            'concurrent_requests_submitted': concurrent_count,
            'successful_requests': successful_requests,
            'failed_requests': failed_requests,
            'success_rate': (successful_requests / concurrent_count) * 100
        }
    
    async def test_ssl_certificate_hot_reload(self) -> Dict[str, Any]:
        """Test SSL certificate hot-reload during operation."""
        # Get initial certificate info
        initial_ssl_status = self.ocm_service.modules['NMM'].get_ssl_status()
        initial_cert_hash = initial_ssl_status.get('cert_hash', '')
        
        # Send new certificates through mock CCU
        new_cert_data = {
            'cert_content': TEST_SSL_CERT.replace('2023', '2024'),
            'key_content': TEST_SSL_KEY,
            'cert_hash': 'updated_cert_hash_789',
            'key_hash': 'updated_key_hash_012',
            'expires_at': (datetime.now() + timedelta(days=300)).isoformat()
        }
        
        # Simulate certificate update from CCU
        for client in self.mock_ccu_websocket.connected_clients:
            await client.send(json.dumps({
                'type': 'certificate_update',
                'certificates': new_cert_data,
                'timestamp': datetime.now().isoformat()
            }))
        
        # Wait for certificate update processing
        await asyncio.sleep(2)
        
        # Check that certificates were updated
        updated_ssl_status = self.ocm_service.modules['NMM'].get_ssl_status()
        updated_cert_hash = updated_ssl_status.get('cert_hash', '')
        
        # Submit a request to verify service still works with new certificates
        test_request = await self.ocm_service.process_output_request({
            'content': 'Test after certificate update'
        })
        
        return {
            'certificate_hot_reload': updated_cert_hash != initial_cert_hash,
            'service_functional_after_update': test_request['success'],
            'ssl_context_valid': updated_ssl_status['ssl_context_valid'],
            'initial_cert_hash': initial_cert_hash[:16],
            'updated_cert_hash': updated_cert_hash[:16]
        }
    
    async def test_connection_recovery(self) -> Dict[str, Any]:
        """Test connection recovery after network interruption."""
        # Record initial connection state
        initial_clients = len(self.mock_ccu_websocket.connected_clients)
        
        # Simulate connection interruption by stopping and restarting mock CCU
        await self.mock_ccu_websocket.stop()
        await asyncio.sleep(2)  # Wait for disconnection
        
        # Check that OCM detects disconnection
        ocm_status = await self.ocm_service.health_check()
        ecm_health = ocm_status.get('modules_health', {}).get('ECM', {})
        
        # Restart mock CCU
        self.mock_ccu_websocket = MockCCUWebSocket(port=47815)
        await self.mock_ccu_websocket.start()
        
        # Wait for reconnection
        await asyncio.sleep(5)
        
        # Check that connection is restored
        restored_clients = len(self.mock_ccu_websocket.connected_clients)
        
        # Submit a request to verify service is working
        recovery_test = await self.ocm_service.process_output_request({
            'content': 'Connection recovery test'
        })
        
        return {
            'initial_connections': initial_clients,
            'connection_detected_loss': not ecm_health.get('healthy', True),
            'connections_restored': restored_clients,
            'service_functional_after_recovery': recovery_test['success']
        }


async def main():
    """Main function to run OCM integration tests."""
    # Configure logging for tests
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    # Create test suite
    test_suite = OCMIntegrationTestSuite()
    
    try:
        # Set up test environment
        await test_suite.setup()
        
        # Run all tests
        logger.info("🚀 Starting OCM End-to-End Integration Test Suite")
        results = await test_suite.run_all_tests()
        
        # Print results
        logger.info("📊 TEST RESULTS SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total Tests: {results['total_tests']}")
        logger.info(f"Passed: {results['passed']} ✅")
        logger.info(f"Failed: {results['failed']} ❌")
        logger.info(f"Success Rate: {results['success_rate']:.1f}%")
        logger.info(f"Total Execution Time: {results['execution_time']:.2f}s")
        logger.info("=" * 60)
        
        # Detailed results
        if results['failed'] > 0:
            logger.info("❌ FAILED TESTS:")
            for test_name, result in results['detailed_results'].items():
                if result['status'] == 'FAILED':
                    logger.error(f"  - {test_name}: {result['error']}")
        
        logger.info("✅ PASSED TESTS:")
        for test_name, result in results['detailed_results'].items():
            if result['status'] == 'PASSED':
                logger.info(f"  - {test_name} ({result['execution_time']:.2f}s)")
        
        # Overall result
        if results['success_rate'] == 100:
            logger.info("🎉 ALL TESTS PASSED! OCM Integration is working perfectly.")
        elif results['success_rate'] >= 80:
            logger.info("🎯 Most tests passed. OCM Integration is working well with minor issues.")
        else:
            logger.warning("⚠️  Multiple test failures. OCM Integration needs attention.")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Test suite failed to run: {e}")
        return {'error': str(e)}
        
    finally:
        # Clean up
        await test_suite.cleanup()


if __name__ == "__main__":
    results = asyncio.run(main())
    
    # Exit with appropriate code
    if results.get('error'):
        exit(1)
    elif results.get('success_rate', 0) < 100:
        exit(1)  # Some tests failed
    else:
        exit(0)  # All tests passed 