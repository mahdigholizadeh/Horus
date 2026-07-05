"""
Output Check Validity Module (OCVM) for OCM

This module is responsible for quality assurance validation, content integrity checks,
format validation, completeness verification, and ensuring generated output meets
quality standards before delivery to the client-facing web server.
"""

import asyncio
import logging
import json
import os
import re
import hashlib
from typing import Dict, Any, Optional, List, Union, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import mimetypes
from pathlib import Path

class ValidationResult(Enum):
    """Validation result status."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"

class ValidationType(Enum):
    """Types of validations performed."""
    CONTENT_INTEGRITY = "content_integrity"
    FORMAT_COMPLIANCE = "format_compliance"
    COMPLETENESS = "completeness"
    SIZE_LIMITS = "size_limits"
    SECURITY = "security"
    ACCESSIBILITY = "accessibility"
    PERFORMANCE = "performance"
    CUSTOM = "custom"

class Severity(Enum):
    """Issue severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ValidationIssue:
    """Validation issue information."""
    issue_id: str
    validation_type: ValidationType
    severity: Severity
    message: str
    description: str
    location: Optional[str] = None
    suggested_fix: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class ValidationReport:
    """Comprehensive validation report."""
    report_id: str
    content_id: str
    content_type: str
    validation_timestamp: datetime
    overall_result: ValidationResult
    total_issues: int
    issues_by_severity: Dict[str, int]
    issues: List[ValidationIssue]
    validation_duration_ms: int
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class OutputCheckValidityModule:
    """
    Output Check Validity Module (OCVM)
    
    Provides comprehensive output validation:
    - Content integrity and completeness checks
    - Format validation (HTML, PDF, JSON, etc.)
    - Security vulnerability scanning
    - Accessibility compliance verification
    - Performance and size optimization checks
    - Custom validation rule support
    - Quality scoring and reporting
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the OCVM module."""
        self.logger = logging.getLogger(__name__)
        self.module_name = "OCVM"
        self.is_active = False
        
        # Configuration
        self.config = config
        self.validation_config = config.get('output_validation', {})
        
        # Validation settings
        self.enabled_validations = set(self.validation_config.get('enabled_validations', [
            'content_integrity', 'format_compliance', 'completeness', 'size_limits'
        ]))
        self.max_file_size_mb = self.validation_config.get('max_file_size_mb', 50)
        self.max_validation_time_ms = self.validation_config.get('max_validation_time_ms', 30000)
        self.quality_threshold = self.validation_config.get('quality_threshold', 80)
        
        # Size limits
        self.size_limits = {
            'html': self.validation_config.get('html_max_size_mb', 10),
            'pdf': self.validation_config.get('pdf_max_size_mb', 50),
            'json': self.validation_config.get('json_max_size_mb', 5),
            'text': self.validation_config.get('text_max_size_mb', 5)
        }
        
        # Validation reports
        self.validation_reports = {}  # report_id -> ValidationReport
        
        # Custom validation rules
        self.custom_validators = {}  # validator_name -> validator_function
        
        # Security patterns to check for
        self.security_patterns = [
            (r'<script[^>]*>.*?</script>', 'Potentially unsafe script tag'),
            (r'javascript:', 'JavaScript protocol in URL'),
            (r'on\w+\s*=', 'Inline event handler'),
            (r'eval\s*\(', 'Use of eval function'),
            (r'document\.cookie', 'Direct cookie access'),
            (r'innerHTML\s*=', 'Direct innerHTML assignment')
        ]
        
        # Accessibility patterns
        self.accessibility_checks = [
            (r'<img(?![^>]*alt=)', 'Image without alt attribute'),
            (r'<input(?![^>]*(?:aria-label|aria-labelledby))', 'Form input without label'),
            (r'<table(?![^>]*summary=)', 'Table without summary'),
            (r'color:\s*#[0-9a-fA-F]{3,6}', 'Color definition (check contrast)')
        ]
        
        # Performance checks
        self.performance_patterns = [
            (r'<img[^>]*(?!.*width=|.*height=)', 'Image without dimensions'),
            (r'<link[^>]*rel=["\']stylesheet["\'][^>]*(?!.*media=)', 'Stylesheet without media query'),
            (r'<style[^>]*>[\s\S]*?</style>', 'Inline styles (consider external CSS)')
        ]
        
        # Statistics
        self.stats = {
            'validations_performed': 0,
            'issues_found': 0,
            'critical_issues': 0,
            'failed_validations': 0,
            'average_quality_score': 0.0,
            'start_time': None,
            'validation_types': {vtype.value: 0 for vtype in ValidationType}
        }
        
        self.logger.info(f"{self.module_name} initialized - enabled validations: {self.enabled_validations}")
    
    async def start(self):
        """Start the OCVM module."""
        try:
            self.is_active = True
            self.stats['start_time'] = datetime.now().isoformat()
            
            # Register built-in validators
            self._register_builtin_validators()
            
            self.logger.info("OCVM started successfully - output validation ready")
            
        except Exception as e:
            self.logger.error(f"Failed to start OCVM: {e}")
            raise
    
    async def stop(self):
        """Stop the OCVM module gracefully."""
        try:
            self.is_active = False
            self.logger.info("OCVM stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping OCVM: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            # Test validation with sample content
            test_html = "<html><head><title>Test</title></head><body><h1>Test</h1></body></html>"
            test_report = await self.validate_content(
                content=test_html,
                content_type="text/html",
                content_id="health_check"
            )
            
            is_healthy = self.is_active and test_report is not None
            
            return {
                'healthy': is_healthy,
                'is_active': self.is_active,
                'validation_test_passed': test_report is not None,
                'enabled_validations': list(self.enabled_validations),
                'custom_validators': len(self.custom_validators),
                'module': 'ocvm'
            }
            
        except Exception as e:
            self.logger.error(f"OCVM health check failed: {e}")
            return {
                'healthy': False,
                'error': str(e),
                'module': 'ocvm'
            }
    
    def _register_builtin_validators(self):
        """Register built-in validation functions."""
        self.custom_validators = {
            'html_structure': self._validate_html_structure,
            'json_syntax': self._validate_json_syntax,
            'pdf_integrity': self._validate_pdf_integrity,
            'content_completeness': self._validate_content_completeness,
            'security_scan': self._validate_security,
            'accessibility_check': self._validate_accessibility,
            'performance_check': self._validate_performance
        }
    
    async def validate_content(self, content: Union[str, bytes], content_type: str, 
                             content_id: str, metadata: Dict[str, Any] = None) -> str:
        """Validate content and return validation report ID."""
        try:
            start_time = datetime.now()
            
            # Generate report ID
            report_id = f"validation_{int(start_time.timestamp())}_{content_id}"
            
            # Initialize validation report
            issues = []
            
            # Determine content format
            file_extension = self._get_file_extension_from_mime_type(content_type)
            
            # Size validation
            if 'size_limits' in self.enabled_validations:
                size_issues = await self._validate_size_limits(content, file_extension, content_id)
                issues.extend(size_issues)
            
            # Content integrity validation
            if 'content_integrity' in self.enabled_validations:
                integrity_issues = await self._validate_content_integrity(content, content_type, content_id)
                issues.extend(integrity_issues)
            
            # Format compliance validation
            if 'format_compliance' in self.enabled_validations:
                format_issues = await self._validate_format_compliance(content, content_type, content_id)
                issues.extend(format_issues)
            
            # Completeness validation
            if 'completeness' in self.enabled_validations:
                completeness_issues = await self._validate_completeness(content, content_type, content_id)
                issues.extend(completeness_issues)
            
            # Security validation
            if 'security' in self.enabled_validations:
                security_issues = await self._validate_security_issues(content, content_type, content_id)
                issues.extend(security_issues)
            
            # Accessibility validation
            if 'accessibility' in self.enabled_validations and content_type in ['text/html', 'application/xhtml+xml']:
                accessibility_issues = await self._validate_accessibility_compliance(content, content_id)
                issues.extend(accessibility_issues)
            
            # Performance validation
            if 'performance' in self.enabled_validations:
                performance_issues = await self._validate_performance_optimization(content, content_type, content_id)
                issues.extend(performance_issues)
            
            # Run custom validators
            custom_issues = await self._run_custom_validators(content, content_type, content_id)
            issues.extend(custom_issues)
            
            # Calculate validation duration
            end_time = datetime.now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Determine overall result
            overall_result = self._determine_overall_result(issues)
            
            # Count issues by severity
            issues_by_severity = {
                'low': sum(1 for issue in issues if issue.severity == Severity.LOW),
                'medium': sum(1 for issue in issues if issue.severity == Severity.MEDIUM),
                'high': sum(1 for issue in issues if issue.severity == Severity.HIGH),
                'critical': sum(1 for issue in issues if issue.severity == Severity.CRITICAL)
            }
            
            # Create validation report
            validation_report = ValidationReport(
                report_id=report_id,
                content_id=content_id,
                content_type=content_type,
                validation_timestamp=start_time,
                overall_result=overall_result,
                total_issues=len(issues),
                issues_by_severity=issues_by_severity,
                issues=issues,
                validation_duration_ms=duration_ms,
                metadata=metadata or {}
            )
            
            # Store report
            self.validation_reports[report_id] = validation_report
            
            # Update statistics
            self.stats['validations_performed'] += 1
            self.stats['issues_found'] += len(issues)
            self.stats['critical_issues'] += issues_by_severity['critical']
            if overall_result == ValidationResult.FAILED:
                self.stats['failed_validations'] += 1
            
            # Calculate quality score
            quality_score = self._calculate_quality_score(issues)
            if self.stats['validations_performed'] > 0:
                current_avg = self.stats['average_quality_score']
                total_validations = self.stats['validations_performed']
                self.stats['average_quality_score'] = ((current_avg * (total_validations - 1)) + quality_score) / total_validations
            
            self.logger.info(f"Validation completed: {report_id} - {overall_result.value} "
                           f"({len(issues)} issues, score: {quality_score:.1f})")
            
            return report_id
            
        except Exception as e:
            self.logger.error(f"Content validation failed for {content_id}: {e}")
            raise
    
    async def _validate_size_limits(self, content: Union[str, bytes], file_extension: str, 
                                  content_id: str) -> List[ValidationIssue]:
        """Validate content size limits."""
        issues = []
        
        try:
            # Calculate content size
            if isinstance(content, str):
                content_size = len(content.encode('utf-8'))
            else:
                content_size = len(content)
            
            size_mb = content_size / (1024 * 1024)
            
            # Check general size limit
            if size_mb > self.max_file_size_mb:
                issues.append(ValidationIssue(
                    issue_id=f"size_limit_{content_id}",
                    validation_type=ValidationType.SIZE_LIMITS,
                    severity=Severity.HIGH,
                    message=f"Content size ({size_mb:.2f}MB) exceeds maximum limit ({self.max_file_size_mb}MB)",
                    description="Content is too large and may cause performance issues",
                    suggested_fix=f"Reduce content size to under {self.max_file_size_mb}MB"
                ))
            
            # Check specific format limits
            if file_extension in self.size_limits:
                format_limit = self.size_limits[file_extension]
                if size_mb > format_limit:
                    issues.append(ValidationIssue(
                        issue_id=f"format_size_{file_extension}_{content_id}",
                        validation_type=ValidationType.SIZE_LIMITS,
                        severity=Severity.MEDIUM,
                        message=f"{file_extension.upper()} content ({size_mb:.2f}MB) exceeds recommended limit ({format_limit}MB)",
                        description=f"Content is larger than recommended for {file_extension} format",
                        suggested_fix=f"Optimize content to under {format_limit}MB for {file_extension} format"
                    ))
            
        except Exception as e:
            issues.append(ValidationIssue(
                issue_id=f"size_validation_error_{content_id}",
                validation_type=ValidationType.SIZE_LIMITS,
                severity=Severity.MEDIUM,
                message=f"Size validation failed: {e}",
                description="Could not determine content size"
            ))
        
        return issues
    
    async def _validate_content_integrity(self, content: Union[str, bytes], content_type: str, 
                                        content_id: str) -> List[ValidationIssue]:
        """Validate content integrity and structure."""
        issues = []
        
        try:
            # Check if content is empty
            if not content or (isinstance(content, str) and not content.strip()):
                issues.append(ValidationIssue(
                    issue_id=f"empty_content_{content_id}",
                    validation_type=ValidationType.CONTENT_INTEGRITY,
                    severity=Severity.CRITICAL,
                    message="Content is empty or contains only whitespace",
                    description="No actual content found",
                    suggested_fix="Ensure content is properly generated before validation"
                ))
                return issues
            
            # Calculate content checksum
            if isinstance(content, str):
                content_bytes = content.encode('utf-8')
            else:
                content_bytes = content
            
            checksum = hashlib.md5(content_bytes).hexdigest()
            
            # Check for null bytes or control characters
            if isinstance(content, str):
                if '\x00' in content:
                    issues.append(ValidationIssue(
                        issue_id=f"null_bytes_{content_id}",
                        validation_type=ValidationType.CONTENT_INTEGRITY,
                        severity=Severity.HIGH,
                        message="Content contains null bytes",
                        description="Null bytes found in content may indicate corruption",
                        suggested_fix="Review content generation process for data corruption"
                    ))
                
                # Check for excessive control characters
                control_chars = sum(1 for char in content if ord(char) < 32 and char not in '\t\n\r')
                if control_chars > len(content) * 0.01:  # More than 1% control characters
                    issues.append(ValidationIssue(
                        issue_id=f"control_chars_{content_id}",
                        validation_type=ValidationType.CONTENT_INTEGRITY,
                        severity=Severity.MEDIUM,
                        message=f"Content contains unusual number of control characters ({control_chars})",
                        description="High concentration of control characters may indicate encoding issues",
                        suggested_fix="Check content encoding and generation process"
                    ))
            
            # Store checksum in metadata for future reference
            # (This could be used for change detection)
            
        except Exception as e:
            issues.append(ValidationIssue(
                issue_id=f"integrity_validation_error_{content_id}",
                validation_type=ValidationType.CONTENT_INTEGRITY,
                severity=Severity.MEDIUM,
                message=f"Integrity validation failed: {e}",
                description="Could not complete integrity checks"
            ))
        
        return issues
    
    async def _validate_format_compliance(self, content: Union[str, bytes], content_type: str, 
                                        content_id: str) -> List[ValidationIssue]:
        """Validate format compliance based on content type."""
        issues = []
        
        try:
            if content_type in ['text/html', 'application/xhtml+xml']:
                issues.extend(await self._validate_html_format(content, content_id))
            elif content_type == 'application/json':
                issues.extend(await self._validate_json_format(content, content_id))
            elif content_type == 'application/pdf':
                issues.extend(await self._validate_pdf_format(content, content_id))
            elif content_type.startswith('text/'):
                issues.extend(await self._validate_text_format(content, content_id))
            
        except Exception as e:
            issues.append(ValidationIssue(
                issue_id=f"format_validation_error_{content_id}",
                validation_type=ValidationType.FORMAT_COMPLIANCE,
                severity=Severity.MEDIUM,
                message=f"Format validation failed: {e}",
                description="Could not complete format compliance checks"
            ))
        
        return issues
    
    async def _validate_html_format(self, content: Union[str, bytes], content_id: str) -> List[ValidationIssue]:
        """Validate HTML format compliance."""
        issues = []
        
        try:
            if isinstance(content, bytes):
                content = content.decode('utf-8', errors='replace')
            
            # Basic HTML structure checks
            if not re.search(r'<html[^>]*>', content, re.IGNORECASE):
                issues.append(ValidationIssue(
                    issue_id=f"missing_html_tag_{content_id}",
                    validation_type=ValidationType.FORMAT_COMPLIANCE,
                    severity=Severity.MEDIUM,
                    message="Missing HTML tag",
                    description="Document should have an HTML tag",
                    suggested_fix="Wrap content with <html> tags"
                ))
            
            if not re.search(r'<head[^>]*>', content, re.IGNORECASE):
                issues.append(ValidationIssue(
                    issue_id=f"missing_head_tag_{content_id}",
                    validation_type=ValidationType.FORMAT_COMPLIANCE,
                    severity=Severity.MEDIUM,
                    message="Missing HEAD section",
                    description="Document should have a HEAD section",
                    suggested_fix="Add <head> section with meta information"
                ))
            
            if not re.search(r'<body[^>]*>', content, re.IGNORECASE):
                issues.append(ValidationIssue(
                    issue_id=f"missing_body_tag_{content_id}",
                    validation_type=ValidationType.FORMAT_COMPLIANCE,
                    severity=Severity.MEDIUM,
                    message="Missing BODY tag",
                    description="Document should have a BODY tag",
                    suggested_fix="Wrap main content with <body> tags"
                ))
            
            # Check for unclosed tags (simplified)
            open_tags = re.findall(r'<(\w+)[^>]*>', content)
            close_tags = re.findall(r'</(\w+)>', content)
            
            # Self-closing tags that don't need closing tags
            self_closing = {'img', 'br', 'hr', 'meta', 'link', 'input', 'area', 'base', 'col', 'embed', 'source', 'track', 'wbr'}
            
            open_count = {}
            for tag in open_tags:
                tag = tag.lower()
                if tag not in self_closing:
                    open_count[tag] = open_count.get(tag, 0) + 1
            
            for tag in close_tags:
                tag = tag.lower()
                if tag in open_count:
                    open_count[tag] -= 1
            
            for tag, count in open_count.items():
                if count > 0:
                    issues.append(ValidationIssue(
                        issue_id=f"unclosed_tag_{tag}_{content_id}",
                        validation_type=ValidationType.FORMAT_COMPLIANCE,
                        severity=Severity.MEDIUM,
                        message=f"Unclosed {tag} tag(s) ({count})",
                        description=f"Found {count} unclosed <{tag}> tag(s)",
                        suggested_fix=f"Add closing </{tag}> tag(s)"
                    ))
            
        except Exception as e:
            issues.append(ValidationIssue(
                issue_id=f"html_validation_error_{content_id}",
                validation_type=ValidationType.FORMAT_COMPLIANCE,
                severity=Severity.LOW,
                message=f"HTML validation error: {e}",
                description="Could not complete HTML format validation"
            ))
        
        return issues
    
    async def _validate_json_format(self, content: Union[str, bytes], content_id: str) -> List[ValidationIssue]:
        """Validate JSON format compliance."""
        issues = []
        
        try:
            if isinstance(content, bytes):
                content = content.decode('utf-8', errors='replace')
            
            # Try to parse JSON
            json.loads(content)
            
        except json.JSONDecodeError as e:
            issues.append(ValidationIssue(
                issue_id=f"json_syntax_error_{content_id}",
                validation_type=ValidationType.FORMAT_COMPLIANCE,
                severity=Severity.CRITICAL,
                message=f"JSON syntax error: {e.msg}",
                description=f"Invalid JSON at line {e.lineno}, column {e.colno}",
                location=f"Line {e.lineno}, Column {e.colno}",
                suggested_fix="Fix JSON syntax errors"
            ))
        except Exception as e:
            issues.append(ValidationIssue(
                issue_id=f"json_validation_error_{content_id}",
                validation_type=ValidationType.FORMAT_COMPLIANCE,
                severity=Severity.MEDIUM,
                message=f"JSON validation error: {e}",
                description="Could not validate JSON format"
            ))
        
        return issues
    
    async def _validate_pdf_format(self, content: Union[str, bytes], content_id: str) -> List[ValidationIssue]:
        """Validate PDF format compliance."""
        issues = []
        
        try:
            if isinstance(content, str):
                content = content.encode('utf-8')
            
            # Basic PDF signature check
            if not content.startswith(b'%PDF-'):
                issues.append(ValidationIssue(
                    issue_id=f"invalid_pdf_signature_{content_id}",
                    validation_type=ValidationType.FORMAT_COMPLIANCE,
                    severity=Severity.CRITICAL,
                    message="Invalid PDF signature",
                    description="Content does not start with PDF signature (%PDF-)",
                    suggested_fix="Ensure content is a valid PDF file"
                ))
            
            # Check for PDF version
            pdf_version_match = re.search(rb'%PDF-(\d+\.\d+)', content[:20])
            if pdf_version_match:
                version = pdf_version_match.group(1).decode('ascii')
                # Validate reasonable PDF version
                try:
                    version_num = float(version)
                    if version_num < 1.0 or version_num > 2.0:
                        issues.append(ValidationIssue(
                            issue_id=f"unusual_pdf_version_{content_id}",
                            validation_type=ValidationType.FORMAT_COMPLIANCE,
                            severity=Severity.LOW,
                            message=f"Unusual PDF version: {version}",
                            description="PDF version is outside typical range (1.0-2.0)"
                        ))
                except ValueError:
                    issues.append(ValidationIssue(
                        issue_id=f"invalid_pdf_version_{content_id}",
                        validation_type=ValidationType.FORMAT_COMPLIANCE,
                        severity=Severity.MEDIUM,
                        message=f"Invalid PDF version: {version}",
                        description="PDF version is not a valid number"
                    ))
            
            # Check for EOF marker
            if not content.rstrip().endswith(b'%%EOF'):
                issues.append(ValidationIssue(
                    issue_id=f"missing_pdf_eof_{content_id}",
                    validation_type=ValidationType.FORMAT_COMPLIANCE,
                    severity=Severity.MEDIUM,
                    message="Missing PDF EOF marker",
                    description="PDF should end with %%EOF marker",
                    suggested_fix="Ensure PDF generation includes proper EOF marker"
                ))
            
        except Exception as e:
            issues.append(ValidationIssue(
                issue_id=f"pdf_validation_error_{content_id}",
                validation_type=ValidationType.FORMAT_COMPLIANCE,
                severity=Severity.LOW,
                message=f"PDF validation error: {e}",
                description="Could not complete PDF format validation"
            ))
        
        return issues
    
    async def _validate_text_format(self, content: Union[str, bytes], content_id: str) -> List[ValidationIssue]:
        """Validate text format compliance."""
        issues = []
        
        try:
            if isinstance(content, bytes):
                content = content.decode('utf-8', errors='replace')
            
            # Check for encoding issues (replacement characters)
            if '�' in content:
                replacement_count = content.count('�')
                issues.append(ValidationIssue(
                    issue_id=f"encoding_issues_{content_id}",
                    validation_type=ValidationType.FORMAT_COMPLIANCE,
                    severity=Severity.MEDIUM,
                    message=f"Text contains {replacement_count} replacement character(s)",
                    description="Replacement characters indicate encoding issues",
                    suggested_fix="Check source encoding and conversion process"
                ))
            
            # Check for extremely long lines
            lines = content.split('\n')
            long_lines = [(i+1, len(line)) for i, line in enumerate(lines) if len(line) > 1000]
            
            if long_lines:
                issues.append(ValidationIssue(
                    issue_id=f"long_lines_{content_id}",
                    validation_type=ValidationType.FORMAT_COMPLIANCE,
                    severity=Severity.LOW,
                    message=f"Found {len(long_lines)} extremely long line(s)",
                    description="Very long lines may cause display or processing issues",
                    location=f"Lines: {', '.join(str(line_num) for line_num, _ in long_lines[:5])}",
                    suggested_fix="Consider breaking long lines or adjusting formatting"
                ))
            
        except Exception as e:
            issues.append(ValidationIssue(
                issue_id=f"text_validation_error_{content_id}",
                validation_type=ValidationType.FORMAT_COMPLIANCE,
                severity=Severity.LOW,
                message=f"Text validation error: {e}",
                description="Could not complete text format validation"
            ))
        
        return issues
    
    async def _validate_completeness(self, content: Union[str, bytes], content_type: str, 
                                   content_id: str) -> List[ValidationIssue]:
        """Validate content completeness."""
        issues = []
        
        try:
            if isinstance(content, bytes):
                content_str = content.decode('utf-8', errors='replace')
            else:
                content_str = content
            
            # Check for placeholder text
            placeholders = [
                'lorem ipsum', 'placeholder', 'todo', 'tbd', 'to be determined',
                'xxx', 'yyy', 'zzz', '[content]', '[data]', '[information]'
            ]
            
            for placeholder in placeholders:
                if re.search(rf'\b{re.escape(placeholder)}\b', content_str, re.IGNORECASE):
                    issues.append(ValidationIssue(
                        issue_id=f"placeholder_text_{placeholder}_{content_id}",
                        validation_type=ValidationType.COMPLETENESS,
                        severity=Severity.MEDIUM,
                        message=f"Placeholder text found: '{placeholder}'",
                        description="Content contains placeholder text that should be replaced",
                        suggested_fix=f"Replace placeholder '{placeholder}' with actual content"
                    ))
            
            # Check for empty or minimal content
            meaningful_content = re.sub(r'<[^>]+>|\s+', ' ', content_str).strip()
            if len(meaningful_content) < 50:
                issues.append(ValidationIssue(
                    issue_id=f"minimal_content_{content_id}",
                    validation_type=ValidationType.COMPLETENESS,
                    severity=Severity.HIGH,
                    message="Content appears to be minimal or empty",
                    description=f"Only {len(meaningful_content)} characters of meaningful content found",
                    suggested_fix="Ensure content is fully generated and populated"
                ))
            
            # Check for error messages or failure indicators
            error_indicators = [
                'error', 'failed', 'exception', 'null pointer', 'undefined',
                'not found', '404', '500', 'internal server error'
            ]
            
            for indicator in error_indicators:
                if re.search(rf'\b{re.escape(indicator)}\b', content_str, re.IGNORECASE):
                    issues.append(ValidationIssue(
                        issue_id=f"error_indicator_{indicator}_{content_id}",
                        validation_type=ValidationType.COMPLETENESS,
                        severity=Severity.HIGH,
                        message=f"Error indicator found: '{indicator}'",
                        description="Content contains error messages or failure indicators",
                        suggested_fix="Review content generation process for errors"
                    ))
            
        except Exception as e:
            issues.append(ValidationIssue(
                issue_id=f"completeness_validation_error_{content_id}",
                validation_type=ValidationType.COMPLETENESS,
                severity=Severity.LOW,
                message=f"Completeness validation error: {e}",
                description="Could not complete content completeness checks"
            ))
        
        return issues
    
    async def _validate_security_issues(self, content: Union[str, bytes], content_type: str, 
                                      content_id: str) -> List[ValidationIssue]:
        """Validate content for security issues."""
        issues = []
        
        try:
            if isinstance(content, bytes):
                content_str = content.decode('utf-8', errors='replace')
            else:
                content_str = content
            
            # Check security patterns
            for pattern, description in self.security_patterns:
                matches = re.finditer(pattern, content_str, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    issues.append(ValidationIssue(
                        issue_id=f"security_{hash(pattern)}_{match.start()}_{content_id}",
                        validation_type=ValidationType.SECURITY,
                        severity=Severity.HIGH,
                        message=f"Security issue: {description}",
                        description=f"Found potentially unsafe pattern: {match.group()[:50]}...",
                        location=f"Position {match.start()}-{match.end()}",
                        suggested_fix="Remove or sanitize potentially unsafe content"
                    ))
            
            # Check for sensitive data patterns (basic check)
            sensitive_patterns = [
                (r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', 'Possible credit card number'),
                (r'\b\d{3}-\d{2}-\d{4}\b', 'Possible social security number'),
                (r'password\s*[=:]\s*["\']?[\w@#$%^&*!]+', 'Possible password exposure')
            ]
            
            for pattern, description in sensitive_patterns:
                if re.search(pattern, content_str, re.IGNORECASE):
                    issues.append(ValidationIssue(
                        issue_id=f"sensitive_data_{hash(pattern)}_{content_id}",
                        validation_type=ValidationType.SECURITY,
                        severity=Severity.CRITICAL,
                        message=f"Sensitive data detected: {description}",
                        description="Content may contain sensitive information",
                        suggested_fix="Remove or redact sensitive information"
                    ))
            
        except Exception as e:
            issues.append(ValidationIssue(
                issue_id=f"security_validation_error_{content_id}",
                validation_type=ValidationType.SECURITY,
                severity=Severity.LOW,
                message=f"Security validation error: {e}",
                description="Could not complete security validation"
            ))
        
        return issues
    
    async def _validate_accessibility_compliance(self, content: Union[str, bytes], 
                                               content_id: str) -> List[ValidationIssue]:
        """Validate accessibility compliance."""
        issues = []
        
        try:
            if isinstance(content, bytes):
                content_str = content.decode('utf-8', errors='replace')
            else:
                content_str = content
            
            # Check accessibility patterns
            for pattern, description in self.accessibility_checks:
                matches = list(re.finditer(pattern, content_str, re.IGNORECASE))
                if matches:
                    issues.append(ValidationIssue(
                        issue_id=f"accessibility_{hash(pattern)}_{content_id}",
                        validation_type=ValidationType.ACCESSIBILITY,
                        severity=Severity.MEDIUM,
                        message=f"Accessibility issue: {description}",
                        description=f"Found {len(matches)} accessibility issue(s)",
                        suggested_fix="Add appropriate accessibility attributes"
                    ))
            
            # Check for heading structure
            headings = re.findall(r'<h([1-6])[^>]*>', content_str, re.IGNORECASE)
            if headings:
                heading_levels = [int(h) for h in headings]
                
                # Check for proper heading hierarchy
                if heading_levels[0] != 1:
                    issues.append(ValidationIssue(
                        issue_id=f"heading_hierarchy_{content_id}",
                        validation_type=ValidationType.ACCESSIBILITY,
                        severity=Severity.MEDIUM,
                        message="Document should start with H1 heading",
                        description="First heading is not H1, which may confuse screen readers",
                        suggested_fix="Start document with H1 heading"
                    ))
                
                # Check for skipped heading levels
                for i in range(1, len(heading_levels)):
                    if heading_levels[i] > heading_levels[i-1] + 1:
                        issues.append(ValidationIssue(
                            issue_id=f"skipped_heading_{i}_{content_id}",
                            validation_type=ValidationType.ACCESSIBILITY,
                            severity=Severity.LOW,
                            message=f"Skipped heading level at position {i+1}",
                            description="Skipping heading levels may confuse screen readers",
                            suggested_fix="Use sequential heading levels"
                        ))
            
        except Exception as e:
            issues.append(ValidationIssue(
                issue_id=f"accessibility_validation_error_{content_id}",
                validation_type=ValidationType.ACCESSIBILITY,
                severity=Severity.LOW,
                message=f"Accessibility validation error: {e}",
                description="Could not complete accessibility validation"
            ))
        
        return issues
    
    async def _validate_performance_optimization(self, content: Union[str, bytes], content_type: str, 
                                               content_id: str) -> List[ValidationIssue]:
        """Validate performance optimization."""
        issues = []
        
        try:
            if isinstance(content, bytes):
                content_str = content.decode('utf-8', errors='replace')
            else:
                content_str = content
            
            # Check performance patterns
            for pattern, description in self.performance_patterns:
                matches = list(re.finditer(pattern, content_str, re.IGNORECASE))
                if matches:
                    issues.append(ValidationIssue(
                        issue_id=f"performance_{hash(pattern)}_{content_id}",
                        validation_type=ValidationType.PERFORMANCE,
                        severity=Severity.LOW,
                        message=f"Performance optimization: {description}",
                        description=f"Found {len(matches)} potential optimization(s)",
                        suggested_fix="Apply suggested performance optimizations"
                    ))
            
            # Check for large inline content
            if content_type == 'text/html':
                # Check for large inline styles
                style_blocks = re.findall(r'<style[^>]*>(.*?)</style>', content_str, re.DOTALL | re.IGNORECASE)
                total_css_size = sum(len(block) for block in style_blocks)
                
                if total_css_size > 10000:  # More than 10KB of inline CSS
                    issues.append(ValidationIssue(
                        issue_id=f"large_inline_css_{content_id}",
                        validation_type=ValidationType.PERFORMANCE,
                        severity=Severity.MEDIUM,
                        message=f"Large amount of inline CSS ({total_css_size} bytes)",
                        description="Large inline CSS can slow page loading",
                        suggested_fix="Consider moving CSS to external stylesheet"
                    ))
                
                # Check for large inline scripts
                script_blocks = re.findall(r'<script[^>]*>(.*?)</script>', content_str, re.DOTALL | re.IGNORECASE)
                total_js_size = sum(len(block) for block in script_blocks)
                
                if total_js_size > 50000:  # More than 50KB of inline JS
                    issues.append(ValidationIssue(
                        issue_id=f"large_inline_js_{content_id}",
                        validation_type=ValidationType.PERFORMANCE,
                        severity=Severity.MEDIUM,
                        message=f"Large amount of inline JavaScript ({total_js_size} bytes)",
                        description="Large inline JavaScript can slow page loading",
                        suggested_fix="Consider moving JavaScript to external file"
                    ))
            
        except Exception as e:
            issues.append(ValidationIssue(
                issue_id=f"performance_validation_error_{content_id}",
                validation_type=ValidationType.PERFORMANCE,
                severity=Severity.LOW,
                message=f"Performance validation error: {e}",
                description="Could not complete performance validation"
            ))
        
        return issues
    
    async def _run_custom_validators(self, content: Union[str, bytes], content_type: str, 
                                   content_id: str) -> List[ValidationIssue]:
        """Run custom validation functions."""
        issues = []
        
        try:
            for validator_name, validator_func in self.custom_validators.items():
                try:
                    custom_issues = await validator_func(content, content_type, content_id)
                    if custom_issues:
                        issues.extend(custom_issues)
                        self.stats['validation_types'][ValidationType.CUSTOM.value] += len(custom_issues)
                except Exception as e:
                    issues.append(ValidationIssue(
                        issue_id=f"custom_validator_error_{validator_name}_{content_id}",
                        validation_type=ValidationType.CUSTOM,
                        severity=Severity.LOW,
                        message=f"Custom validator '{validator_name}' failed: {e}",
                        description="Custom validation function encountered an error"
                    ))
        
        except Exception as e:
            self.logger.error(f"Error running custom validators: {e}")
        
        return issues
    
    # Built-in custom validator functions (examples)
    
    async def _validate_html_structure(self, content: Union[str, bytes], content_type: str, content_id: str) -> List[ValidationIssue]:
        """Custom HTML structure validator."""
        return []  # Placeholder - implement specific HTML structure rules
    
    async def _validate_json_syntax(self, content: Union[str, bytes], content_type: str, content_id: str) -> List[ValidationIssue]:
        """Custom JSON syntax validator."""
        return []  # Placeholder - implement specific JSON rules
    
    async def _validate_pdf_integrity(self, content: Union[str, bytes], content_type: str, content_id: str) -> List[ValidationIssue]:
        """Custom PDF integrity validator."""
        return []  # Placeholder - implement specific PDF rules
    
    async def _validate_content_completeness(self, content: Union[str, bytes], content_type: str, content_id: str) -> List[ValidationIssue]:
        """Custom content completeness validator."""
        return []  # Placeholder - implement specific completeness rules
    
    async def _validate_security(self, content: Union[str, bytes], content_type: str, content_id: str) -> List[ValidationIssue]:
        """Custom security validator."""
        return []  # Placeholder - implement additional security rules
    
    async def _validate_accessibility(self, content: Union[str, bytes], content_type: str, content_id: str) -> List[ValidationIssue]:
        """Custom accessibility validator."""
        return []  # Placeholder - implement additional accessibility rules
    
    async def _validate_performance(self, content: Union[str, bytes], content_type: str, content_id: str) -> List[ValidationIssue]:
        """Custom performance validator."""
        return []  # Placeholder - implement additional performance rules
    
    def _determine_overall_result(self, issues: List[ValidationIssue]) -> ValidationResult:
        """Determine overall validation result based on issues."""
        if not issues:
            return ValidationResult.PASSED
        
        # Check for critical issues
        critical_count = sum(1 for issue in issues if issue.severity == Severity.CRITICAL)
        if critical_count > 0:
            return ValidationResult.FAILED
        
        # Check for high severity issues
        high_count = sum(1 for issue in issues if issue.severity == Severity.HIGH)
        if high_count > 0:
            return ValidationResult.FAILED
        
        # If only medium/low issues, it's a warning
        return ValidationResult.WARNING
    
    def _calculate_quality_score(self, issues: List[ValidationIssue]) -> float:
        """Calculate quality score based on issues found."""
        if not issues:
            return 100.0
        
        # Penalty points by severity
        penalties = {
            Severity.LOW: 2,
            Severity.MEDIUM: 5,
            Severity.HIGH: 15,
            Severity.CRITICAL: 30
        }
        
        total_penalty = sum(penalties.get(issue.severity, 5) for issue in issues)
        
        # Start with 100 and subtract penalties
        score = max(0.0, 100.0 - total_penalty)
        
        return score
    
    def _get_file_extension_from_mime_type(self, mime_type: str) -> str:
        """Get file extension from MIME type."""
        extension_map = {
            'text/html': 'html',
            'application/xhtml+xml': 'html',
            'application/json': 'json',
            'application/pdf': 'pdf',
            'text/plain': 'text',
            'text/css': 'css',
            'application/javascript': 'js'
        }
        
        return extension_map.get(mime_type, 'unknown')
    
    # Public API methods
    
    async def get_validation_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Get validation report by ID."""
        if report_id in self.validation_reports:
            return asdict(self.validation_reports[report_id])
        return None
    
    async def is_content_valid(self, report_id: str) -> bool:
        """Check if content passed validation."""
        if report_id in self.validation_reports:
            return self.validation_reports[report_id].overall_result == ValidationResult.PASSED
        return False
    
    def register_custom_validator(self, name: str, validator_function: callable):
        """Register a custom validation function."""
        self.custom_validators[name] = validator_function
        self.logger.info(f"Registered custom validator: {name}")
    
    def list_validation_reports(self, limit: int = None) -> List[Dict[str, Any]]:
        """List validation reports."""
        reports = list(self.validation_reports.values())
        reports.sort(key=lambda r: r.validation_timestamp, reverse=True)
        
        if limit:
            reports = reports[:limit]
        
        return [asdict(report) for report in reports]
    
    def get_quality_metrics(self) -> Dict[str, Any]:
        """Get quality metrics and statistics."""
        return {
            'total_validations': self.stats['validations_performed'],
            'average_quality_score': self.stats['average_quality_score'],
            'total_issues': self.stats['issues_found'],
            'critical_issues': self.stats['critical_issues'],
            'failed_validations': self.stats['failed_validations'],
            'success_rate': (self.stats['validations_performed'] - self.stats['failed_validations']) / max(1, self.stats['validations_performed']) * 100,
            'validation_types': self.stats['validation_types'].copy()
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current OCVM status."""
        return {
            'module': self.module_name,
            'active': self.is_active,
            'enabled_validations': list(self.enabled_validations),
            'custom_validators': list(self.custom_validators.keys()),
            'reports_stored': len(self.validation_reports),
            'quality_threshold': self.quality_threshold,
            'stats': self.stats.copy()
        } 