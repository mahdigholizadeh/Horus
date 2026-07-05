"""
Test O00000032: HRPM HTML Report Generation
Module(s) Tested: HRPM (HTML Report Producer Module)
Description: Test HTML report generation with Jinja2 templating
Test Description:
- Generate HTML reports from templates
- Test data binding and rendering
- Verify template variable substitution
- Check HTML validation
- Test report customization
- Validate report formatting
Expected Result: High-quality HTML report generation
Pass Criteria: Reports generated, data bound, variables substituted, HTML valid
Implementation Notes: Test with various data types and templates
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

async def test_o00000032():
    test_code = "O00000032"
    test_name = "HRPM HTML Report Generation"
    results = []
    
    try:
        # Import HRPM module
        from HRPM.hrpm import HTMLReportProducerModule, ReportType, TemplateType
        
        # Create temporary test directory
        test_dir = tempfile.mkdtemp(prefix="hrpm_gen_test_")
        templates_dir = os.path.join(test_dir, "templates")
        output_dir = os.path.join(test_dir, "output")
        os.makedirs(templates_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        
        # Step 1: Test HRPM module initialization with report generation config
        config = {
            "report_generation": {
                "templates_directory": templates_dir,
                "default_template": "default_template.html",
                "output_directory": output_dir,
                "cache_templates": True
            },
            "html_generation": {
                "enabled": True,
                "jinja2_environment": True,
                "auto_escape": True,
                "optimize_output": True,
                "validate_html": True
            }
        }
        
        hrpm = HTMLReportProducerModule(config)
        await hrpm.start()
        results.append(hrpm.is_active == True)
        results.append(hasattr(hrpm, 'generate_report'))
        results.append(hasattr(hrpm, 'generate_computation_report'))
        results.append(hasattr(hrpm, 'get_report_content'))
        
        # Step 2: Test HTML report generation from templates
        generation_results = []
        
        # Create test template
        test_template_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{{ title | default('OCM Report') }}</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }
                .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
                .content { background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }
                .data-table { width: 100%; border-collapse: collapse; margin: 20px 0; }
                .data-table th, .data-table td { border: 1px solid #ddd; padding: 12px; text-align: left; }
                .data-table th { background-color: #f2f2f2; font-weight: bold; }
                .highlight { background-color: #fff3cd; padding: 10px; border-radius: 5px; margin: 10px 0; }
                .footer { text-align: center; color: #666; margin-top: 30px; padding: 20px; border-top: 1px solid #eee; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{{ title | default('OCM Report') }}</h1>
                <p>Generated on: {{ generated_at | format_datetime }}</p>
                {% if report_id %}
                <p>Report ID: {{ report_id }}</p>
                {% endif %}
            </div>
            
            <div class="content">
                <h2>Summary</h2>
                <div class="highlight">
                    <strong>Status:</strong> {{ status | default('Completed') }}<br>
                    {% if processing_time %}
                    <strong>Processing Time:</strong> {{ processing_time | format_duration }}<br>
                    {% endif %}
                    {% if confidence_level %}
                    <strong>Confidence Level:</strong> {{ confidence_level | format_percentage }}<br>
                    {% endif %}
                </div>
                
                <h2>Results</h2>
                {{ results | safe }}
                
                {% if parameters %}
                <h2>Parameters</h2>
                <table class="data-table">
                    <tr><th>Parameter</th><th>Value</th></tr>
                    {% for param, value in parameters.items() %}
                    <tr><td>{{ param }}</td><td>{{ value }}</td></tr>
                    {% endfor %}
                </table>
                {% endif %}
                
                {% if metadata %}
                <h2>Metadata</h2>
                <table class="data-table">
                    <tr><th>Key</th><th>Value</th></tr>
                    {% for key, value in metadata.items() %}
                    <tr><td>{{ key }}</td><td>{{ value }}</td></tr>
                    {% endfor %}
                </table>
                {% endif %}
            </div>
            
            <div class="footer">
                <p>Generated by OCM System | {{ generated_at | format_datetime }}</p>
            </div>
        </body>
        </html>
        """
        
        test_template_path = os.path.join(templates_dir, "test_template.html")
        with open(test_template_path, 'w', encoding='utf-8') as f:
            f.write(test_template_content)
        
        generation_results.append(os.path.exists(test_template_path))
        
        # Load templates
        await hrpm._load_templates()
        generation_results.append(len(hrpm.templates) >= 1)
        
        # Step 3: Test data binding and rendering
        binding_results = []
        
        # Test data for report generation
        test_data = {
            "title": "Test Report Generation",
            "report_id": f"REP_{uuid.uuid4().hex[:8].upper()}",
            "status": "Completed",
            "processing_time": 2.5,
            "confidence_level": 0.95,
            "generated_at": datetime.now().isoformat(),
            "results": "<p>This is a test result with <strong>HTML content</strong>.</p>",
            "parameters": {
                "param1": "value1",
                "param2": 42,
                "param3": True,
                "param4": [1, 2, 3, 4, 5]
            },
            "metadata": {
                "source": "test_system",
                "version": "1.0.0",
                "author": "OCM Test Suite"
            }
        }
        
        # Generate report
        report_id = await hrpm.generate_report(
            template_id="test_template",
            data=test_data,
            report_type=ReportType.STANDARD
        )
        
        binding_results.append(report_id is not None)
        binding_results.append(len(report_id) > 0)
        
        # Step 4: Test template variable substitution
        substitution_results = []
        
        # Get generated report content
        report_content = await hrpm.get_report_content(report_id)
        substitution_results.append(report_content is not None)
        substitution_results.append(len(report_content) > 0)
        
        # Verify variable substitution
        if report_content:
            substitution_results.append("Test Report Generation" in report_content)
            substitution_results.append(test_data["report_id"] in report_content)
            substitution_results.append("Completed" in report_content)
            substitution_results.append("95.0%" in report_content)  # confidence level formatted
            substitution_results.append("2.5s" in report_content)  # processing time formatted
            substitution_results.append("value1" in report_content)
            substitution_results.append("42" in report_content)
            substitution_results.append("test_system" in report_content)
        
        # Step 5: Test HTML validation
        validation_results = []
        
        # Test HTML structure validation
        if report_content:
            validation_results.append("<!DOCTYPE html>" in report_content)
            validation_results.append("<html" in report_content)
            validation_results.append("</html>" in report_content)
            validation_results.append("<head>" in report_content)
            validation_results.append("</head>" in report_content)
            validation_results.append("<body>" in report_content)
            validation_results.append("</body>" in report_content)
            
            # Test for proper HTML escaping
            validation_results.append("&lt;" not in report_content)  # Should not have escaped <
            validation_results.append("&gt;" not in report_content)  # Should not have escaped >
            
            # Test for safe HTML content
            validation_results.append("<strong>HTML content</strong>" in report_content)
        
        # Step 6: Test report customization
        customization_results = []
        
        # Test custom styling
        custom_data = {
            "title": "Custom Styled Report",
            "report_id": f"CUSTOM_{uuid.uuid4().hex[:8].upper()}",
            "status": "Custom Status",
            "generated_at": datetime.now().isoformat(),
            "results": "<div style='color: blue; font-weight: bold;'>Custom styled content</div>",
            "parameters": {
                "custom_param": "custom_value",
                "numeric_param": 123.45
            }
        }
        
        custom_report_id = await hrpm.generate_report(
            template_id="test_template",
            data=custom_data,
            report_type=ReportType.CUSTOM
        )
        
        customization_results.append(custom_report_id is not None)
        
        # Get custom report content
        custom_report_content = await hrpm.get_report_content(custom_report_id)
        customization_results.append(custom_report_content is not None)
        
        if custom_report_content:
            customization_results.append("Custom Styled Report" in custom_report_content)
            customization_results.append("Custom Status" in custom_report_content)
            customization_results.append("custom_value" in custom_report_content)
            customization_results.append("123.45" in custom_report_content)
            customization_results.append("color: blue" in custom_report_content)
        
        # Step 7: Test report formatting
        formatting_results = []
        
        # Test different data types formatting
        complex_data = {
            "title": "Complex Data Report",
            "report_id": f"COMPLEX_{uuid.uuid4().hex[:8].upper()}",
            "generated_at": datetime.now().isoformat(),
            "results": "<p>Complex data test</p>",
            "parameters": {
                "string_param": "Hello World",
                "int_param": 1000,
                "float_param": 3.14159,
                "bool_param": True,
                "list_param": ["item1", "item2", "item3"],
                "dict_param": {"nested": "value", "number": 42}
            },
            "metadata": {
                "timestamp": datetime.now().timestamp(),
                "version": "2.1.0",
                "tags": ["test", "complex", "data"]
            }
        }
        
        complex_report_id = await hrpm.generate_report(
            template_id="test_template",
            data=complex_data,
            report_type=ReportType.DETAILED
        )
        
        formatting_results.append(complex_report_id is not None)
        
        # Get complex report content
        complex_report_content = await hrpm.get_report_content(complex_report_id)
        formatting_results.append(complex_report_content is not None)
        
        if complex_report_content:
            formatting_results.append("Complex Data Report" in complex_report_content)
            formatting_results.append("Hello World" in complex_report_content)
            formatting_results.append("1000" in complex_report_content)
            formatting_results.append("3.14159" in complex_report_content)
            formatting_results.append("True" in complex_report_content)
        
        # Step 8: Test pipeline report generation
        pipeline_results = []

        pipeline_data = {
            "analysis_id": f"PIPE_{uuid.uuid4().hex[:8].upper()}",
            "route": "forward",
            "status": "Analysis Complete",
            "confidence_level": 0.87,
            "processing_time": 15.3,
            "generated_at": datetime.now().isoformat(),
            "results": {
                "primary_result": "Positive",
                "secondary_analysis": "Confirmed",
                "details": "Detailed analysis results here",
            },
            "parameters": {
                "input_file": "test_data.csv",
                "algorithm_version": "2.1.0",
                "threshold": 0.75,
            },
        }

        pipeline_report_id = await hrpm.generate_computation_report(
            computation_data=pipeline_data,
            metadata={"source": "test_suite", "priority": "high", "title": "Pipeline Report"},
        )

        pipeline_results.append(pipeline_report_id is not None)

        pipeline_report_content = await hrpm.get_report_content(pipeline_report_id)
        pipeline_results.append(pipeline_report_content is not None)

        if pipeline_report_content:
            pipeline_results.append("Pipeline Report" in pipeline_report_content)
            pipeline_results.append("Analysis Complete" in pipeline_report_content)
            pipeline_results.append("87.0%" in pipeline_report_content)
            pipeline_results.append("15.3s" in pipeline_report_content)
        
        # Step 9: Test report generation performance
        performance_results = []
        
        # Test bulk report generation
        start_time = datetime.now()
        
        bulk_reports = []
        for i in range(5):
            bulk_data = {
                "title": f"Bulk Report {i+1}",
                "report_id": f"BULK_{i+1}_{uuid.uuid4().hex[:8].upper()}",
                "status": "Generated",
                "generated_at": datetime.now().isoformat(),
                "results": f"<p>Bulk report content {i+1}</p>",
                "parameters": {"index": i+1, "bulk_test": True}
            }
            
            report_id = await hrpm.generate_report(
                template_id="test_template",
                data=bulk_data,
                report_type=ReportType.STANDARD
            )
            bulk_reports.append(report_id)
        
        end_time = datetime.now()
        generation_time = (end_time - start_time).total_seconds()
        
        performance_results.append(len(bulk_reports) == 5)
        performance_results.append(all(report_id is not None for report_id in bulk_reports))
        performance_results.append(generation_time < 10.0)  # Should complete within 10 seconds
        
        # Step 10: Test report generation error handling
        error_results = []
        
        # Test with invalid template ID
        try:
            invalid_report_id = await hrpm.generate_report(
                template_id="non_existent_template",
                data=test_data,
                report_type=ReportType.STANDARD
            )
            error_results.append(invalid_report_id is None)
        except Exception:
            error_results.append(True)
        
        # Test with invalid data
        try:
            invalid_data_report_id = await hrpm.generate_report(
                template_id="test_template",
                data=None,
                report_type=ReportType.STANDARD
            )
            error_results.append(invalid_data_report_id is None)
        except Exception:
            error_results.append(True)
        
        # Test report listing
        report_list = hrpm.list_generated_reports()
        error_results.append(isinstance(report_list, list))
        error_results.append(len(report_list) >= 8)  # Should have at least 8 reports generated
        
        # Aggregate all results
        all_results = (
            results + 
            generation_results + 
            binding_results + 
            substitution_results + 
            validation_results + 
            customization_results + 
            formatting_results + 
            pipeline_results + 
            performance_results + 
            error_results
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
                "html_report_generation": generation_results,
                "data_binding_rendering": binding_results,
                "template_variable_substitution": substitution_results,
                "html_validation": validation_results,
                "report_customization": customization_results,
                "report_formatting": formatting_results,
                "pipeline_report_generation": pipeline_results,
                "generation_performance": performance_results,
                "error_handling": error_results
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
    result = await test_o00000032()
    print(json.dumps(result, indent=2))
    return result

if __name__ == "__main__":
    asyncio.run(main()) 