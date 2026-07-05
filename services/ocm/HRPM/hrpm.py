"""
HTML Report Producer Module (HRPM) for OCM

This module is responsible for HTML templating, report generation, and producing 
formatted HTML output from computation results. It provides templating engine 
integration, custom template management, and dynamic report generation.
"""

import asyncio
import logging
import json
import os
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import jinja2
import html
import base64
import uuid
from pathlib import Path

class ReportType(Enum):
    """Types of HTML reports."""
    STANDARD = "standard"
    DETAILED = "detailed"
    SUMMARY = "summary"
    CUSTOM = "custom"

class TemplateType(Enum):
    """Template categories."""
    GENERIC = "generic"
    ANALYSIS = "analysis"
    SUMMARY = "summary"

@dataclass
class ReportTemplate:
    """HTML report template information."""
    template_id: str
    name: str
    template_type: TemplateType
    file_path: str
    description: str
    version: str
    parameters: List[str]
    created_at: datetime
    updated_at: datetime
    is_active: bool = True

@dataclass
class GeneratedReport:
    """Generated HTML report information."""
    report_id: str
    template_id: str
    report_type: ReportType
    title: str
    content: str
    metadata: Dict[str, Any]
    generated_at: datetime
    file_path: Optional[str] = None
    size_bytes: int = 0

class HTMLReportProducerModule:
    """
    HTML Report Producer Module (HRPM)
    
    Handles HTML report generation:
    - Template management and loading
    - Dynamic content injection
    - Custom styling and formatting
    - Report metadata management
    - Template caching and optimization
    - Multi-language support
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the HRPM module."""
        self.logger = logging.getLogger(__name__)
        self.module_name = "HRPM"
        self.is_active = False
        
        # Configuration
        self.config = config
        self.report_config = config.get('report_generation', {})
        
        # Template settings
        self.templates_dir = self.report_config.get('templates_directory', 'templates')
        self.default_template = self.report_config.get('default_template', 'default_template.html')
        self.output_dir = self.report_config.get('output_directory', 'reports')
        self.cache_templates = self.report_config.get('cache_templates', True)
        
        # Jinja2 environment
        self.jinja_env = None
        
        # Template storage
        self.templates = {}  # template_id -> ReportTemplate
        self.template_cache = {}  # template_id -> compiled template
        
        # Generated reports tracking
        self.generated_reports = {}  # report_id -> GeneratedReport
        
        # Custom filters and functions
        self.custom_filters = {}
        self.custom_functions = {}
        
        # Statistics
        self.stats = {
            'templates_loaded': 0,
            'reports_generated': 0,
            'reports_cached': 0,
            'template_errors': 0,
            'generation_errors': 0,
            'total_size_bytes': 0,
            'start_time': None
        }
        
        # Create directories
        os.makedirs(self.templates_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Register built-in filters and functions
        self._register_builtin_filters()
        self._register_builtin_functions()
        
        self.logger.info(f"{self.module_name} initialized - templates dir: {self.templates_dir}")
    
    async def start(self):
        """Start the HRPM module."""
        try:
            self.is_active = True
            self.stats['start_time'] = datetime.now().isoformat()
            
            # Initialize Jinja2 environment
            self._initialize_jinja_environment()
            
            # Load templates
            await self._load_templates()
            
            # Create default template if none exists
            await self._ensure_default_template()
            
            self.logger.info("HRPM started successfully - HTML report generation ready")
            
        except Exception as e:
            self.logger.error(f"Failed to start HRPM: {e}")
            raise
    
    async def stop(self):
        """Stop the HRPM module gracefully."""
        try:
            self.is_active = False
            self.logger.info("HRPM stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping HRPM: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            # Check if Jinja environment is working
            jinja_healthy = True
            jinja_error = None
            
            if not self.jinja_env:
                jinja_healthy = False
                jinja_error = "Jinja environment not initialized"
            else:
                # Try to render a simple template
                try:
                    test_template = self.jinja_env.from_string("{{ test_var }}")
                    test_result = test_template.render(test_var="test")
                    if test_result != "test":
                        jinja_healthy = False
                        jinja_error = "Template rendering failed"
                except Exception as e:
                    jinja_healthy = False
                    jinja_error = str(e)
            
            is_healthy = self.is_active and jinja_healthy
            
            return {
                'healthy': is_healthy,
                'is_active': self.is_active,
                'jinja_healthy': jinja_healthy,
                'jinja_error': jinja_error,
                'templates_loaded': len(self.templates),
                'module': 'hrpm'
            }
            
        except Exception as e:
            self.logger.error(f"HRPM health check failed: {e}")
            return {
                'healthy': False,
                'error': str(e),
                'module': 'hrpm'
            }
    
    def _initialize_jinja_environment(self):
        """Initialize Jinja2 templating environment."""
        try:
            # Create Jinja2 environment
            loader = jinja2.FileSystemLoader(self.templates_dir)
            self.jinja_env = jinja2.Environment(
                loader=loader,
                autoescape=jinja2.select_autoescape(['html', 'xml']),
                trim_blocks=True,
                lstrip_blocks=True,
                cache_size=100 if self.cache_templates else 0
            )
            
            # Add custom filters
            for name, filter_func in self.custom_filters.items():
                self.jinja_env.filters[name] = filter_func
            
            # Add custom functions
            for name, func in self.custom_functions.items():
                self.jinja_env.globals[name] = func
            
            self.logger.info("Jinja2 environment initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Jinja2 environment: {e}")
            raise
    
    def _register_builtin_filters(self):
        """Register built-in Jinja2 filters."""
        self.custom_filters = {
            'format_datetime': self._filter_format_datetime,
            'format_number': self._filter_format_number,
            'format_currency': self._filter_format_currency,
            'format_percentage': self._filter_format_percentage,
            'truncate_text': self._filter_truncate_text,
            'highlight_keywords': self._filter_highlight_keywords,
            'format_bytes': self._filter_format_bytes,
            'escape_json': self._filter_escape_json,
            'base64_encode': self._filter_base64_encode,
            'capitalize_words': self._filter_capitalize_words,
            'format_duration': self._func_format_duration  # Add as filter too
        }
    
    def _register_builtin_functions(self):
        """Register built-in Jinja2 functions."""
        self.custom_functions = {
            'current_timestamp': self._func_current_timestamp,
            'generate_uuid': self._func_generate_uuid,
            'format_duration': self._func_format_duration,
            'get_file_size': self._func_get_file_size,
            'include_css': self._func_include_css,
            'include_js': self._func_include_js,
            'generate_table_of_contents': self._func_generate_toc,
            'format_list_as_html': self._func_format_list_as_html
        }
    
    async def _load_templates(self):
        """Load all available templates."""
        try:
            templates_path = Path(self.templates_dir)
            
            if not templates_path.exists():
                self.logger.warning(f"Templates directory not found: {self.templates_dir}")
                return
            
            # Scan for template files
            for template_file in templates_path.glob("*.html"):
                try:
                    await self._load_template_file(template_file)
                except Exception as e:
                    self.logger.error(f"Failed to load template {template_file}: {e}")
                    self.stats['template_errors'] += 1
            
            self.logger.info(f"Loaded {len(self.templates)} templates")
            
        except Exception as e:
            self.logger.error(f"Error loading templates: {e}")
    
    async def _load_template_file(self, template_path: Path):
        """Load a single template file."""
        try:
            # Read template content
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract metadata from template comments
            metadata = self._extract_template_metadata(content)
            
            # Create template object
            template_id = metadata.get('id', template_path.stem)
            
            template = ReportTemplate(
                template_id=template_id,
                name=metadata.get('name', template_path.stem),
                template_type=TemplateType(metadata.get('type', 'generic')),
                file_path=str(template_path),
                description=metadata.get('description', ''),
                version=metadata.get('version', '1.0.0'),
                parameters=metadata.get('parameters', []),
                created_at=datetime.fromtimestamp(template_path.stat().st_ctime),
                updated_at=datetime.fromtimestamp(template_path.stat().st_mtime),
                is_active=metadata.get('active', True)
            )
            
            self.templates[template_id] = template
            
            # Cache compiled template if caching is enabled
            if self.cache_templates:
                compiled_template = self.jinja_env.get_template(template_path.name)
                self.template_cache[template_id] = compiled_template
            
            self.stats['templates_loaded'] += 1
            
        except Exception as e:
            self.logger.error(f"Failed to load template file {template_path}: {e}")
            raise
    
    def _extract_template_metadata(self, content: str) -> Dict[str, Any]:
        """Extract metadata from template HTML comments."""
        metadata = {}
        
        try:
            # Look for metadata in HTML comments
            lines = content.split('\n')
            in_metadata = False
            
            for line in lines:
                line = line.strip()
                
                if line.startswith('<!-- TEMPLATE_METADATA'):
                    in_metadata = True
                    continue
                elif line.startswith('-->') and in_metadata:
                    break
                elif in_metadata and ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Parse different value types
                    if key == 'parameters' and value.startswith('['):
                        metadata[key] = json.loads(value)
                    elif key == 'active':
                        metadata[key] = value.lower() == 'true'
                    else:
                        metadata[key] = value
            
        except Exception as e:
            self.logger.error(f"Error extracting template metadata: {e}")
        
        return metadata
    
    async def _ensure_default_template(self):
        """Ensure a default template exists."""
        try:
            default_path = Path(self.templates_dir) / self.default_template
            
            if not default_path.exists():
                # Create a basic default template
                default_content = self._get_default_template_content()
                
                with open(default_path, 'w', encoding='utf-8') as f:
                    f.write(default_content)
                
                # Load the default template
                await self._load_template_file(default_path)
                
                self.logger.info(f"Created default template: {default_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to ensure default template: {e}")
    
    def _get_default_template_content(self) -> str:
        """Get default template HTML content."""
        return '''<!DOCTYPE html>
<!-- TEMPLATE_METADATA
id: default
name: Default OCM Report Template
type: generic
description: Default template for OCM reports
version: 1.0.0
parameters: ["title", "content", "timestamp", "metadata"]
active: true
-->
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title | default('OCM Report') }}</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            border-bottom: 3px solid #2c3e50;
            margin-bottom: 30px;
            padding-bottom: 20px;
        }
        h1 {
            color: #2c3e50;
            margin: 0;
            font-size: 2.2em;
        }
        .meta-info {
            color: #666;
            font-size: 0.9em;
            margin-top: 10px;
        }
        .content {
            margin: 20px 0;
        }
        .section {
            margin: 25px 0;
            padding: 20px;
            border-left: 4px solid #3498db;
            background-color: #f8f9fa;
        }
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            text-align: center;
            color: #888;
            font-size: 0.8em;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #f4f4f4;
            font-weight: bold;
        }
        .highlight {
            background-color: #fff3cd;
            padding: 2px 4px;
            border-radius: 3px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ title | default('OCM Report') }}</h1>
            <div class="meta-info">
                <strong>Generated:</strong> {{ current_timestamp() | format_datetime }}<br>
                {% if metadata and metadata.request_id %}
                <strong>Request ID:</strong> {{ metadata.request_id }}<br>
                {% endif %}
                {% if metadata and metadata.priority %}
                <strong>Priority:</strong> {{ metadata.priority | upper }}<br>
                {% endif %}
            </div>
        </div>
        
        <div class="content">
            {% if content %}
                {{ content | safe }}
            {% else %}
                <div class="section">
                    <h2>Report Content</h2>
                    <p>No content provided for this report.</p>
                </div>
            {% endif %}
        </div>
        
        {% if metadata %}
        <div class="section">
            <h3>Report Metadata</h3>
            <table>
                {% for key, value in metadata.items() %}
                <tr>
                    <td><strong>{{ key | capitalize_words }}</strong></td>
                    <td>{{ value }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
        {% endif %}
        
        <div class="footer">
            <p>Generated by OCM (Output Cache Management) - {{ current_timestamp() | format_datetime }}</p>
        </div>
    </div>
</body>
</html>'''
    
    async def generate_report(self, template_id: str, data: Dict[str, Any], 
                            report_type: ReportType = ReportType.STANDARD,
                            output_file: Optional[str] = None) -> str:
        """Generate HTML report from template and data."""
        try:
            # Validate template exists
            if template_id not in self.templates:
                raise ValueError(f"Template not found: {template_id}")
            
            template_info = self.templates[template_id]
            
            if not template_info.is_active:
                raise ValueError(f"Template is inactive: {template_id}")
            
            # Get compiled template
            if self.cache_templates and template_id in self.template_cache:
                template = self.template_cache[template_id]
            else:
                template_filename = Path(template_info.file_path).name
                template = self.jinja_env.get_template(template_filename)
            
            # Prepare template data
            template_data = {
                'report_type': report_type.value,
                'template_info': asdict(template_info),
                **data
            }
            
            # Render template
            rendered_content = template.render(**template_data)
            
            # Generate report ID
            report_id = str(uuid.uuid4())
            
            # Save to file if output path specified
            file_path = None
            size_bytes = len(rendered_content.encode('utf-8'))
            
            if output_file:
                file_path = os.path.join(self.output_dir, output_file)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(rendered_content)
                size_bytes = os.path.getsize(file_path)
            
            # Store generated report info
            generated_report = GeneratedReport(
                report_id=report_id,
                template_id=template_id,
                report_type=report_type,
                title=data.get('title', f'Report {report_id}'),
                content=rendered_content,
                metadata=data.get('metadata', {}),
                generated_at=datetime.now(),
                file_path=file_path,
                size_bytes=size_bytes
            )
            
            self.generated_reports[report_id] = generated_report
            
            # Update statistics
            self.stats['reports_generated'] += 1
            self.stats['total_size_bytes'] += size_bytes
            
            self.logger.info(f"Generated HTML report: {report_id} (template: {template_id}, size: {size_bytes} bytes)")
            
            return report_id
            
        except Exception as e:
            self.logger.error(f"Failed to generate report with template {template_id}: {e}")
            self.stats['generation_errors'] += 1
            raise
    
    async def generate_computation_report(
        self, computation_data: Dict[str, Any], metadata: Dict[str, Any] = None
    ) -> str:
        """Generate a standard computation report from pipeline results."""
        report_data = {
            "title": metadata.get("title", "Pipeline Report") if metadata else "Pipeline Report",
            "computation_results": computation_data,
            "metadata": metadata or {},
            "content": self._format_computation_content(computation_data),
        }
        return await self.generate_report(
            template_id="default", data=report_data, report_type=ReportType.STANDARD
        )

    async def generate_ofgssc_report(
        self, computation_data: Dict[str, Any], metadata: Dict[str, Any] = None
    ) -> str:
        """Backward-compatible alias for generate_computation_report."""
        return await self.generate_computation_report(computation_data, metadata)
    
    def _format_computation_content(self, computation_data: Dict[str, Any]) -> str:
        """Format computation data into HTML content."""
        try:
            content = '<div class="computation-results">'
            
            # Input parameters section
            if 'input_parameters' in computation_data:
                content += '<div class="section"><h2>Input Parameters</h2>'
                content += '<table>'
                for key, value in computation_data['input_parameters'].items():
                    content += f'<tr><td><strong>{html.escape(str(key))}</strong></td><td>{html.escape(str(value))}</td></tr>'
                content += '</table></div>'
            
            # Results section
            if 'results' in computation_data:
                content += '<div class="section"><h2>Computation Results</h2>'
                results = computation_data['results']
                
                if isinstance(results, dict):
                    content += '<table>'
                    for key, value in results.items():
                        content += f'<tr><td><strong>{html.escape(str(key))}</strong></td><td>{html.escape(str(value))}</td></tr>'
                    content += '</table>'
                else:
                    content += f'<p>{html.escape(str(results))}</p>'
                
                content += '</div>'
            
            # Analysis section
            if 'analysis' in computation_data:
                content += '<div class="section"><h2>Analysis</h2>'
                content += f'<p>{html.escape(str(computation_data["analysis"]))}</p></div>'
            
            # Charts and visualizations (if any)
            if 'charts' in computation_data:
                content += '<div class="section"><h2>Visualizations</h2>'
                for chart in computation_data['charts']:
                    content += f'<div class="chart-container">'
                    content += f'<h3>{html.escape(chart.get("title", "Chart"))}</h3>'
                    if 'image_data' in chart:
                        content += f'<img src="data:image/png;base64,{chart["image_data"]}" alt="{html.escape(chart.get("title", "Chart"))}" style="max-width: 100%; height: auto;">'
                    content += '</div>'
                content += '</div>'
            
            content += '</div>'
            return content
            
        except Exception as e:
            self.logger.error(f"Error formatting computation content: {e}")
            return '<p>Error formatting computation results.</p>'
    
    async def get_report_content(self, report_id: str) -> Optional[str]:
        """Get generated report content by ID."""
        if report_id in self.generated_reports:
            return self.generated_reports[report_id].content
        return None
    
    async def get_report_info(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Get generated report information by ID."""
        if report_id in self.generated_reports:
            return asdict(self.generated_reports[report_id])
        return None
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """List all available templates."""
        return [asdict(template) for template in self.templates.values()]
    
    def list_generated_reports(self, limit: int = None) -> List[Dict[str, Any]]:
        """List generated reports."""
        reports = list(self.generated_reports.values())
        reports.sort(key=lambda r: r.generated_at, reverse=True)
        
        if limit:
            reports = reports[:limit]
        
        return [asdict(report) for report in reports]
    
    def register_custom_filter(self, name: str, filter_func: callable):
        """Register a custom Jinja2 filter."""
        self.custom_filters[name] = filter_func
        if self.jinja_env:
            self.jinja_env.filters[name] = filter_func
        self.logger.info(f"Registered custom filter: {name}")
    
    def register_custom_function(self, name: str, function: callable):
        """Register a custom Jinja2 global function."""
        self.custom_functions[name] = function
        if self.jinja_env:
            self.jinja_env.globals[name] = function
        self.logger.info(f"Registered custom function: {name}")
    
    # Built-in filter functions
    
    def _filter_format_datetime(self, value, format='%Y-%m-%d %H:%M:%S'):
        """Format datetime value."""
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        elif isinstance(value, datetime):
            pass
        else:
            return str(value)
        
        return value.strftime(format)
    
    def _filter_format_number(self, value, decimals=2):
        """Format number with specified decimal places."""
        try:
            return f"{float(value):.{decimals}f}"
        except (ValueError, TypeError):
            return str(value)
    
    def _filter_format_currency(self, value, currency='$'):
        """Format value as currency."""
        try:
            return f"{currency}{float(value):,.2f}"
        except (ValueError, TypeError):
            return str(value)
    
    def _filter_format_percentage(self, value, decimals=1):
        """Format value as percentage."""
        try:
            return f"{float(value):.{decimals}f}%"
        except (ValueError, TypeError):
            return str(value)
    
    def _filter_truncate_text(self, value, length=100, suffix='...'):
        """Truncate text to specified length."""
        text = str(value)
        if len(text) <= length:
            return text
        return text[:length] + suffix
    
    def _filter_highlight_keywords(self, value, keywords):
        """Highlight keywords in text."""
        text = html.escape(str(value))
        if isinstance(keywords, str):
            keywords = [keywords]
        
        for keyword in keywords:
            keyword_escaped = html.escape(keyword)
            text = text.replace(keyword_escaped, f'<span class="highlight">{keyword_escaped}</span>')
        
        return text
    
    def _filter_format_bytes(self, value):
        """Format bytes into human readable format."""
        try:
            bytes_value = int(value)
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if bytes_value < 1024.0:
                    return f"{bytes_value:.1f} {unit}"
                bytes_value /= 1024.0
            return f"{bytes_value:.1f} PB"
        except (ValueError, TypeError):
            return str(value)
    
    def _filter_escape_json(self, value):
        """Escape value for JSON inclusion."""
        return html.escape(json.dumps(value))
    
    def _filter_base64_encode(self, value):
        """Base64 encode a string."""
        return base64.b64encode(str(value).encode()).decode()
    
    def _filter_capitalize_words(self, value):
        """Capitalize each word."""
        return str(value).title().replace('_', ' ')
    
    # Built-in global functions
    
    def _func_current_timestamp(self):
        """Get current timestamp."""
        return datetime.now()
    
    def _func_generate_uuid(self):
        """Generate a new UUID."""
        return str(uuid.uuid4())
    
    def _func_format_duration(self, seconds):
        """Format duration in seconds to human readable format."""
        try:
            seconds = int(seconds)
            hours, remainder = divmod(seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            if hours:
                return f"{hours}h {minutes}m {seconds}s"
            elif minutes:
                return f"{minutes}m {seconds}s"
            else:
                return f"{seconds}s"
        except (ValueError, TypeError):
            return str(seconds)
    
    def _func_get_file_size(self, file_path):
        """Get file size in bytes."""
        try:
            return os.path.getsize(file_path)
        except (OSError, TypeError):
            return 0
    
    def _func_include_css(self, css_content):
        """Include CSS content in style tags."""
        return f'<style>{css_content}</style>'
    
    def _func_include_js(self, js_content):
        """Include JavaScript content in script tags."""
        return f'<script>{js_content}</script>'
    
    def _func_generate_toc(self, content, max_level=3):
        """Generate table of contents from HTML headings."""
        # Simple TOC generation - could be enhanced with proper HTML parsing
        import re
        
        toc = []
        headings = re.findall(r'<h([1-6]).*?>(.*?)</h[1-6]>', content, re.IGNORECASE)
        
        for level, text in headings:
            level = int(level)
            if level <= max_level:
                # Remove HTML tags from heading text
                clean_text = re.sub(r'<[^>]+>', '', text).strip()
                # Generate anchor
                anchor = re.sub(r'[^\w\s-]', '', clean_text.lower().replace(' ', '-'))
                toc.append(f'<li class="toc-level-{level}"><a href="#{anchor}">{clean_text}</a></li>')
        
        if toc:
            return f'<ul class="table-of-contents">{"".join(toc)}</ul>'
        return ''
    
    def _func_format_list_as_html(self, items, list_type='ul'):
        """Format list as HTML ul or ol."""
        if not items:
            return ''
        
        list_items = [f'<li>{html.escape(str(item))}</li>' for item in items]
        return f'<{list_type}>{"".join(list_items)}</{list_type}>'
    
    def get_status(self) -> Dict[str, Any]:
        """Get current HRPM status."""
        return {
            'module': self.module_name,
            'active': self.is_active,
            'templates_loaded': len(self.templates),
            'templates_cached': len(self.template_cache),
            'reports_generated': len(self.generated_reports),
            'custom_filters': len(self.custom_filters),
            'custom_functions': len(self.custom_functions),
            'stats': self.stats.copy()
        } 