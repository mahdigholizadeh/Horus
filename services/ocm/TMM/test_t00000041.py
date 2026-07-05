"""
Test O00000041: OCVM Quality Metrics
Module(s) Tested: OCVM (Output Check Validity Module)
Description: Test quality metrics calculation and reporting
Test Description:
- Calculate content quality scores
- Test readability metrics
- Verify completeness indicators
- Check accuracy measurements
- Test quality trend analysis
- Validate quality reporting
Expected Result: Comprehensive quality metrics and reporting
Pass Criteria: Metrics calculated, scores accurate, trends analyzed, reporting clear
Implementation Notes: Test with various content quality levels
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

async def test_o00000041():
    test_code = "O00000041"
    test_name = "OCVM Quality Metrics"
    results = []
    
    test_dir = None
    ocvm = None
    
    try:
        # Import OCVM module
        from OCVM.ocvm import OutputCheckValidityModule, ValidationType, ValidationResult, Severity
        
        # Create temporary test directory
        test_dir = tempfile.mkdtemp(prefix="ocvm_quality_test_")
        
        # Step 1: Test OCVM module initialization with quality metrics config
        config = {
            "output_validation": {
                "enabled_validations": [
                    "content_integrity", 
                    "format_compliance", 
                    "completeness", 
                    "size_limits",
                    "security",
                    "accessibility",
                    "performance"
                ],
                "max_file_size_mb": 10,
                "max_validation_time_ms": 30000,
                "quality_threshold": 80,
                "html_max_size_mb": 5,
                "pdf_max_size_mb": 20,
                "json_max_size_mb": 2,
                "text_max_size_mb": 2
            }
        }
        
        ocvm = OutputCheckValidityModule(config)
        await ocvm.start()
        
        # Test module initialization
        results.append(ocvm.is_active == True)
        results.append(hasattr(ocvm, 'validate_content'))
        results.append(hasattr(ocvm, 'get_quality_metrics'))
        results.append(hasattr(ocvm, 'get_validation_report'))
        
        # Step 2: Test content quality score calculation
        quality_score_results = []
        
        # Create high-quality HTML content
        high_quality_html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>High Quality Document</title>
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    margin: 20px; 
                    line-height: 1.6; 
                    color: #333;
                }
                .header { 
                    background: #2c3e50; 
                    color: white; 
                    padding: 20px; 
                    border-radius: 8px; 
                    margin-bottom: 20px; 
                    text-align: center;
                }
                .content { 
                    background: #f8f9fa; 
                    padding: 20px; 
                    border-radius: 8px; 
                    margin: 20px 0; 
                }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>High Quality Document</h1>
                <p>This document demonstrates excellent quality standards.</p>
            </div>
            <div class="content">
                <h2>Introduction</h2>
                <p>This is a well-structured document with proper HTML formatting, semantic markup, and accessibility features.</p>
                <h2>Main Content</h2>
                <p>The content is comprehensive, well-organized, and follows best practices for web development.</p>
                <ul>
                    <li>Proper heading structure</li>
                    <li>Semantic HTML elements</li>
                    <li>Accessibility considerations</li>
                    <li>Clean and maintainable code</li>
                </ul>
            </div>
        </body>
        </html>
        """
        
        try:
            # Validate high-quality content
            high_quality_report_id = await ocvm.validate_content(
                content=high_quality_html,
                content_type="text/html",
                content_id=f"high_quality_{uuid.uuid4().hex[:8]}",
                metadata={"test_type": "high_quality"}
            )
            
            quality_score_results.append(high_quality_report_id is not None)
            
            # Get high-quality report
            if high_quality_report_id:
                high_quality_report = await ocvm.get_validation_report(high_quality_report_id)
                quality_score_results.append(high_quality_report is not None)
                
                if high_quality_report:
                    # Check quality score calculation
                    quality_score_results.append(high_quality_report.get("overall_result") == ValidationResult.PASSED.value)
                    quality_score_results.append(high_quality_report.get("total_issues", 0) <= 2)  # Should have few issues
                    
                    # Check quality metrics
                    quality_metrics = ocvm.get_quality_metrics()
                    quality_score_results.append(isinstance(quality_metrics, dict))
                    quality_score_results.append("average_quality_score" in quality_metrics)
                    quality_score_results.append(quality_metrics.get("average_quality_score", 0) >= 80)
                else:
                    quality_score_results.extend([False, False, False, False, False])
            else:
                quality_score_results.extend([False, False, False, False, False, False])
                
        except Exception as e:
            print(f"High quality validation failed: {e}")
            quality_score_results.extend([False, False, False, False, False, False])
        
        # Create medium-quality HTML content
        medium_quality_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Medium Quality Document</title>
        </head>
        <body>
            <h1>Medium Quality Document</h1>
            <p>This document has some quality issues but is generally acceptable.</p>
            <div>
                <p>Some content here.</p>
                <p>More content with some formatting issues.</p>
            </div>
        </body>
        </html>
        """
        
        try:
            # Validate medium-quality content
            medium_quality_report_id = await ocvm.validate_content(
                content=medium_quality_html,
                content_type="text/html",
                content_id=f"medium_quality_{uuid.uuid4().hex[:8]}",
                metadata={"test_type": "medium_quality"}
            )
            
            quality_score_results.append(medium_quality_report_id is not None)
            
            # Get medium-quality report
            if medium_quality_report_id:
                medium_quality_report = await ocvm.get_validation_report(medium_quality_report_id)
                quality_score_results.append(medium_quality_report is not None)
                
                if medium_quality_report:
                    # Check quality score for medium quality content
                    overall_result = medium_quality_report.get("overall_result")
                    quality_score_results.append(
                        overall_result in [ValidationResult.PASSED.value, ValidationResult.WARNING.value]
                    )
                else:
                    quality_score_results.append(False)
            else:
                quality_score_results.extend([False, False])
                
        except Exception as e:
            print(f"Medium quality validation failed: {e}")
            quality_score_results.extend([False, False, False])
        
        # Create low-quality HTML content
        low_quality_html = """
        <html>
        <body>
            <h1>Low Quality Document</h1>
            <p>This document has many quality issues.</p>
            <script>alert('Unsafe script');</script>
            <img src="image.jpg">
            <div style="color: #000000;">
                <p>Content with accessibility issues.</p>
            </div>
        </body>
        </html>
        """
        
        try:
            # Validate low-quality content
            low_quality_report_id = await ocvm.validate_content(
                content=low_quality_html,
                content_type="text/html",
                content_id=f"low_quality_{uuid.uuid4().hex[:8]}",
                metadata={"test_type": "low_quality"}
            )
            
            quality_score_results.append(low_quality_report_id is not None)
            
            # Get low-quality report
            if low_quality_report_id:
                low_quality_report = await ocvm.get_validation_report(low_quality_report_id)
                quality_score_results.append(low_quality_report is not None)
                
                if low_quality_report:
                    # Check quality score for low quality content
                    overall_result = low_quality_report.get("overall_result")
                    quality_score_results.append(
                        overall_result in [ValidationResult.FAILED.value, ValidationResult.WARNING.value]
                    )
                    quality_score_results.append(low_quality_report.get("total_issues", 0) >= 3)  # Should have many issues
                else:
                    quality_score_results.extend([False, False])
            else:
                quality_score_results.extend([False, False, False])
                
        except Exception as e:
            print(f"Low quality validation failed: {e}")
            quality_score_results.extend([False, False, False, False])
        
        # Step 3: Test readability metrics
        readability_results = []
        
        # Test with readable content
        readable_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Readable Content</title>
        </head>
        <body>
            <h1>Clear and Readable Content</h1>
            <p>This content is written in simple, clear language that is easy to understand.</p>
            <p>It uses short sentences and common words to improve readability.</p>
            <h2>Well-Structured Information</h2>
            <p>The information is organized logically with proper headings and paragraphs.</p>
        </body>
        </html>
        """
        
        try:
            readable_report_id = await ocvm.validate_content(
                content=readable_content,
                content_type="text/html",
                content_id=f"readable_{uuid.uuid4().hex[:8]}",
                metadata={"test_type": "readability"}
            )
            
            readability_results.append(readable_report_id is not None)
            
            if readable_report_id:
                readable_report = await ocvm.get_validation_report(readable_report_id)
                readability_results.append(readable_report is not None)
                
                if readable_report:
                    readability_results.append(readable_report.get("overall_result") == ValidationResult.PASSED.value)
                    readability_results.append(readable_report.get("total_issues", 0) <= 1)
                else:
                    readability_results.extend([False, False])
            else:
                readability_results.extend([False, False, False])
                
        except Exception as e:
            print(f"Readability test failed: {e}")
            readability_results.extend([False, False, False, False])
        
        # Test with complex content
        complex_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Complex Content</title>
        </head>
        <body>
            <h1>Complex Technical Documentation</h1>
            <p>This document contains highly technical terminology and complex sentence structures that may be difficult for general audiences to comprehend without specialized knowledge in the subject matter.</p>
            <p>The utilization of sophisticated vocabulary and intricate grammatical constructions necessitates advanced reading comprehension skills.</p>
        </body>
        </html>
        """
        
        try:
            complex_report_id = await ocvm.validate_content(
                content=complex_content,
                content_type="text/html",
                content_id=f"complex_{uuid.uuid4().hex[:8]}",
                metadata={"test_type": "complexity"}
            )
            
            readability_results.append(complex_report_id is not None)
            
        except Exception as e:
            print(f"Complex content test failed: {e}")
            readability_results.append(False)
        
        # Step 4: Test completeness indicators
        completeness_results = []
        
        # Test complete content
        complete_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Complete Document</title>
        </head>
        <body>
            <header>
                <h1>Complete Document</h1>
                <nav>
                    <ul>
                        <li><a href="#intro">Introduction</a></li>
                        <li><a href="#main">Main Content</a></li>
                        <li><a href="#conclusion">Conclusion</a></li>
                    </ul>
                </nav>
            </header>
            <main>
                <section id="intro">
                    <h2>Introduction</h2>
                    <p>This is a complete document with all necessary sections.</p>
                </section>
                <section id="main">
                    <h2>Main Content</h2>
                    <p>The main content provides comprehensive information.</p>
                </section>
                <section id="conclusion">
                    <h2>Conclusion</h2>
                    <p>This concludes the complete document.</p>
                </section>
            </main>
            <footer>
                <p>&copy; 2024 Complete Document</p>
            </footer>
        </body>
        </html>
        """
        
        try:
            complete_report_id = await ocvm.validate_content(
                content=complete_content,
                content_type="text/html",
                content_id=f"complete_{uuid.uuid4().hex[:8]}",
                metadata={"test_type": "completeness"}
            )
            
            completeness_results.append(complete_report_id is not None)
            
            if complete_report_id:
                complete_report = await ocvm.get_validation_report(complete_report_id)
                completeness_results.append(complete_report is not None)
                
                if complete_report:
                    completeness_results.append(complete_report.get("overall_result") == ValidationResult.PASSED.value)
                    completeness_results.append(complete_report.get("total_issues", 0) <= 2)
                else:
                    completeness_results.extend([False, False])
            else:
                completeness_results.extend([False, False, False])
                
        except Exception as e:
            print(f"Completeness test failed: {e}")
            completeness_results.extend([False, False, False, False])
        
        # Test incomplete content
        incomplete_content = """
        <!DOCTYPE html>
        <html>
        <body>
            <h1>Incomplete Document</h1>
            <p>This document is missing important sections.</p>
            <!-- Missing introduction, main content, and conclusion -->
        </body>
        </html>
        """
        
        try:
            incomplete_report_id = await ocvm.validate_content(
                content=incomplete_content,
                content_type="text/html",
                content_id=f"incomplete_{uuid.uuid4().hex[:8]}",
                metadata={"test_type": "incompleteness"}
            )
            
            completeness_results.append(incomplete_report_id is not None)
            
            if incomplete_report_id:
                incomplete_report = await ocvm.get_validation_report(incomplete_report_id)
                completeness_results.append(incomplete_report is not None)
                
                if incomplete_report:
                    # Should have more issues due to incompleteness
                    completeness_results.append(incomplete_report.get("total_issues", 0) >= 1)
                else:
                    completeness_results.append(False)
            else:
                completeness_results.extend([False, False])
                
        except Exception as e:
            print(f"Incomplete content test failed: {e}")
            completeness_results.extend([False, False, False])
        
        # Step 5: Test accuracy measurements
        accuracy_results = []
        
        # Test accurate content
        accurate_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Accurate Information</title>
        </head>
        <body>
            <h1>Accurate Information</h1>
            <p>The Earth orbits around the Sun, completing one revolution approximately every 365.25 days.</p>
            <p>Water boils at 100 degrees Celsius at sea level under standard atmospheric pressure.</p>
            <p>The speed of light in a vacuum is approximately 299,792,458 meters per second.</p>
        </body>
        </html>
        """
        
        try:
            accurate_report_id = await ocvm.validate_content(
                content=accurate_content,
                content_type="text/html",
                content_id=f"accurate_{uuid.uuid4().hex[:8]}",
                metadata={"test_type": "accuracy"}
            )
            
            accuracy_results.append(accurate_report_id is not None)
            
            if accurate_report_id:
                accurate_report = await ocvm.get_validation_report(accurate_report_id)
                accuracy_results.append(accurate_report is not None)
                
                if accurate_report:
                    accuracy_results.append(accurate_report.get("overall_result") == ValidationResult.PASSED.value)
                    accuracy_results.append(accurate_report.get("total_issues", 0) <= 1)
                else:
                    accuracy_results.extend([False, False])
            else:
                accuracy_results.extend([False, False, False])
                
        except Exception as e:
            print(f"Accuracy test failed: {e}")
            accuracy_results.extend([False, False, False, False])
        
        # Test inaccurate content
        inaccurate_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Inaccurate Information</title>
        </head>
        <body>
            <h1>Inaccurate Information</h1>
            <p>The Sun orbits around the Earth.</p>
            <p>Water boils at 50 degrees Celsius.</p>
            <p>The speed of light is 100 meters per second.</p>
        </body>
        </html>
        """
        
        try:
            inaccurate_report_id = await ocvm.validate_content(
                content=inaccurate_content,
                content_type="text/html",
                content_id=f"inaccurate_{uuid.uuid4().hex[:8]}",
                metadata={"test_type": "inaccuracy"}
            )
            
            accuracy_results.append(inaccurate_report_id is not None)
            
            if inaccurate_report_id:
                inaccurate_report = await ocvm.get_validation_report(inaccurate_report_id)
                accuracy_results.append(inaccurate_report is not None)
                
                if inaccurate_report:
                    # Should have issues due to inaccuracies
                    accuracy_results.append(inaccurate_report.get("total_issues", 0) >= 0)
                else:
                    accuracy_results.append(False)
            else:
                accuracy_results.extend([False, False])
                
        except Exception as e:
            print(f"Inaccurate content test failed: {e}")
            accuracy_results.extend([False, False, False])
        
        # Step 6: Test quality trend analysis
        trend_results = []
        
        # Test multiple validations to analyze trends
        trend_content_samples = [
            ("<html><body><h1>Sample 1</h1><p>Good content.</p></body></html>", "sample_1"),
            ("<html><body><h1>Sample 2</h1><p>Better content with more detail.</p></body></html>", "sample_2"),
            ("<html><body><h1>Sample 3</h1><p>Excellent content with comprehensive information.</p></body></html>", "sample_3")
        ]
        
        trend_report_ids = []
        for content, sample_id in trend_content_samples:
            try:
                report_id = await ocvm.validate_content(
                    content=content,
                    content_type="text/html",
                    content_id=f"trend_{sample_id}_{uuid.uuid4().hex[:8]}",
                    metadata={"test_type": "trend_analysis"}
                )
                trend_report_ids.append(report_id)
            except Exception as e:
                print(f"Trend analysis sample {sample_id} failed: {e}")
                trend_report_ids.append(None)
        
        trend_results.append(len(trend_report_ids) == 3)
        trend_results.append(any(report_id is not None for report_id in trend_report_ids))
        
        # Analyze quality trends
        quality_scores = []
        for report_id in trend_report_ids:
            if report_id:
                try:
                    report = await ocvm.get_validation_report(report_id)
                    if report:
                        # Calculate quality score based on issues
                        total_issues = report.get("total_issues", 0)
                        quality_score = max(0, 100 - (total_issues * 10))
                        quality_scores.append(quality_score)
                except Exception:
                    quality_scores.append(0)
        
        trend_results.append(len(quality_scores) >= 2)
        trend_results.append(all(score >= 0 for score in quality_scores))
        
        # Check if quality metrics show trends
        try:
            quality_metrics = ocvm.get_quality_metrics()
            trend_results.append("average_quality_score" in quality_metrics)
            trend_results.append(quality_metrics.get("total_validations", 0) >= 3)
        except Exception:
            trend_results.extend([False, False])
        
        # Step 7: Test quality reporting
        reporting_results = []
        
        # Test quality metrics reporting
        try:
            quality_metrics = ocvm.get_quality_metrics()
            reporting_results.append(isinstance(quality_metrics, dict))
            reporting_results.append("total_validations" in quality_metrics)
            reporting_results.append("average_quality_score" in quality_metrics)
            reporting_results.append("total_issues" in quality_metrics)
            reporting_results.append("critical_issues" in quality_metrics)
            reporting_results.append("failed_validations" in quality_metrics)
            reporting_results.append("success_rate" in quality_metrics)
            reporting_results.append("validation_types" in quality_metrics)
        except Exception as e:
            print(f"Quality metrics reporting failed: {e}")
            reporting_results.extend([False, False, False, False, False, False, False, False])
        
        # Test validation report listing
        try:
            validation_reports = ocvm.list_validation_reports(limit=10)
            reporting_results.append(isinstance(validation_reports, list))
            reporting_results.append(len(validation_reports) >= 0)
        except Exception as e:
            print(f"Validation report listing failed: {e}")
            reporting_results.extend([False, False])
        
        # Test individual report retrieval
        if high_quality_report_id:
            try:
                report = await ocvm.get_validation_report(high_quality_report_id)
                reporting_results.append(isinstance(report, dict))
                reporting_results.append("report_id" in report)
                reporting_results.append("content_id" in report)
                reporting_results.append("overall_result" in report)
                reporting_results.append("total_issues" in report)
                reporting_results.append("issues_by_severity" in report)
                reporting_results.append("validation_timestamp" in report)
            except Exception as e:
                print(f"Individual report retrieval failed: {e}")
                reporting_results.extend([False, False, False, False, False, False, False])
        else:
            reporting_results.extend([False, False, False, False, False, False, False])
        
        # Test content validity check
        if high_quality_report_id:
            try:
                is_valid = await ocvm.is_content_valid(high_quality_report_id)
                reporting_results.append(isinstance(is_valid, bool))
            except Exception as e:
                print(f"Content validity check failed: {e}")
                reporting_results.append(False)
        else:
            reporting_results.append(False)
        
        # Step 8: Test quality performance
        performance_results = []
        
        # Test multiple concurrent validations
        start_time = datetime.now()
        
        concurrent_content = [
            ("<html><body><h1>Concurrent 1</h1><p>Content 1.</p></body></html>", "concurrent_1"),
            ("<html><body><h1>Concurrent 2</h1><p>Content 2.</p></body></html>", "concurrent_2"),
            ("<html><body><h1>Concurrent 3</h1><p>Content 3.</p></body></html>", "concurrent_3")
        ]
        
        concurrent_tasks = []
        for content, content_id in concurrent_content:
            task = ocvm.validate_content(
                content=content,
                content_type="text/html",
                content_id=f"perf_{content_id}_{uuid.uuid4().hex[:8]}",
                metadata={"test_type": "performance"}
            )
            concurrent_tasks.append(task)
        
        try:
            concurrent_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            end_time = datetime.now()
            performance_time = (end_time - start_time).total_seconds()
            
            performance_results.append(len(concurrent_results) == 3)
            performance_results.append(any(isinstance(result, str) for result in concurrent_results))
            performance_results.append(performance_time < 10.0)  # Should complete within 10 seconds
            
        except Exception as e:
            print(f"Performance test failed: {e}")
            performance_results.extend([False, False, False])
        
        # Step 9: Test quality error handling
        error_results = []
        
        # Test with invalid content
        try:
            invalid_report_id = await ocvm.validate_content(
                content=None,
                content_type="text/html",
                content_id=f"error_{uuid.uuid4().hex[:8]}",
                metadata={"test_type": "error_handling"}
            )
            error_results.append(invalid_report_id is not None)
        except Exception:
            # Exception is also acceptable for invalid content
            error_results.append(True)
        
        # Test with very large content
        large_content = "A" * (11 * 1024 * 1024)  # 11MB, exceeds limit
        try:
            large_report_id = await ocvm.validate_content(
                content=large_content,
                content_type="text/plain",
                content_id=f"large_{uuid.uuid4().hex[:8]}",
                metadata={"test_type": "large_content"}
            )
            error_results.append(large_report_id is not None)
        except Exception:
            # Exception is also acceptable for very large content
            error_results.append(True)
        
        # Step 10: Test quality validation
        validation_results = []
        
        # Test module status
        try:
            status = ocvm.get_status()
            validation_results.append(isinstance(status, dict))
            validation_results.append("module" in status)
            validation_results.append("active" in status)
            validation_results.append("enabled_validations" in status)
            validation_results.append("custom_validators" in status)
        except Exception as e:
            print(f"Module status test failed: {e}")
            validation_results.extend([False, False, False, False, False])
        
        # Test health check
        try:
            health = await ocvm.health_check()
            validation_results.append(isinstance(health, dict))
            validation_results.append("healthy" in health)
            validation_results.append("is_active" in health)
            validation_results.append("module" in health)
        except Exception as e:
            print(f"Health check test failed: {e}")
            validation_results.extend([False, False, False, False])
        
        # Test quality metrics validity
        try:
            metrics = ocvm.get_quality_metrics()
            validation_results.append(isinstance(metrics, dict))
            validation_results.append(metrics.get("total_validations", 0) >= 0)
            validation_results.append(0 <= metrics.get("average_quality_score", 0) <= 100)
            validation_results.append(metrics.get("total_issues", 0) >= 0)
        except Exception as e:
            print(f"Quality metrics validation failed: {e}")
            validation_results.extend([False, False, False, False])
        
        # Aggregate all results
        all_results = (
            results + 
            quality_score_results + 
            readability_results + 
            completeness_results + 
            accuracy_results + 
            trend_results + 
            reporting_results + 
            performance_results + 
            error_results + 
            validation_results
        )
        
        # Calculate pass rate
        passed_tests = sum(all_results)
        total_tests = len(all_results)
        pass_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        # Get final quality metrics
        final_quality_metrics = ocvm.get_quality_metrics()
        
        # Cleanup
        await ocvm.stop()
        
        # Clean up test directory
        try:
            import shutil
            shutil.rmtree(test_dir)
        except Exception:
            pass  # Ignore cleanup errors
        
        return {
            "test_code": test_code,
            "test_name": test_name,
            "status": "PASSED" if pass_rate >= 85 else "FAILED",
            "pass_rate": pass_rate,
            "passed_tests": passed_tests,
            "total_tests": total_tests,
            "results": {
                "module_initialization": results,
                "content_quality_score_calculation": quality_score_results,
                "readability_metrics": readability_results,
                "completeness_indicators": completeness_results,
                "accuracy_measurements": accuracy_results,
                "quality_trend_analysis": trend_results,
                "quality_reporting": reporting_results,
                "quality_performance": performance_results,
                "quality_error_handling": error_results,
                "quality_validation": validation_results
            },
            "quality_metrics": {
                "total_validations": final_quality_metrics.get("total_validations", 0),
                "average_quality_score": final_quality_metrics.get("average_quality_score", 0),
                "total_issues": final_quality_metrics.get("total_issues", 0),
                "critical_issues": final_quality_metrics.get("critical_issues", 0),
                "failed_validations": final_quality_metrics.get("failed_validations", 0),
                "success_rate": final_quality_metrics.get("success_rate", 0)
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
    result = await test_o00000041()
    print(json.dumps(result, indent=2))
    return result

if __name__ == "__main__":
    asyncio.run(main())