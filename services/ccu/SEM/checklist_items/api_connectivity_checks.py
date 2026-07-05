"""
API Connectivity Checker - SEM Checklist Item

Tests API connections and webserver connectivity for all Horus services.
Validates that services can communicate with external APIs and internal endpoints.
"""

import asyncio
import aiohttp
import logging
import time
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class APIConnectivityResult:
    """Result of API connectivity test."""
    service_name: str
    api_type: str
    endpoint: str
    success: bool
    message: str
    response_time_ms: float
    status_code: Optional[int] = None
    response_data: Optional[Dict[str, Any]] = None


class APIConnectivityChecker:
    """Tests API connectivity for all Horus services."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the API connectivity checker."""
        self.logger = logging.getLogger(f'{__name__}.APIConnectivityChecker')
        self.config = config
        self.timeout = 10  # seconds
        
        # API endpoints to test
        self.api_endpoints = {
            "RCM": {
                "openai_api": {
                    "url": "https://api.openai.com/v1/models",
                    "method": "GET",
                    "headers": self._get_openai_headers(),
                    "expected_status": 200,
                    "timeout": 10
                },
                "health_check": {
                    "url": "http://localhost:8082/health",
                    "method": "GET",
                    "expected_status": 200,
                    "timeout": 5
                }
            },
            "TPP": {
                "health_check": {
                    "url": "http://localhost:8083/health",
                    "method": "GET",
                    "expected_status": 200,
                    "timeout": 5
                },
                "api_status": {
                    "url": "http://localhost:8083/api/status",
                    "method": "GET",
                    "expected_status": 200,
                    "timeout": 5
                }
            },
            "JFA": {
                "health_check": {
                    "url": "http://localhost:8085/health",
                    "method": "GET",
                    "expected_status": 200,
                    "timeout": 5
                }
            }
        }
        
        # Webserver endpoints
        self.webserver_endpoints = {
            "RLA": {
                "main_server": {
                    "url": "http://localhost:8080/health",
                    "method": "GET",
                    "expected_status": 200,
                    "timeout": 5
                },
                "admin_interface": {
                    "url": "http://localhost:8081/admin/status",
                    "method": "GET",
                    "expected_status": 200,
                    "timeout": 5
                }
            },
            "OCM": {
                "main_server": {
                    "url": "http://localhost:8086/health",
                    "method": "GET",
                    "expected_status": 200,
                    "timeout": 5
                },
                "admin_interface": {
                    "url": "http://localhost:8087/admin/status",
                    "method": "GET",
                    "expected_status": 200,
                    "timeout": 5
                }
            }
        }
        
        self.logger.info("APIConnectivityChecker initialized")
    
    def _get_openai_headers(self) -> Dict[str, str]:
        """Get OpenAI API headers with authentication."""
        # Get API key from config or environment
        api_key = self.config.get('rcm_setting', {}).get('api_configuration', {}).get('openai', {}).get('api_key')
        
        if not api_key or api_key.startswith("sk-proj-YOUR"):
            # Return empty headers if no valid API key
            return {}
        
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    async def test_all_api_connections(self) -> List[APIConnectivityResult]:
        """
        Test all API connections for all services.
        
        Returns:
            List of APIConnectivityResult objects
        """
        self.logger.info("🔌 Testing all API connections")
        results = []
        
        # Test each service's API endpoints
        for service_name, endpoints in self.api_endpoints.items():
            for api_type, endpoint_config in endpoints.items():
                result = await self._test_api_endpoint(service_name, api_type, endpoint_config)
                results.append(result)
                
                # Log result
                if result.success:
                    self.logger.info(f"✅ {service_name} {api_type}: {result.message}")
                else:
                    self.logger.warning(f"❌ {service_name} {api_type}: {result.message}")
        
        # Summary
        successful_tests = sum(1 for r in results if r.success)
        total_tests = len(results)
        self.logger.info(f"API connectivity tests: {successful_tests}/{total_tests} passed")
        
        return results
    
    async def test_webserver_connectivity(self) -> List[APIConnectivityResult]:
        """
        Test webserver connectivity for RLA and OCM.
        
        Returns:
            List of APIConnectivityResult objects
        """
        self.logger.info("🌐 Testing webserver connectivity")
        results = []
        
        # Test each webserver endpoint
        for service_name, endpoints in self.webserver_endpoints.items():
            for server_type, endpoint_config in endpoints.items():
                result = await self._test_api_endpoint(service_name, server_type, endpoint_config)
                results.append(result)
                
                # Log result
                if result.success:
                    self.logger.info(f"✅ {service_name} {server_type}: {result.message}")
                else:
                    self.logger.warning(f"❌ {service_name} {server_type}: {result.message}")
        
        # Summary
        successful_tests = sum(1 for r in results if r.success)
        total_tests = len(results)
        self.logger.info(f"Webserver connectivity tests: {successful_tests}/{total_tests} passed")
        
        return results
    
    async def _test_api_endpoint(self, service_name: str, api_type: str, endpoint_config: Dict[str, Any]) -> APIConnectivityResult:
        """
        Test a specific API endpoint.
        
        Args:
            service_name: Name of the service
            api_type: Type of API being tested
            endpoint_config: Configuration for the endpoint
            
        Returns:
            APIConnectivityResult with test details
        """
        start_time = time.time()
        url = endpoint_config['url']
        method = endpoint_config.get('method', 'GET')
        headers = endpoint_config.get('headers', {})
        expected_status = endpoint_config.get('expected_status', 200)
        timeout = endpoint_config.get('timeout', self.timeout)
        
        try:
            # Create HTTP session
            connector = aiohttp.TCPConnector(limit=10)
            timeout_config = aiohttp.ClientTimeout(total=timeout)
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout_config,
                headers=headers
            ) as session:
                
                # Make request
                async with session.request(method, url) as response:
                    response_time = (time.time() - start_time) * 1000  # Convert to ms
                    
                    # Try to get response data
                    response_data = None
                    try:
                        if response.content_type == 'application/json':
                            response_data = await response.json()
                        else:
                            response_text = await response.text()
                            response_data = {"text": response_text[:200]}  # Truncate for logging
                    except Exception:
                        response_data = {"error": "Could not parse response"}
                    
                    # Check if status matches expected
                    success = response.status == expected_status
                    
                    if success:
                        message = f"Connected successfully ({response.status}) in {response_time:.1f}ms"
                    else:
                        message = f"Unexpected status {response.status}, expected {expected_status}"
                    
                    return APIConnectivityResult(
                        service_name=service_name,
                        api_type=api_type,
                        endpoint=url,
                        success=success,
                        message=message,
                        response_time_ms=response_time,
                        status_code=response.status,
                        response_data=response_data
                    )
        
        except asyncio.TimeoutError:
            response_time = (time.time() - start_time) * 1000
            return APIConnectivityResult(
                service_name=service_name,
                api_type=api_type,
                endpoint=url,
                success=False,
                message=f"Connection timeout after {timeout}s",
                response_time_ms=response_time
            )
        
        except aiohttp.ClientConnectionError as e:
            response_time = (time.time() - start_time) * 1000
            return APIConnectivityResult(
                service_name=service_name,
                api_type=api_type,
                endpoint=url,
                success=False,
                message=f"Connection error: {str(e)}",
                response_time_ms=response_time
            )
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return APIConnectivityResult(
                service_name=service_name,
                api_type=api_type,
                endpoint=url,
                success=False,
                message=f"Unexpected error: {str(e)}",
                response_time_ms=response_time
            )
    
    async def test_specific_api(self, service_name: str, api_type: str) -> APIConnectivityResult:
        """
        Test a specific API for a service.
        
        Args:
            service_name: Name of the service
            api_type: Type of API to test
            
        Returns:
            APIConnectivityResult with test details
        """
        # Check API endpoints
        if service_name in self.api_endpoints:
            endpoint_config = self.api_endpoints[service_name].get(api_type)
            if endpoint_config:
                return await self._test_api_endpoint(service_name, api_type, endpoint_config)
        
        # Check webserver endpoints
        if service_name in self.webserver_endpoints:
            endpoint_config = self.webserver_endpoints[service_name].get(api_type)
            if endpoint_config:
                return await self._test_api_endpoint(service_name, api_type, endpoint_config)
        
        # Not found
        return APIConnectivityResult(
            service_name=service_name,
            api_type=api_type,
            endpoint="unknown",
            success=False,
            message=f"No endpoint configuration found for {service_name}.{api_type}",
            response_time_ms=0
        )
    
    async def test_external_dependencies(self) -> List[APIConnectivityResult]:
        """
        Test connectivity to external dependencies.
        
        Returns:
            List of APIConnectivityResult objects for external services
        """
        self.logger.info("🌍 Testing external dependencies")
        results = []
        
        # Test OpenAI API specifically
        if self._get_openai_headers():
            openai_config = {
                "url": "https://api.openai.com/v1/models",
                "method": "GET",
                "headers": self._get_openai_headers(),
                "expected_status": 200,
                "timeout": 15
            }
            
            result = await self._test_api_endpoint("External", "OpenAI", openai_config)
            results.append(result)
        else:
            # No API key available
            results.append(APIConnectivityResult(
                service_name="External",
                api_type="OpenAI",
                endpoint="https://api.openai.com/v1/models",
                success=False,
                message="No valid OpenAI API key configured",
                response_time_ms=0
            ))
        
        # Test internet connectivity
        internet_config = {
            "url": "https://httpbin.org/get",
            "method": "GET",
            "expected_status": 200,
            "timeout": 10
        }
        
        result = await self._test_api_endpoint("External", "Internet", internet_config)
        results.append(result)
        
        # Summary
        successful_tests = sum(1 for r in results if r.success)
        total_tests = len(results)
        self.logger.info(f"External dependency tests: {successful_tests}/{total_tests} passed")
        
        return results
    
    def get_endpoint_config(self, service_name: str) -> Dict[str, Any]:
        """
        Get endpoint configuration for a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Dictionary with endpoint configurations
        """
        config = {}
        
        if service_name in self.api_endpoints:
            config['api_endpoints'] = self.api_endpoints[service_name]
        
        if service_name in self.webserver_endpoints:
            config['webserver_endpoints'] = self.webserver_endpoints[service_name]
        
        return config
    
    def add_custom_endpoint(self, service_name: str, api_type: str, endpoint_config: Dict[str, Any]):
        """
        Add a custom endpoint for testing.
        
        Args:
            service_name: Name of the service
            api_type: Type of API
            endpoint_config: Configuration for the endpoint
        """
        if service_name not in self.api_endpoints:
            self.api_endpoints[service_name] = {}
        
        self.api_endpoints[service_name][api_type] = endpoint_config
        self.logger.info(f"Added custom endpoint: {service_name}.{api_type}")
    
    def get_connectivity_summary(self, results: List[APIConnectivityResult]) -> Dict[str, Any]:
        """
        Generate a summary of connectivity test results.
        
        Args:
            results: List of APIConnectivityResult objects
            
        Returns:
            Summary dictionary
        """
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r.success)
        failed_tests = total_tests - successful_tests
        
        # Group by service
        by_service = {}
        for result in results:
            if result.service_name not in by_service:
                by_service[result.service_name] = {'total': 0, 'successful': 0}
            
            by_service[result.service_name]['total'] += 1
            if result.success:
                by_service[result.service_name]['successful'] += 1
        
        # Calculate average response time for successful tests
        successful_results = [r for r in results if r.success]
        avg_response_time = (
            sum(r.response_time_ms for r in successful_results) / len(successful_results)
            if successful_results else 0
        )
        
        return {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "failed_tests": failed_tests,
            "success_rate": (successful_tests / total_tests * 100) if total_tests > 0 else 0,
            "average_response_time_ms": avg_response_time,
            "by_service": by_service,
            "failed_endpoints": [
                {"service": r.service_name, "api_type": r.api_type, "endpoint": r.endpoint, "message": r.message}
                for r in results if not r.success
            ]
        }