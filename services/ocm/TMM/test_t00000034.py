"""
Test O00000034: HRPM Template Customization
Module(s) Tested: HRPM (HTML Report Producer Module)
Description: Test template customization and theming
Test Description:
- Apply custom themes to templates
- Test branding customization
- Verify layout modifications
- Check style customization
- Test template inheritance
- Validate customization persistence
Expected Result: Flexible template customization system
Pass Criteria: Themes applied, branding customized, layouts modified, styles applied
Implementation Notes: Test with various customization scenarios
"""

import asyncio
import json
import sys
import os
import tempfile
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import uuid

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_o00000034():
    test_code = "O00000034"
    test_name = "HRPM Template Customization"
    results = []
    
    try:
        # Import HRPM module
        from HRPM.hrpm import HTMLReportProducerModule, ReportType, TemplateType
        
        # Create temporary test directory
        test_dir = tempfile.mkdtemp(prefix="hrpm_custom_test_")
        templates_dir = os.path.join(test_dir, "templates")
        output_dir = os.path.join(test_dir, "output")
        os.makedirs(templates_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        
        # Step 1: Test HRPM module initialization with customization config
        config = {
            "report_generation": {
                "templates_directory": templates_dir,
                "default_template": "base_template.html",
                "output_directory": output_dir,
                "cache_templates": True
            },
            "template_customization": {
                "enabled": True,
                "theme_support": True,
                "branding_customization": True,
                "layout_modification": True,
                "style_customization": True,
                "template_inheritance": True,
                "customization_persistence": True
            }
        }
        
        hrpm = HTMLReportProducerModule(config)
        await hrpm.start()
        results.append(hrpm.is_active == True)
        results.append(hasattr(hrpm, 'generate_report'))
        results.append(hasattr(hrpm, 'register_custom_filter'))
        results.append(hasattr(hrpm, 'register_custom_function'))
        
        # Step 2: Test custom themes application
        theme_results = []
        
        # Create base template with theme support
        base_template_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{{ title | default('OCM Report') }}</title>
            <style>
                /* Base theme variables */
                :root {
                    --primary-color: {{ theme.primary_color | default('#667eea') }};
                    --secondary-color: {{ theme.secondary_color | default('#764ba2') }};
                    --accent-color: {{ theme.accent_color | default('#f093fb') }};
                    --text-color: {{ theme.text_color | default('#333333') }};
                    --background-color: {{ theme.background_color | default('#ffffff') }};
                    --header-bg: {{ theme.header_bg | default('linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%)') }};
                    --font-family: {{ theme.font_family | default('Arial, sans-serif') }};
                    --border-radius: {{ theme.border_radius | default('8px') }};
                }
                
                body { 
                    font-family: var(--font-family); 
                    margin: 20px; 
                    line-height: 1.6; 
                    color: var(--text-color);
                    background-color: var(--background-color);
                }
                
                .header { 
                    background: var(--header-bg); 
                    color: white; 
                    padding: 20px; 
                    border-radius: var(--border-radius); 
                    margin-bottom: 20px; 
                }
                
                .content { 
                    background: #f8f9fa; 
                    padding: 20px; 
                    border-radius: var(--border-radius); 
                    margin: 20px 0; 
                }
                
                .brand-logo {
                    max-width: 200px;
                    height: auto;
                    margin-bottom: 10px;
                }
                
                .custom-section {
                    border: 2px solid var(--accent-color);
                    padding: 15px;
                    border-radius: var(--border-radius);
                    margin: 15px 0;
                }
            </style>
        </head>
        <body>
            <div class="header">
                {% if branding.logo_url %}
                <img src="{{ branding.logo_url }}" alt="{{ branding.company_name }}" class="brand-logo">
                {% endif %}
                <h1>{{ title | default('OCM Report') }}</h1>
                <p>Generated on: {{ generated_at | format_datetime }}</p>
                {% if branding.company_name %}
                <p>{{ branding.company_name }}</p>
                {% endif %}
            </div>
            
            <div class="content">
                {{ content | safe }}
            </div>
            
            <div class="custom-section">
                <h2>Custom Themed Section</h2>
                <p>This section uses the custom theme colors and styling.</p>
            </div>
        </body>
        </html>
        """
        
        base_template_path = os.path.join(templates_dir, "base_template.html")
        with open(base_template_path, 'w', encoding='utf-8') as f:
            f.write(base_template_content)
        
        theme_results.append(os.path.exists(base_template_path))
        
        # Load templates
        await hrpm._load_templates()
        theme_results.append(len(hrpm.templates) >= 1)
        
        # Step 3: Test branding customization
        branding_results = []
        
        # Test data with branding customization
        branding_data = {
            "title": "Branded Report",
            "generated_at": datetime.now().isoformat(),
            "content": "<p>This is a branded report with custom styling.</p>",
            "theme": {
                "primary_color": "#2c3e50",
                "secondary_color": "#34495e",
                "accent_color": "#e74c3c",
                "text_color": "#2c3e50",
                "background_color": "#ecf0f1",
                "font_family": "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
                "border_radius": "12px"
            },
            "branding": {
                "company_name": "Test Company Inc.",
                "logo_url": "https://example.com/logo.png",
                "tagline": "Innovation in Technology"
            }
        }
        
        # Generate branded report
        branded_report_id = await hrpm.generate_report(
            template_id="base_template",
            data=branding_data,
            report_type=ReportType.CUSTOM
        )
        
        branding_results.append(branded_report_id is not None)
        
        # Get branded report content
        branded_report_content = await hrpm.get_report_content(branded_report_id)
        branding_results.append(branded_report_content is not None)
        
        if branded_report_content:
            # Test branding elements
            branding_results.append("Test Company Inc." in branded_report_content)
            branding_results.append("logo.png" in branded_report_content)
            branding_results.append("#2c3e50" in branded_report_content)  # primary color
            branding_results.append("#e74c3c" in branded_report_content)  # accent color
            branding_results.append("Segoe UI" in branded_report_content)  # font family
        
        # Step 4: Test layout modifications
        layout_results = []
        
        # Create layout-modified template
        layout_template_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{{ title | default('Layout Report') }}</title>
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    margin: 0; 
                    padding: 0; 
                    display: grid;
                    grid-template-areas: 
                        "header header"
                        "sidebar main"
                        "footer footer";
                    grid-template-columns: 250px 1fr;
                    grid-template-rows: auto 1fr auto;
                    min-height: 100vh;
                }
                
                .header { 
                    grid-area: header;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; 
                    padding: 20px; 
                    text-align: center;
                }
                
                .sidebar { 
                    grid-area: sidebar;
                    background: #f8f9fa; 
                    padding: 20px; 
                    border-right: 1px solid #ddd;
                }
                
                .main-content { 
                    grid-area: main;
                    padding: 20px; 
                    background: white;
                }
                
                .footer { 
                    grid-area: footer;
                    background: #333; 
                    color: white; 
                    padding: 15px; 
                    text-align: center;
                }
                
                .sidebar-menu {
                    list-style: none;
                    padding: 0;
                }
                
                .sidebar-menu li {
                    padding: 10px 0;
                    border-bottom: 1px solid #ddd;
                }
                
                .sidebar-menu li:last-child {
                    border-bottom: none;
                }
                
                @media (max-width: 768px) {
                    body {
                        grid-template-areas: 
                            "header"
                            "main"
                            "sidebar"
                            "footer";
                        grid-template-columns: 1fr;
                    }
                }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{{ title | default('Layout Report') }}</h1>
                <p>Generated on: {{ generated_at | format_datetime }}</p>
            </div>
            
            <div class="sidebar">
                <h3>Navigation</h3>
                <ul class="sidebar-menu">
                    {% for item in navigation %}
                    <li>{{ item }}</li>
                    {% endfor %}
                </ul>
                
                <h3>Quick Stats</h3>
                <p>Total Items: {{ stats.total_items | default(0) }}</p>
                <p>Status: {{ stats.status | default('Active') }}</p>
            </div>
            
            <div class="main-content">
                <h2>Main Content</h2>
                {{ content | safe }}
                
                {% if sections %}
                {% for section in sections %}
                <div class="content-section">
                    <h3>{{ section.title }}</h3>
                    <p>{{ section.content }}</p>
                </div>
                {% endfor %}
                {% endif %}
            </div>
            
            <div class="footer">
                <p>&copy; 2024 OCM System. All rights reserved.</p>
            </div>
        </body>
        </html>
        """
        
        layout_template_path = os.path.join(templates_dir, "layout_template.html")
        with open(layout_template_path, 'w', encoding='utf-8') as f:
            f.write(layout_template_content)
        
        layout_results.append(os.path.exists(layout_template_path))
        
        # Reload templates
        await hrpm._load_templates()
        layout_results.append(len(hrpm.templates) >= 2)
        
        # Test layout data
        layout_data = {
            "title": "Layout Modified Report",
            "generated_at": datetime.now().isoformat(),
            "content": "<p>This report uses a custom grid layout with sidebar navigation.</p>",
            "navigation": ["Dashboard", "Reports", "Analytics", "Settings"],
            "stats": {
                "total_items": 42,
                "status": "Active"
            },
            "sections": [
                {
                    "title": "Section 1",
                    "content": "This is the first content section."
                },
                {
                    "title": "Section 2", 
                    "content": "This is the second content section."
                }
            ]
        }
        
        # Generate layout report
        layout_report_id = await hrpm.generate_report(
            template_id="layout_template",
            data=layout_data,
            report_type=ReportType.CUSTOM
        )
        
        layout_results.append(layout_report_id is not None)
        
        # Get layout report content
        layout_report_content = await hrpm.get_report_content(layout_report_id)
        layout_results.append(layout_report_content is not None)
        
        if layout_report_content:
            # Test layout elements
            layout_results.append("grid-template-areas" in layout_report_content)
            layout_results.append("sidebar" in layout_report_content)
            layout_results.append("Dashboard" in layout_report_content)
            layout_results.append("42" in layout_report_content)
            layout_results.append("Section 1" in layout_report_content)
            layout_results.append("@media" in layout_report_content)  # responsive design
        
        # Step 5: Test style customization
        style_results = []
        
        # Create style-customized template
        style_template_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{{ title | default('Styled Report') }}</title>
            <style>
                /* Custom CSS variables */
                :root {
                    --custom-primary: {{ styles.primary_color | default('#3498db') }};
                    --custom-secondary: {{ styles.secondary_color | default('#2ecc71') }};
                    --custom-accent: {{ styles.accent_color | default('#e74c3c') }};
                    --custom-shadow: {{ styles.shadow | default('0 4px 6px rgba(0,0,0,0.1)') }};
                    --custom-border: {{ styles.border_style | default('2px solid var(--custom-primary)') }};
                }
                
                body { 
                    font-family: {{ styles.font_family | default('Arial, sans-serif') }}; 
                    margin: 20px; 
                    line-height: 1.6; 
                    background: {{ styles.background | default('#f9f9f9') }};
                }
                
                .custom-header { 
                    background: var(--custom-primary); 
                    color: white; 
                    padding: 30px; 
                    border-radius: 15px; 
                    margin-bottom: 30px; 
                    box-shadow: var(--custom-shadow);
                    text-align: center;
                }
                
                .custom-content { 
                    background: white; 
                    padding: 25px; 
                    border-radius: 10px; 
                    margin: 20px 0; 
                    border: var(--custom-border);
                    box-shadow: var(--custom-shadow);
                }
                
                .highlight-box {
                    background: var(--custom-secondary);
                    color: white;
                    padding: 15px;
                    border-radius: 8px;
                    margin: 15px 0;
                }
                
                .accent-text {
                    color: var(--custom-accent);
                    font-weight: bold;
                }
                
                .custom-button {
                    background: var(--custom-primary);
                    color: white;
                    padding: 10px 20px;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                    margin: 5px;
                }
                
                .custom-button:hover {
                    background: var(--custom-secondary);
                }
            </style>
        </head>
        <body>
            <div class="custom-header">
                <h1>{{ title | default('Styled Report') }}</h1>
                <p>Generated on: {{ generated_at | format_datetime }}</p>
            </div>
            
            <div class="custom-content">
                <h2>Custom Styled Content</h2>
                {{ content | safe }}
                
                <div class="highlight-box">
                    <h3>Highlighted Information</h3>
                    <p>This section uses custom styling with <span class="accent-text">accent colors</span>.</p>
                </div>
                
                {% if buttons %}
                <div class="button-section">
                    {% for button in buttons %}
                    <button class="custom-button">{{ button.text }}</button>
                    {% endfor %}
                </div>
                {% endif %}
            </div>
        </body>
        </html>
        """
        
        style_template_path = os.path.join(templates_dir, "style_template.html")
        with open(style_template_path, 'w', encoding='utf-8') as f:
            f.write(style_template_content)
        
        style_results.append(os.path.exists(style_template_path))
        
        # Reload templates
        await hrpm._load_templates()
        style_results.append(len(hrpm.templates) >= 3)
        
        # Test style data
        style_data = {
            "title": "Custom Styled Report",
            "generated_at": datetime.now().isoformat(),
            "content": "<p>This report demonstrates custom styling capabilities.</p>",
            "styles": {
                "primary_color": "#9b59b6",
                "secondary_color": "#f39c12",
                "accent_color": "#e67e22",
                "font_family": "'Courier New', monospace",
                "background": "#2c3e50",
                "shadow": "0 8px 16px rgba(0,0,0,0.2)",
                "border_style": "3px dashed #9b59b6"
            },
            "buttons": [
                {"text": "Action 1"},
                {"text": "Action 2"},
                {"text": "Action 3"}
            ]
        }
        
        # Generate styled report
        styled_report_id = await hrpm.generate_report(
            template_id="style_template",
            data=style_data,
            report_type=ReportType.CUSTOM
        )
        
        style_results.append(styled_report_id is not None)
        
        # Get styled report content
        styled_report_content = await hrpm.get_report_content(styled_report_id)
        style_results.append(styled_report_content is not None)
        
        if styled_report_content:
            # Test style elements
            style_results.append("#9b59b6" in styled_report_content)  # primary color
            style_results.append("#f39c12" in styled_report_content)  # secondary color
            style_results.append("Courier New" in styled_report_content)  # font family
            style_results.append("Action 1" in styled_report_content)  # buttons
            style_results.append("dashed" in styled_report_content)  # border style
            style_results.append("0 8px 16px" in styled_report_content)  # shadow
        
        # Step 6: Test template inheritance
        inheritance_results = []
        
        # Create parent template
        parent_template_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{% block title %}{{ title | default('Parent Template') }}{% endblock %}</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .parent-header { background: #3498db; color: white; padding: 20px; border-radius: 8px; }
                .parent-content { background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }
                {% block custom_styles %}{% endblock %}
            </style>
        </head>
        <body>
            <div class="parent-header">
                <h1>{% block header %}{{ title | default('Parent Template') }}{% endblock %}</h1>
                <p>Generated on: {{ generated_at | format_datetime }}</p>
            </div>
            
            <div class="parent-content">
                {% block content %}
                <p>Default content from parent template.</p>
                {% endblock %}
            </div>
            
            {% block additional_content %}{% endblock %}
        </body>
        </html>
        """
        
        parent_template_path = os.path.join(templates_dir, "parent_template.html")
        with open(parent_template_path, 'w', encoding='utf-8') as f:
            f.write(parent_template_content)
        
        # Create child template
        child_template_content = """
        {% extends "parent_template.html" %}
        
        {% block title %}Child Template - {{ title | default('Child') }}{% endblock %}
        
        {% block custom_styles %}
        .child-specific { background: #e74c3c; color: white; padding: 15px; border-radius: 8px; margin: 15px 0; }
        .child-header { background: #2ecc71; color: white; padding: 20px; border-radius: 8px; }
        {% endblock %}
        
        {% block header %}
        <div class="child-header">
            <h1>{{ title | default('Child Template') }}</h1>
            <p>This is a child template with custom styling.</p>
        </div>
        {% endblock %}
        
        {% block content %}
        <h2>Child Content</h2>
        <p>{{ content | default('Content from child template.') }}</p>
        
        <div class="child-specific">
            <h3>Child-Specific Section</h3>
            <p>This section is specific to the child template.</p>
        </div>
        {% endblock %}
        
        {% block additional_content %}
        <div class="parent-content">
            <h2>Additional Child Content</h2>
            <p>This content extends the parent template.</p>
        </div>
        {% endblock %}
        """
        
        child_template_path = os.path.join(templates_dir, "child_template.html")
        with open(child_template_path, 'w', encoding='utf-8') as f:
            f.write(child_template_content)
        
        inheritance_results.append(os.path.exists(parent_template_path))
        inheritance_results.append(os.path.exists(child_template_path))
        
        # Reload templates
        await hrpm._load_templates()
        inheritance_results.append(len(hrpm.templates) >= 5)
        
        # Test inheritance data
        inheritance_data = {
            "title": "Inheritance Test Report",
            "generated_at": datetime.now().isoformat(),
            "content": "This content is passed to the child template."
        }
        
        # Generate inherited report
        inherited_report_id = await hrpm.generate_report(
            template_id="child_template",
            data=inheritance_data,
            report_type=ReportType.CUSTOM
        )
        
        inheritance_results.append(inherited_report_id is not None)
        
        # Get inherited report content
        inherited_report_content = await hrpm.get_report_content(inherited_report_id)
        inheritance_results.append(inherited_report_content is not None)
        
        if inherited_report_content:
            # Test inheritance elements
            inheritance_results.append("Child Template" in inherited_report_content)
            inheritance_results.append("child-specific" in inherited_report_content)
            inheritance_results.append("child-header" in inherited_report_content)
            inheritance_results.append("Parent Template" in inherited_report_content)
            inheritance_results.append("Additional Child Content" in inherited_report_content)
        
        # Step 7: Test customization persistence
        persistence_results = []
        
        # Test that customizations persist across multiple generations
        persistence_data = {
            "title": "Persistence Test Report",
            "generated_at": datetime.now().isoformat(),
            "content": "Testing customization persistence.",
            "theme": {
                "primary_color": "#8e44ad",
                "secondary_color": "#16a085",
                "accent_color": "#f1c40f"
            },
            "branding": {
                "company_name": "Persistence Test Corp.",
                "logo_url": "https://example.com/persistent-logo.png"
            }
        }
        
        # Generate multiple reports with same customization
        persistent_reports = []
        for i in range(3):
            report_id = await hrpm.generate_report(
                template_id="base_template",
                data=persistence_data,
                report_type=ReportType.CUSTOM
            )
            persistent_reports.append(report_id)
        
        persistence_results.append(len(persistent_reports) == 3)
        persistence_results.append(all(report_id is not None for report_id in persistent_reports))
        
        # Verify persistence across reports
        for report_id in persistent_reports:
            report_content = await hrpm.get_report_content(report_id)
            if report_content:
                persistence_results.append("#8e44ad" in report_content)  # primary color
                persistence_results.append("Persistence Test Corp." in report_content)  # company name
                persistence_results.append("persistent-logo.png" in report_content)  # logo
        
        # Step 8: Test customization performance
        performance_results = []
        
        # Test customization performance
        start_time = datetime.now()
        
        # Generate multiple customized reports
        custom_reports = []
        for i in range(5):
            custom_data = {
                "title": f"Performance Test Report {i+1}",
                "generated_at": datetime.now().isoformat(),
                "content": f"Performance test content {i+1}.",
                "theme": {
                    "primary_color": f"#{i*50:06x}",
                    "secondary_color": f"#{i*30:06x}",
                    "accent_color": f"#{i*20:06x}"
                },
                "branding": {
                    "company_name": f"Company {i+1}",
                    "logo_url": f"https://example.com/logo{i+1}.png"
                }
            }
            
            report_id = await hrpm.generate_report(
                template_id="base_template",
                data=custom_data,
                report_type=ReportType.CUSTOM
            )
            custom_reports.append(report_id)
        
        end_time = datetime.now()
        generation_time = (end_time - start_time).total_seconds()
        
        performance_results.append(len(custom_reports) == 5)
        performance_results.append(all(report_id is not None for report_id in custom_reports))
        performance_results.append(generation_time < 15.0)  # Should complete within 15 seconds
        
        # Step 9: Test customization error handling
        error_results = []
        
        # Test with invalid theme data
        invalid_theme_data = {
            "title": "Invalid Theme Test",
            "generated_at": datetime.now().isoformat(),
            "content": "Testing invalid theme handling.",
            "theme": None  # Invalid theme
        }
        
        try:
            invalid_theme_report_id = await hrpm.generate_report(
                template_id="base_template",
                data=invalid_theme_data,
                report_type=ReportType.CUSTOM
            )
            error_results.append(invalid_theme_report_id is not None)  # Should still generate
        except Exception:
            error_results.append(True)  # Should handle error gracefully
        
        # Test with missing template
        try:
            missing_template_report_id = await hrpm.generate_report(
                template_id="non_existent_custom_template",
                data=persistence_data,
                report_type=ReportType.CUSTOM
            )
            error_results.append(missing_template_report_id is None)
        except Exception:
            error_results.append(True)
        
        # Test template listing
        template_list = hrpm.list_templates()
        error_results.append(isinstance(template_list, list))
        error_results.append(len(template_list) >= 5)  # Should have at least 5 templates
        
        # Step 10: Test customization validation
        validation_results = []
        
        # Test customization configuration validation
        validation_results.append(hrpm.is_active == True)
        validation_results.append(len(hrpm.templates) >= 5)
        
        # Test template information
        if template_list:
            template_info = template_list[0]
            validation_results.append(isinstance(template_info, dict))
            validation_results.append("template_id" in template_info)
            validation_results.append("name" in template_info)
        
        # Aggregate all results
        all_results = (
            results + 
            theme_results + 
            branding_results + 
            layout_results + 
            style_results + 
            inheritance_results + 
            persistence_results + 
            performance_results + 
            error_results + 
            validation_results
        )
        
        # Calculate pass rate
        passed_tests = sum(all_results)
        total_tests = len(all_results)
        pass_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        # Cleanup
        await hrpm.stop()
        
        # Clean up test directory
        try:
            import shutil
            shutil.rmtree(test_dir)
        except Exception:
            pass  # Ignore cleanup errors
        
        return {
            "test_code": test_code,
            "test_name": test_name,
            "status": "PASSED" if pass_rate >= 90 else "FAILED",
            "pass_rate": pass_rate,
            "passed_tests": passed_tests,
            "total_tests": total_tests,
            "results": {
                "module_initialization": results,
                "custom_themes": theme_results,
                "branding_customization": branding_results,
                "layout_modifications": layout_results,
                "style_customization": style_results,
                "template_inheritance": inheritance_results,
                "customization_persistence": persistence_results,
                "customization_performance": performance_results,
                "error_handling": error_results,
                "customization_validation": validation_results
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "test_code": test_code,
            "test_name": test_name,
            "status": "ERROR",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

async def main():
    """Main test execution function."""
    result = await test_o00000034()
    print(json.dumps(result, indent=2))
    return result

if __name__ == "__main__":
    asyncio.run(main())