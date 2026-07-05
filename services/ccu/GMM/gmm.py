"""
Graphical Monitoring Module (GMM)

This module provides a real-time graphical user interface similar to the glances tool
for system observability. It visualizes data from CMM, CEIM, and SRMM modules,
displaying service logs, real-time request statistics, microservice health,
error statuses, and system resource metrics.

Key Responsibilities:
- Real-time web dashboard accessible on configurable port
- System resource visualization (CPU, memory, disk, network)
- Microservice health monitoring display
- Request statistics and throughput metrics
- Error logs and alert visualization
- Interactive controls for system management
- Historical data charts and trends
"""

import asyncio
import logging
import json
import sqlite3
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import threading
import time
import websockets
from aiohttp import web, WSMsgType
import aiohttp_cors
import jinja2
import aiofiles
import weakref


class DashboardStatus(Enum):
    """Dashboard status."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"


class GraphicalMonitoringModule:
    """
    Graphical Monitoring Module (GMM)
    
    Provides real-time web dashboard for system monitoring and management.
    """
    
    def __init__(self):
        """Initialize the GMM module."""
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.dashboard_port = 11489
        self.dashboard_host = "0.0.0.0"
        self.dashboard_title = "CCU System Dashboard"
        self.refresh_interval = 5  # seconds
        self.max_data_points = 1000
        
        # Dashboard state
        self.status = DashboardStatus.STOPPED
        self.app = None
        self.runner = None
        self.site = None
        self.websocket_connections = weakref.WeakSet()
        
        # Data storage
        self.current_data = {
            'system_resources': {},
            'service_health': {},
            'request_statistics': {},
            'error_logs': [],
            'alerts': [],
            'performance_metrics': {}
        }
        
        # Data history for charts
        self.data_history = {
            'cpu_usage': [],
            'memory_usage': [],
            'disk_usage': [],
            'network_latency': [],
            'request_rate': [],
            'error_rate': []
        }
        
        # Statistics
        self.stats = {
            'dashboard_start_time': None,
            'total_page_views': 0,
            'active_websocket_connections': 0,
            'data_updates_sent': 0,
            'last_update': None
        }
        
        # Templates and static files
        self.templates_dir = Path(__file__).parent / 'templates'
        self.static_dir = Path(__file__).parent / 'static'
        
        # Initialize templates
        self.init_templates()
        
        self.logger.info("GMM module initialized")
    
    def init_templates(self):
        """Initialize Jinja2 templates."""
        try:
            # Create templates directory if it doesn't exist
            self.templates_dir.mkdir(exist_ok=True)
            self.static_dir.mkdir(exist_ok=True)
            
            # Create dashboard template
            self.create_dashboard_template()
            self.create_static_files()
            
            # Initialize Jinja2 environment
            self.template_env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(str(self.templates_dir)),
                autoescape=jinja2.select_autoescape(['html', 'xml'])
            )
            
            self.logger.info("Templates initialized")
            
        except Exception as e:
            self.logger.error(f"Error initializing templates: {e}")
    
    def create_dashboard_template(self):
        """Create the main dashboard HTML template."""
        template_content = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ dashboard_title }}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #1a1a1a;
            color: #ffffff;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background-color: #2d2d2d;
            border-radius: 10px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background-color: #2d2d2d;
            padding: 20px;
            border-radius: 10px;
            border: 1px solid #404040;
        }
        .card h2 {
            margin-top: 0;
            color: #4CAF50;
        }
        .metric {
            display: flex;
            justify-content: space-between;
            margin: 10px 0;
            padding: 10px;
            background-color: #404040;
            border-radius: 5px;
        }
        .metric-value {
            font-weight: bold;
        }
        .status-ok { color: #4CAF50; }
        .status-warning { color: #FF9800; }
        .status-critical { color: #F44336; }
        .chart-container {
            position: relative;
            height: 300px;
            margin: 20px 0;
        }
        .log-container {
            max-height: 400px;
            overflow-y: auto;
            background-color: #1a1a1a;
            padding: 10px;
            border-radius: 5px;
            font-family: monospace;
            font-size: 12px;
        }
        .log-entry {
            margin: 5px 0;
            padding: 5px;
            border-left: 3px solid #4CAF50;
        }
        .log-error { border-left-color: #F44336; }
        .log-warning { border-left-color: #FF9800; }
        .controls {
            text-align: center;
            margin: 20px 0;
        }
        button {
            background-color: #4CAF50;
            color: white;
            border: none;
            padding: 10px 20px;
            margin: 0 10px;
            border-radius: 5px;
            cursor: pointer;
        }
        button:hover {
            background-color: #45a049;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            padding: 20px;
            background-color: #2d2d2d;
            border-radius: 10px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ dashboard_title }}</h1>
        <p>Real-time System Monitoring Dashboard</p>
        <p>Last Updated: <span id="last-updated">{{ current_time }}</span></p>
    </div>
    
    <div class="grid">
        <div class="card">
            <h2>System Resources</h2>
            <div class="metric">
                <span>CPU Usage</span>
                <span class="metric-value" id="cpu-usage">0%</span>
            </div>
            <div class="metric">
                <span>Memory Usage</span>
                <span class="metric-value" id="memory-usage">0%</span>
            </div>
            <div class="metric">
                <span>Disk Usage</span>
                <span class="metric-value" id="disk-usage">0%</span>
            </div>
            <div class="metric">
                <span>Network Latency</span>
                <span class="metric-value" id="network-latency">0ms</span>
            </div>
        </div>
        
        <div class="card">
            <h2>Service Health</h2>
            <div id="service-health-container">
                <!-- Service health metrics will be populated here -->
            </div>
        </div>
        
        <div class="card">
            <h2>Request Statistics</h2>
            <div class="metric">
                <span>Total Requests</span>
                <span class="metric-value" id="total-requests">0</span>
            </div>
            <div class="metric">
                <span>Active Requests</span>
                <span class="metric-value" id="active-requests">0</span>
            </div>
            <div class="metric">
                <span>Completed Requests</span>
                <span class="metric-value" id="completed-requests">0</span>
            </div>
            <div class="metric">
                <span>Failed Requests</span>
                <span class="metric-value" id="failed-requests">0</span>
            </div>
        </div>
        
        <div class="card">
            <h2>Recent Alerts</h2>
            <div id="alerts-container">
                <!-- Alerts will be populated here -->
            </div>
        </div>
    </div>
    
    <div class="card">
        <h2>System Performance Charts</h2>
        <div class="chart-container">
            <canvas id="performance-chart"></canvas>
        </div>
    </div>
    
    <div class="card">
        <h2>System Logs</h2>
        <div class="log-container" id="log-container">
            <!-- Logs will be populated here -->
        </div>
    </div>
    
    <div class="controls">
        <button onclick="refreshData()">Refresh Data</button>
        <button onclick="clearLogs()">Clear Logs</button>
        <button onclick="exportData()">Export Data</button>
    </div>
    
    <div class="footer">
        <p>CCU Dashboard - Real-time System Monitoring</p>
        <p>Refresh Rate: {{ refresh_interval }}s | Max Data Points: {{ max_data_points }}</p>
    </div>
    
    <script>
        // WebSocket connection
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(protocol + '//' + window.location.host + '/ws');
        
        // Chart setup
        const ctx = document.getElementById('performance-chart').getContext('2d');
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'CPU Usage (%)',
                    data: [],
                    borderColor: '#FF6384',
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    fill: false
                }, {
                    label: 'Memory Usage (%)',
                    data: [],
                    borderColor: '#36A2EB',
                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                    fill: false
                }, {
                    label: 'Network Latency (ms)',
                    data: [],
                    borderColor: '#FFCE56',
                    backgroundColor: 'rgba(255, 206, 86, 0.2)',
                    fill: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Real-time System Performance'
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'minute'
                        }
                    },
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
        
        // WebSocket event handlers
        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            updateDashboard(data);
        };
        
        ws.onopen = function() {
            console.log('WebSocket connected');
        };
        
        ws.onclose = function() {
            console.log('WebSocket disconnected');
            setTimeout(function() {
                location.reload();
            }, 5000);
        };
        
        // Update dashboard with new data
        function updateDashboard(data) {
            // Update system resources
            if (data.system_resources) {
                document.getElementById('cpu-usage').textContent = data.system_resources.cpu_usage + '%';
                document.getElementById('memory-usage').textContent = data.system_resources.memory_usage + '%';
                document.getElementById('disk-usage').textContent = data.system_resources.disk_usage + '%';
                document.getElementById('network-latency').textContent = data.system_resources.network_latency + 'ms';
            }
            
            // Update request statistics
            if (data.request_statistics) {
                document.getElementById('total-requests').textContent = data.request_statistics.total_requests;
                document.getElementById('active-requests').textContent = data.request_statistics.active_requests;
                document.getElementById('completed-requests').textContent = data.request_statistics.completed_requests;
                document.getElementById('failed-requests').textContent = data.request_statistics.failed_requests;
            }
            
            // Update service health
            if (data.service_health) {
                updateServiceHealth(data.service_health);
            }
            
            // Update alerts
            if (data.alerts) {
                updateAlerts(data.alerts);
            }
            
            // Update logs
            if (data.logs) {
                updateLogs(data.logs);
            }
            
            // Update charts
            if (data.performance_metrics) {
                updateChart(data.performance_metrics);
            }
            
            // Update timestamp
            document.getElementById('last-updated').textContent = new Date().toLocaleString();
        }
        
        function updateServiceHealth(services) {
            const container = document.getElementById('service-health-container');
            container.innerHTML = '';
            
            for (const [service, health] of Object.entries(services)) {
                const div = document.createElement('div');
                div.className = 'metric';
                
                const statusClass = health.status === 'active' ? 'status-ok' : 
                                   health.status === 'error' ? 'status-critical' : 'status-warning';
                
                div.innerHTML = `
                    <span>${service}</span>
                    <span class="metric-value ${statusClass}">${health.status}</span>
                `;
                container.appendChild(div);
            }
        }
        
        function updateAlerts(alerts) {
            const container = document.getElementById('alerts-container');
            container.innerHTML = '';
            
            alerts.slice(0, 5).forEach(alert => {
                const div = document.createElement('div');
                div.className = 'metric';
                
                const statusClass = alert.level === 'critical' ? 'status-critical' : 'status-warning';
                
                div.innerHTML = `
                    <span>${alert.message}</span>
                    <span class="metric-value ${statusClass}">${alert.level}</span>
                `;
                container.appendChild(div);
            });
        }
        
        function updateLogs(logs) {
            const container = document.getElementById('log-container');
            
            logs.forEach(log => {
                const div = document.createElement('div');
                div.className = 'log-entry';
                
                if (log.level === 'ERROR') {
                    div.className += ' log-error';
                } else if (log.level === 'WARNING') {
                    div.className += ' log-warning';
                }
                
                div.innerHTML = `
                    <span>[${log.timestamp}] ${log.level}: ${log.message}</span>
                `;
                container.appendChild(div);
            });
            
            // Keep only last 100 log entries
            while (container.children.length > 100) {
                container.removeChild(container.firstChild);
            }
            
            // Scroll to bottom
            container.scrollTop = container.scrollHeight;
        }
        
        function updateChart(metrics) {
            const now = new Date();
            
            // Add new data point
            chart.data.labels.push(now);
            chart.data.datasets[0].data.push(metrics.cpu_usage);
            chart.data.datasets[1].data.push(metrics.memory_usage);
            chart.data.datasets[2].data.push(metrics.network_latency);
            
            // Keep only last 50 data points
            if (chart.data.labels.length > 50) {
                chart.data.labels.shift();
                chart.data.datasets.forEach(dataset => {
                    dataset.data.shift();
                });
            }
            
            chart.update('none');
        }
        
        // Control functions
        function refreshData() {
            ws.send(JSON.stringify({action: 'refresh'}));
        }
        
        function clearLogs() {
            document.getElementById('log-container').innerHTML = '';
        }
        
        function exportData() {
            ws.send(JSON.stringify({action: 'export'}));
        }
    </script>
</body>
</html>
        '''
        
        template_file = self.templates_dir / 'dashboard.html'
        with open(template_file, 'w') as f:
            f.write(template_content)
    
    def create_static_files(self):
        """Create static CSS and JS files."""
        # This would normally contain separate CSS and JS files
        # For simplicity, we're including them inline in the template
        pass
    
    async def start(self):
        """Start the dashboard."""
        try:
            self.logger.info("Starting GMM dashboard...")
            self.status = DashboardStatus.STARTING
            
            # Create aiohttp application
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
            self.app.router.add_get('/', self.dashboard_handler)
            self.app.router.add_get('/ws', self.websocket_handler)
            self.app.router.add_get('/api/status', self.api_status_handler)
            self.app.router.add_get('/api/metrics', self.api_metrics_handler)
            
            # Add CORS to all routes
            for route in list(self.app.router.routes()):
                cors.add(route)
            
            # Start the server
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            self.site = web.TCPSite(
                self.runner,
                self.dashboard_host,
                self.dashboard_port
            )
            await self.site.start()
            
            self.status = DashboardStatus.RUNNING
            self.stats['dashboard_start_time'] = datetime.now()
            
            # Start data broadcasting
            asyncio.create_task(self.broadcast_data())
            
            self.logger.info(f"GMM dashboard started on http://{self.dashboard_host}:{self.dashboard_port}")
            
        except Exception as e:
            self.logger.error(f"Failed to start GMM dashboard: {e}")
            self.status = DashboardStatus.ERROR
            raise
    
    async def stop(self):
        """Stop the dashboard."""
        try:
            self.logger.info("Stopping GMM dashboard...")
            
            # Close all websocket connections
            for ws in self.websocket_connections:
                await ws.close()
            
            # Stop the server
            if self.site:
                await self.site.stop()
            
            if self.runner:
                await self.runner.cleanup()
            
            self.status = DashboardStatus.STOPPED
            
            self.logger.info("GMM dashboard stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to stop GMM dashboard: {e}")
            raise
    
    async def dashboard_handler(self, request):
        """Handle dashboard page requests."""
        try:
            self.stats['total_page_views'] += 1
            
            template = self.template_env.get_template('dashboard.html')
            html = template.render(
                dashboard_title=self.dashboard_title,
                current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                refresh_interval=self.refresh_interval,
                max_data_points=self.max_data_points
            )
            
            return web.Response(text=html, content_type='text/html')
            
        except Exception as e:
            self.logger.error(f"Error handling dashboard request: {e}")
            return web.Response(text="Dashboard Error", status=500)
    
    async def websocket_handler(self, request):
        """Handle WebSocket connections."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.websocket_connections.add(ws)
        self.stats['active_websocket_connections'] = len(self.websocket_connections)
        
        try:
            # Send initial data
            await ws.send_str(json.dumps(self.current_data))
            
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self.handle_websocket_message(ws, data)
                    except json.JSONDecodeError:
                        await ws.send_str(json.dumps({'error': 'Invalid JSON'}))
                elif msg.type == WSMsgType.ERROR:
                    self.logger.error(f'WebSocket error: {ws.exception()}')
                    break
                    
        except Exception as e:
            self.logger.error(f"WebSocket error: {e}")
        finally:
            self.websocket_connections.discard(ws)
            self.stats['active_websocket_connections'] = len(self.websocket_connections)
        
        return ws
    
    async def handle_websocket_message(self, ws, data):
        """Handle WebSocket messages from clients."""
        try:
            action = data.get('action')
            
            if action == 'refresh':
                await ws.send_str(json.dumps(self.current_data))
            elif action == 'export':
                export_data = {
                    'timestamp': datetime.now().isoformat(),
                    'current_data': self.current_data,
                    'data_history': self.data_history,
                    'stats': self.stats
                }
                await ws.send_str(json.dumps({'export': export_data}))
            else:
                await ws.send_str(json.dumps({'error': f'Unknown action: {action}'}))
                
        except Exception as e:
            self.logger.error(f"Error handling WebSocket message: {e}")
            await ws.send_str(json.dumps({'error': 'Internal server error'}))
    
    async def api_status_handler(self, request):
        """Handle API status requests."""
        try:
            status_data = {
                'dashboard_status': self.status.value,
                'stats': self.stats,
                'active_connections': len(self.websocket_connections)
            }
            
            return web.json_response(status_data)
            
        except Exception as e:
            self.logger.error(f"Error handling API status request: {e}")
            return web.json_response({'error': 'Internal server error'}, status=500)
    
    async def api_metrics_handler(self, request):
        """Handle API metrics requests."""
        try:
            return web.json_response(self.current_data)
            
        except Exception as e:
            self.logger.error(f"Error handling API metrics request: {e}")
            return web.json_response({'error': 'Internal server error'}, status=500)
    
    async def broadcast_data(self):
        """Broadcast data to all connected WebSocket clients."""
        while self.status == DashboardStatus.RUNNING:
            try:
                if self.websocket_connections:
                    message = json.dumps(self.current_data)
                    
                    # Send to all connected clients
                    for ws in list(self.websocket_connections):
                        try:
                            await ws.send_str(message)
                        except Exception as e:
                            self.logger.error(f"Error sending data to WebSocket client: {e}")
                            self.websocket_connections.discard(ws)
                    
                    self.stats['data_updates_sent'] += 1
                    self.stats['last_update'] = datetime.now()
                
                await asyncio.sleep(self.refresh_interval)
                
            except Exception as e:
                self.logger.error(f"Error in broadcast loop: {e}")
                await asyncio.sleep(self.refresh_interval)
    
    # Data update methods
    async def update_system_resources(self, resources: Dict[str, Any]):
        """Update system resources data."""
        self.current_data['system_resources'] = resources
        
        # Update history
        if 'cpu_usage' in resources:
            self.data_history['cpu_usage'].append({
                'timestamp': datetime.now().isoformat(),
                'value': resources['cpu_usage']
            })
            if len(self.data_history['cpu_usage']) > self.max_data_points:
                self.data_history['cpu_usage'].pop(0)
        
        if 'memory_usage' in resources:
            self.data_history['memory_usage'].append({
                'timestamp': datetime.now().isoformat(),
                'value': resources['memory_usage']
            })
            if len(self.data_history['memory_usage']) > self.max_data_points:
                self.data_history['memory_usage'].pop(0)
    
    async def update_service_health(self, services: Dict[str, Any]):
        """Update service health data."""
        self.current_data['service_health'] = services
    
    async def update_request_statistics(self, stats: Dict[str, Any]):
        """Update request statistics."""
        self.current_data['request_statistics'] = stats
        
        # Update request rate history
        if 'total_requests' in stats:
            self.data_history['request_rate'].append({
                'timestamp': datetime.now().isoformat(),
                'value': stats['total_requests']
            })
            if len(self.data_history['request_rate']) > self.max_data_points:
                self.data_history['request_rate'].pop(0)
    
    async def update_error_logs(self, logs: List[Dict[str, Any]]):
        """Update error logs."""
        self.current_data['error_logs'] = logs
    
    async def update_alerts(self, alerts: List[Dict[str, Any]]):
        """Update alerts."""
        self.current_data['alerts'] = alerts
    
    async def update_performance_metrics(self, metrics: Dict[str, Any]):
        """Update performance metrics."""
        self.current_data['performance_metrics'] = metrics
    
    async def add_log_entry(self, level: str, message: str, timestamp: datetime = None):
        """Add a log entry to the dashboard."""
        if timestamp is None:
            timestamp = datetime.now()
        
        log_entry = {
            'timestamp': timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            'level': level,
            'message': message
        }
        
        if 'logs' not in self.current_data:
            self.current_data['logs'] = []
        
        self.current_data['logs'].append(log_entry)
        
        # Keep only last 100 log entries
        if len(self.current_data['logs']) > 100:
            self.current_data['logs'].pop(0)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the GMM module."""
        return {
            'module': 'GMM',
            'dashboard_status': self.status.value,
            'dashboard_url': f"http://{self.dashboard_host}:{self.dashboard_port}",
            'active_connections': len(self.websocket_connections),
            'stats': self.stats
        }
    
    def is_running(self) -> bool:
        """Check if dashboard is running."""
        return self.status == DashboardStatus.RUNNING
    
    def set_configuration(self, config: Dict[str, Any]):
        """Update configuration."""
        if 'dashboard_port' in config:
            self.dashboard_port = config['dashboard_port']
        
        if 'dashboard_host' in config:
            self.dashboard_host = config['dashboard_host']
        
        if 'dashboard_title' in config:
            self.dashboard_title = config['dashboard_title']
        
        if 'refresh_interval' in config:
            self.refresh_interval = config['refresh_interval']
        
        if 'max_data_points' in config:
            self.max_data_points = config['max_data_points']
        
        self.logger.info(f"Updated GMM configuration: {config}")
    
    async def start_dashboard(self):
        """Alias for start method."""
        await self.start() 