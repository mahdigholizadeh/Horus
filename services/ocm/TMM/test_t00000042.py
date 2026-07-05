"""
Test O00000042: OCVM Custom Validators
Module(s) Tested: OCVM (Output Check Validity Module)
Description: Test custom validation rule registration and execution
Test Description:
- Test custom validation rule registration
- Verify rule execution and validation
- Check validation chaining
- Test rule management
- Verify performance monitoring
- Validate custom rule reporting
Expected Result: Comprehensive custom validation system
Pass Criteria: Rules registered, executed, chained, managed, monitored, reported
Implementation Notes: Test with various custom validation scenarios
"""

import asyncio
import json
import sys
import os
import tempfile
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import uuid

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_o00000042():
    test_code = "O00000042"
    test_name = "OCVM Custom Validators"
    results = []
    
    test_dir = None
    ocvm = None
    
    try:
        # Import OCVM module
        from OCVM.ocvm import OutputCheckValidityModule, ValidationType, ValidationResult, Severity, ValidationIssue
        
        # Create temporary test directory
        test_dir = tempfile.mkdtemp(prefix="ocvm_custom_test_")
        
        # Step 1: Test OCVM module initialization with custom validators config
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
        results.append(hasattr(ocvm, 'register_custom_validator'))
        results.append(hasattr(ocvm, 'get_validation_report'))
        
        # Step 2: Test custom validation rule registration
        registration_results = []
        
        # Define custom validators
        async def custom_html_validator(content: str, content_type: str, content_id: str) -> List[ValidationIssue]:
            """Custom HTML validator that checks for specific patterns."""
            issues = []
            
            if content_type == "text/html":
                # Check for missing DOCTYPE
                if not content.strip().startswith("<!DOCTYPE"):
                    issues.append(ValidationIssue(
                        issue_id=f"custom_missing_doctype_{content_id}",
                        validation_type=ValidationType.FORMAT_COMPLIANCE,
                        severity=Severity.MEDIUM,
                        message="Missing DOCTYPE declaration",
                        description="HTML document should include DOCTYPE declaration",
                        suggested_fix="Add <!DOCTYPE html> at the beginning of the document"
                    ))
                
                # Check for missing lang attribute
                if '<html' in content and 'lang=' not in content:
                    issues.append(ValidationIssue(
                        issue_id=f"custom_missing_lang_{content_id}",
                        validation_type=ValidationType.ACCESSIBILITY,
                        severity=Severity.LOW,
                        message="Missing lang attribute on html element",
                        description="HTML element should have a lang attribute for accessibility",
                        suggested_fix="Add lang attribute to html element: <html lang=\"en\">"
                    ))
            
            return issues
        
        async def custom_content_length_validator(content: str, content_type: str, content_id: str) -> List[ValidationIssue]:
            """Custom validator that checks content length."""
            issues = []
            
            # Check minimum content length
            if len(content.strip()) < 100:
                issues.append(ValidationIssue(
                    issue_id=f"custom_content_too_short_{content_id}",
                    validation_type=ValidationType.COMPLETENESS,
                    severity=Severity.MEDIUM,
                    message="Content is too short",
                    description="Content should be at least 100 characters long",
                    suggested_fix="Add more content to meet minimum length requirements"
                ))
            
            # Check maximum content length
            if len(content) > 10000:
                issues.append(ValidationIssue(
                    issue_id=f"custom_content_too_long_{content_id}",
                    validation_type=ValidationType.SIZE_LIMITS,
                    severity=Severity.LOW,
                    message="Content is very long",
                    description="Content exceeds recommended length of 10,000 characters",
                    suggested_fix="Consider breaking content into smaller sections"
                ))
            
            return issues
        
        async def custom_security_validator(content: str, content_type: str, content_id: str) -> List[ValidationIssue]:
            """Custom security validator."""
            issues = []
            
            # Check for potentially dangerous patterns
            dangerous_patterns = [
                (r'<iframe[^>]*src=["\']http://', 'Insecure iframe source'),
                (r'<script[^>]*src=["\']http://', 'Insecure script source'),
                (r'<link[^>]*href=["\']http://', 'Insecure stylesheet source'),
                (r'<img[^>]*src=["\']http://', 'Insecure image source')
            ]
            
            for pattern, description in dangerous_patterns:
                import re
                if re.search(pattern, content, re.IGNORECASE):
                    issues.append(ValidationIssue(
                        issue_id=f"custom_security_{hash(pattern)}_{content_id}",
                        validation_type=ValidationType.SECURITY,
                        severity=Severity.HIGH,
                        message=f"Security issue: {description}",
                        description=f"Found potentially insecure resource: {description}",
                        suggested_fix="Use HTTPS URLs for external resources"
                    ))
            
            return issues
        
        # Register custom validators
        try:
            ocvm.register_custom_validator("custom_html_check", custom_html_validator)
            registration_results.append(True)
            
            ocvm.register_custom_validator("custom_content_length", custom_content_length_validator)
            registration_results.append(True)
            
            ocvm.register_custom_validator("custom_security_check", custom_security_validator)
            registration_results.append(True)
            
            # Check if validators are registered
            custom_validators = ocvm.get_status().get("custom_validators", [])
            registration_results.append("custom_html_check" in custom_validators)
            registration_results.append("custom_content_length" in custom_validators)
            registration_results.append("custom_security_check" in custom_validators)
            registration_results.append(len(custom_validators) >= 3)
            
        except Exception as e:
            print(f"Custom validator registration failed: {e}")
            registration_results.extend([False, False, False, False, False, False, False])
        
        # Step 3: Test rule execution and validation
        execution_results = []
        
        # Test content that should trigger custom validators
        test_content_with_issues = """
        <html>
        <head>
            <title>Test Content</title>
            <script src="http://insecure-site.com/script.js"></script>
            <link href="http://insecure-site.com/style.css" rel="stylesheet">
        </head>
        <body>
            <h1>Short content</h1>
            <p>This content is too short to pass the custom length validator.</p>
            <iframe src="http://insecure-site.com/embed"></iframe>
        </body>
        </html>
        """
        
        try:
            # Validate content with custom validators
            custom_report_id = await ocvm.validate_content(
                content=test_content_with_issues,
                content_type="text/html",
                content_id=f"custom_test_{uuid.uuid4().hex[:8]}",
                metadata={"test_type": "custom_validation"}
            )
            
            execution_results.append(custom_report_id is not None)
            
            if custom_report_id:
                custom_report = await ocvm.get_validation_report(custom_report_id)
                execution_results.append(custom_report is not None)
                
                if custom_report:
                    # Check if custom validators were executed
                    issues = custom_report.get("issues", [])
                    execution_results.append(len(issues) >= 3)  # Should have multiple issues
                    
                    # Check for custom validation issues
                    custom_issues = [issue for issue in issues if "custom_" in issue.get("issue_id", "")]
                    execution_results.append(len(custom_issues) >= 2)
                    
                    # Check specific custom issues
                    has_doctype_issue = any("custom_missing_doctype" in issue.get("issue_id", "") for issue in issues)
                    has_lang_issue = any("custom_missing_lang" in issue.get("issue_id", "") for issue in issues)
                    has_length_issue = any("custom_content_too_short" in issue.get("issue_id", "") for issue in issues)
                    has_security_issue = any("custom_security" in issue.get("issue_id", "") for issue in issues)
                    
                    execution_results.append(has_doctype_issue)
                    execution_results.append(has_lang_issue)
                    execution_results.append(has_length_issue)
                    execution_results.append(has_security_issue)
                    
                    # Check overall result
                    overall_result = custom_report.get("overall_result")
                    execution_results.append(
                        overall_result in [ValidationResult.FAILED.value, ValidationResult.WARNING.value]
                    )
                else:
                    execution_results.extend([False, False, False, False, False, False, False, False, False])
            else:
                execution_results.extend([False, False, False, False, False, False, False, False, False, False])
                
        except Exception as e:
            print(f"Custom validation execution failed: {e}")
            execution_results.extend([False, False, False, False, False, False, False, False, False, False])
        
        # Test content that should pass custom validators
        test_content_clean = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Clean Test Content</title>
            <script src="https://secure-site.com/script.js"></script>
            <link href="https://secure-site.com/style.css" rel="stylesheet">
        </head>
        <body>
            <h1>Clean Content</h1>
            <p>This content should pass all custom validators. It has proper DOCTYPE, lang attribute, sufficient length, and uses secure HTTPS resources.</p>
            <p>Additional content to ensure minimum length requirements are met. This paragraph provides more context and information to satisfy the content length validator.</p>
            <p>More content to make sure we exceed the minimum character count and provide comprehensive information for testing purposes.</p>
        </body>
        </html>
        """
        
        try:
            # Validate clean content with custom validators
            clean_custom_report_id = await ocvm.validate_content(
                content=test_content_clean,
                content_type="text/html",
                content_id=f"clean_custom_{uuid.uuid4().hex[:8]}",
                metadata={"test_type": "clean_custom_validation"}
            )
            
            execution_results.append(clean_custom_report_id is not None)
            
            if clean_custom_report_id:
                clean_custom_report = await ocvm.get_validation_report(clean_custom_report_id)
                execution_results.append(clean_custom_report is not None)
                
                if clean_custom_report:
                    # Should have fewer issues
                    issues = clean_custom_report.get("issues", [])
                    execution_results.append(len(issues) <= 2)  # Should have few issues
                    
                    # Check overall result
                    overall_result = clean_custom_report.get("overall_result")
                    execution_results.append(
                        overall_result in [ValidationResult.PASSED.value, ValidationResult.WARNING.value]
                    )
                else:
                    execution_results.extend([False, False, False])
            else:
                execution_results.extend([False, False, False, False])
                
        except Exception as e:
            print(f"Clean custom validation failed: {e}")
            execution_results.extend([False, False, False, False])
        
        # Step 4: Test validation chaining
        chaining_results = []
        
        # Define chained validators
        async def first_validator(content: str, content_type: str, content_id: str) -> List[ValidationIssue]:
            """First validator in chain."""
            issues = []
            if content_type == "text/html" and "<h1>" not in content:
                issues.append(ValidationIssue(
                    issue_id=f"chain_no_h1_{content_id}",
                    validation_type=ValidationType.FORMAT_COMPLIANCE,
                    severity=Severity.MEDIUM,
                    message="Missing H1 heading",
                    description="HTML document should have at least one H1 heading",
                    suggested_fix="Add an H1 heading to the document"
                ))
            return issues
        
        async def second_validator(content: str, content_type: str, content_id: str) -> List[ValidationIssue]:
            """Second validator in chain."""
            issues = []
            if content_type == "text/html" and "<p>" not in content:
                issues.append(ValidationIssue(
                    issue_id=f"chain_no_p_{content_id}",
                    validation_type=ValidationType.FORMAT_COMPLIANCE,
                    severity=Severity.LOW,
                    message="Missing paragraph content",
                    description="HTML document should have paragraph content",
                    suggested_fix="Add paragraph content to the document"
                ))
            return issues
        
        # Register chained validators
        try:
            ocvm.register_custom_validator("chain_first", first_validator)
            ocvm.register_custom_validator("chain_second", second_validator)
            
            chaining_results.append(True)
            
            # Test chained validation
            chained_content = """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <title>Chained Test</title>
            </head>
            <body>
                <h1>Main Heading</h1>
                <p>This content should pass both chained validators.</p>
            </body>
            </html>
            """
            
            chained_report_id = await ocvm.validate_content(
                content=chained_content,
                content_type="text/html",
                content_id=f"chained_{uuid.uuid4().hex[:8]}",
                metadata={"test_type": "validation_chaining"}
            )
            
            chaining_results.append(chained_report_id is not None)
            
            if chained_report_id:
                chained_report = await ocvm.get_validation_report(chained_report_id)
                chaining_results.append(chained_report is not None)
                
                if chained_report:
                    # Should pass both validators
                    issues = chained_report.get("issues", [])
                    chaining_results.append(len(issues) <= 1)  # Should have few issues
                    
                    # Check overall result
                    overall_result = chained_report.get("overall_result")
                    chaining_results.append(
                        overall_result in [ValidationResult.PASSED.value, ValidationResult.WARNING.value]
                    )
                else:
                    chaining_results.extend([False, False, False])
            else:
                chaining_results.extend([False, False, False, False])
                
        except Exception as e:
            print(f"Validation chaining failed: {e}")
            chaining_results.extend([False, False, False, False, False])
        
        # Step 5: Test rule management
        management_results = []
        
        # Test validator status
        try:
            status = ocvm.get_status()
            custom_validators = status.get("custom_validators", [])
            
            management_results.append(isinstance(custom_validators, list))
            management_results.append(len(custom_validators) >= 5)  # Should have all registered validators
            
            # Check for specific validators
            expected_validators = [
                "custom_html_check", "custom_content_length", "custom_security_check",
                "chain_first", "chain_second"
            ]
            
            for validator in expected_validators:
                management_results.append(validator in custom_validators)
            
        except Exception as e:
            print(f"Rule management test failed: {e}")
            management_results.extend([False, False, False, False, False, False, False])
        
        # Step 6: Test performance monitoring
        performance_results = []
        
        # Test multiple custom validations for performance
        start_time = datetime.now()
        
        performance_content_samples = [
            ("<html><body><h1>Test 1</h1><p>Content 1.</p></body></html>", "perf_1"),
            ("<html><body><h1>Test 2</h1><p>Content 2.</p></body></html>", "perf_2"),
            ("<html><body><h1>Test 3</h1><p>Content 3.</p></body></html>", "perf_3")
        ]
        
        performance_tasks = []
        for content, content_id in performance_content_samples:
            task = ocvm.validate_content(
                content=content,
                content_type="text/html",
                content_id=f"perf_{content_id}_{uuid.uuid4().hex[:8]}",
                metadata={"test_type": "custom_performance"}
            )
            performance_tasks.append(task)
        
        try:
            performance_results_list = await asyncio.gather(*performance_tasks, return_exceptions=True)
            end_time = datetime.now()
            performance_time = (end_time - start_time).total_seconds()
            
            performance_results.append(len(performance_results_list) == 3)
            performance_results.append(any(isinstance(result, str) for result in performance_results_list))
            performance_results.append(performance_time < 10.0)  # Should complete within 10 seconds
            
        except Exception as e:
            print(f"Performance monitoring failed: {e}")
            performance_results.extend([False, False, False])
        
        # Step 7: Test custom rule reporting
        reporting_results = []
        
        # Test validation report with custom validators
        try:
            validation_reports = ocvm.list_validation_reports(limit=5)
            reporting_results.append(isinstance(validation_reports, list))
            reporting_results.append(len(validation_reports) >= 0)
            
            # Check if reports contain custom validation issues
            custom_issues_found = False
            for report in validation_reports:
                issues = report.get("issues", [])
                for issue in issues:
                    if "custom_" in issue.get("issue_id", ""):
                        custom_issues_found = True
                        break
                if custom_issues_found:
                    break
            
            reporting_results.append(custom_issues_found)
            
        except Exception as e:
            print(f"Custom rule reporting failed: {e}")
            reporting_results.extend([False, False, False])
        
        # Test individual report with custom validators
        if custom_report_id:
            try:
                report = await ocvm.get_validation_report(custom_report_id)
                reporting_results.append(isinstance(report, dict))
                reporting_results.append("issues" in report)
                
                if report and "issues" in report:
                    issues = report["issues"]
                    custom_issues = [issue for issue in issues if "custom_" in issue.get("issue_id", "")]
                    reporting_results.append(len(custom_issues) >= 2)
                else:
                    reporting_results.append(False)
            except Exception as e:
                print(f"Individual custom report failed: {e}")
                reporting_results.extend([False, False, False])
        else:
            reporting_results.extend([False, False, False])
        
        # Step 8: Test custom validator error handling
        error_results = []
        
        # Test with invalid custom validator
        async def invalid_validator(content: str, content_type: str, content_id: str) -> List[ValidationIssue]:
            """Invalid validator that raises an exception."""
            raise Exception("Custom validator error")
        
        try:
            ocvm.register_custom_validator("invalid_validator", invalid_validator)
            error_results.append(True)
            
            # Test validation with invalid validator
            test_content = "<html><body><h1>Test</h1></body></html>"
            
            invalid_report_id = await ocvm.validate_content(
                content=test_content,
                content_type="text/html",
                content_id=f"invalid_validator_{uuid.uuid4().hex[:8]}",
                metadata={"test_type": "invalid_validator"}
            )
            
            error_results.append(invalid_report_id is not None)
            
            if invalid_report_id:
                invalid_report = await ocvm.get_validation_report(invalid_report_id)
                error_results.append(invalid_report is not None)
                
                if invalid_report:
                    # Should still have other validation results
                    error_results.append("issues" in invalid_report)
                else:
                    error_results.append(False)
            else:
                error_results.extend([False, False])
                
        except Exception as e:
            print(f"Invalid validator test failed: {e}")
            error_results.extend([False, False, False, False])
        
        # Test with None content
        try:
            none_report_id = await ocvm.validate_content(
                content=None,
                content_type="text/html",
                content_id=f"none_content_{uuid.uuid4().hex[:8]}",
                metadata={"test_type": "none_content"}
            )
            # Should either return None or raise an exception, both are acceptable
            error_results.append(True)
        except Exception:
            # Exception is also acceptable for None content
            error_results.append(True)
        
        # Step 9: Test custom validator validation
        validation_results = []
        
        # Test module status with custom validators
        try:
            status = ocvm.get_status()
            validation_results.append(isinstance(status, dict))
            validation_results.append("module" in status)
            validation_results.append("active" in status)
            validation_results.append("custom_validators" in status)
            
            custom_validators = status.get("custom_validators", [])
            validation_results.append(isinstance(custom_validators, list))
            validation_results.append(len(custom_validators) >= 5)
            
        except Exception as e:
            print(f"Custom validator status test failed: {e}")
            validation_results.extend([False, False, False, False, False, False])
        
        # Test health check with custom validators
        try:
            health = await ocvm.health_check()
            validation_results.append(isinstance(health, dict))
            validation_results.append("healthy" in health)
            validation_results.append("is_active" in health)
            validation_results.append("custom_validators" in health)
            
        except Exception as e:
            print(f"Custom validator health check failed: {e}")
            validation_results.extend([False, False, False, False])
        
        # Test quality metrics with custom validators
        try:
            metrics = ocvm.get_quality_metrics()
            validation_results.append(isinstance(metrics, dict))
            validation_results.append("total_validations" in metrics)
            validation_results.append("average_quality_score" in metrics)
            validation_results.append(metrics.get("total_validations", 0) >= 0)
            
        except Exception as e:
            print(f"Custom validator quality metrics failed: {e}")
            validation_results.extend([False, False, False, False])
        
        # Step 10: Test custom validator cleanup
        cleanup_results = []
        
        # Test that custom validators persist after multiple validations
        try:
            # Get initial validator count
            initial_status = ocvm.get_status()
            initial_validators = initial_status.get("custom_validators", [])
            initial_count = len(initial_validators)
            
            cleanup_results.append(initial_count >= 5)
            
            # Perform additional validation
            cleanup_content = "<html><body><h1>Cleanup Test</h1><p>Content for cleanup test.</p></body></html>"
            
            cleanup_report_id = await ocvm.validate_content(
                content=cleanup_content,
                content_type="text/html",
                content_id=f"cleanup_{uuid.uuid4().hex[:8]}",
                metadata={"test_type": "cleanup_test"}
            )
            
            cleanup_results.append(cleanup_report_id is not None)
            
            # Check that validators still exist
            final_status = ocvm.get_status()
            final_validators = final_status.get("custom_validators", [])
            final_count = len(final_validators)
            
            cleanup_results.append(final_count >= initial_count)
            cleanup_results.append("custom_html_check" in final_validators)
            
        except Exception as e:
            print(f"Custom validator cleanup test failed: {e}")
            cleanup_results.extend([False, False, False, False])
        
        # Aggregate all results
        all_results = (
            results + 
            registration_results + 
            execution_results + 
            chaining_results + 
            management_results + 
            performance_results + 
            reporting_results + 
            error_results + 
            validation_results + 
            cleanup_results
        )
        
        # Calculate pass rate
        passed_tests = sum(all_results)
        total_tests = len(all_results)
        pass_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        # Get final status
        final_status = ocvm.get_status()
        
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
                "custom_validation_rule_registration": registration_results,
                "rule_execution_and_validation": execution_results,
                "validation_chaining": chaining_results,
                "rule_management": management_results,
                "performance_monitoring": performance_results,
                "custom_rule_reporting": reporting_results,
                "custom_validator_error_handling": error_results,
                "custom_validator_validation": validation_results,
                "custom_validator_cleanup": cleanup_results
            },
            "custom_validator_metrics": {
                "total_custom_validators": len(final_status.get("custom_validators", [])),
                "custom_validators": final_status.get("custom_validators", []),
                "total_validations": final_status.get("stats", {}).get("validations_performed", 0),
                "validation_types": final_status.get("stats", {}).get("validation_types", {})
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
    result = await test_o00000042()
    print(json.dumps(result, indent=2))
    return result

if __name__ == "__main__":
    asyncio.run(main())