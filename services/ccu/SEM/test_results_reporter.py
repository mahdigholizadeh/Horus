"""
Test Results Reporter - SEM Component

Generates comprehensive reports of SEM execution results including:
- Detailed test outcomes
- Performance metrics
- Error analysis
- System health assessment
- Recommendations for system administrators
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import asdict
import csv


class TestResultsReporter:
    """Generates and manages SEM test execution reports."""
    
    def __init__(self):
        """Initialize the test results reporter."""
        self.logger = logging.getLogger(f'{__name__}.TestResultsReporter')
        
        # Report output directories
        self.reports_dir = Path("logs/sem_reports")
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Report templates and formats
        self.supported_formats = ["json", "html", "csv", "txt"]
        
        self.logger.info("TestResultsReporter initialized")
    
    async def generate_final_report(self, execution_report) -> bool:
        """
        Generate comprehensive final report for SEM execution.
        
        Args:
            execution_report: SEMExecutionReport object
            
        Returns:
            True if report generation successful, False otherwise
        """
        try:
            self.logger.info("�📊 Generating comprehensive SEM execution report")
            
            # Generate timestamp for report
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            operation = execution_report.operation.value
            
            # Create report data structure
            report_data = self._create_comprehensive_report_data(execution_report)
            
            # Generate reports in multiple formats
            success_count = 0
            
            # JSON Report (detailed technical data)
            json_success = await self._generate_json_report(
                report_data, f"sem_execution_{operation}_{timestamp}.json"
            )
            if json_success:
                success_count += 1
            
            # HTML Report (human-readable dashboard)
            html_success = await self._generate_html_report(
                report_data, f"sem_execution_{operation}_{timestamp}.html"
            )
            if html_success:
                success_count += 1
            
            # CSV Report (for data analysis)
            csv_success = await self._generate_csv_report(
                report_data, f"sem_execution_{operation}_{timestamp}.csv"
            )
            if csv_success:
                success_count += 1
            
            # Text Summary (for logs and quick review)
            txt_success = await self._generate_text_summary(
                report_data, f"sem_execution_{operation}_{timestamp}.txt"
            )
            if txt_success:
                success_count += 1
            
            # Generate latest symlinks for easy access
            await self._create_latest_symlinks(operation, timestamp)
            
            self.logger.info(f"✅ Generated {success_count}/{len(self.supported_formats)} report formats")
            
            return success_count > 0
            
        except Exception as e:
            self.logger.error(f"❌ Failed to generate final report: {e}")
            return False
    
    async def save_execution_report(self, execution_report) -> bool:
        """
        Save execution report to persistent storage.
        
        Args:
            execution_report: SEMExecutionReport object
            
        Returns:
            True if save successful, False otherwise
        """
        try:
            # Convert to dictionary for JSON serialization
            report_dict = self._convert_execution_report_to_dict(execution_report)
            
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sem_execution_raw_{timestamp}.json"
            filepath = self.reports_dir / filename
            
            # Save as JSON
            with open(filepath, 'w') as f:
                json.dump(report_dict, f, indent=2, default=str)
            
            self.logger.info(f"✅ Execution report saved: {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to save execution report: {e}")
            return False
    
    def _create_comprehensive_report_data(self, execution_report) -> Dict[str, Any]:
        """Create comprehensive report data structure."""
        # Convert execution report to dict
        raw_data = self._convert_execution_report_to_dict(execution_report)
        
        # Calculate summary metrics
        total_checks = len(execution_report.check_results)
        successful_checks = sum(1 for check in execution_report.check_results if check.success)
        failed_checks = total_checks - successful_checks
        
        # Calculate average durations
        check_durations = [check.duration_seconds for check in execution_report.check_results]
        avg_duration = sum(check_durations) / len(check_durations) if check_durations else 0
        
        # Categorize checks by phase
        checks_by_phase = {}
        for check in execution_report.check_results:
            phase = self._determine_check_phase(check.check_name)
            if phase not in checks_by_phase:
                checks_by_phase[phase] = {"total": 0, "successful": 0, "failed": 0}
            
            checks_by_phase[phase]["total"] += 1
            if check.success:
                checks_by_phase[phase]["successful"] += 1
            else:
                checks_by_phase[phase]["failed"] += 1
        
        # Generate recommendations
        recommendations = self._generate_recommendations(execution_report)
        
        # Create comprehensive report
        comprehensive_report = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "report_version": "1.0",
                "sem_version": "1.0",
                "horus_version": "1.0"
            },
            "execution_summary": {
                "operation": execution_report.operation.value,
                "overall_success": execution_report.success,
                "start_time": execution_report.start_time.isoformat(),
                "end_time": execution_report.end_time.isoformat() if execution_report.end_time else None,
                "total_duration_seconds": execution_report.total_duration,
                "final_phase": execution_report.phase.value,
                "error_summary": execution_report.error_summary
            },
            "check_summary": {
                "total_checks": total_checks,
                "successful_checks": successful_checks,
                "failed_checks": failed_checks,
                "success_rate": (successful_checks / total_checks * 100) if total_checks > 0 else 0,
                "average_duration_seconds": avg_duration,
                "checks_by_phase": checks_by_phase
            },
            "service_summary": {
                "services_started": execution_report.services_started or [],
                "total_services": len(execution_report.services_started) if execution_report.services_started else 0
            },
            "performance_metrics": {
                "fastest_check": min(execution_report.check_results, key=lambda x: x.duration_seconds).check_name if execution_report.check_results else None,
                "slowest_check": max(execution_report.check_results, key=lambda x: x.duration_seconds).check_name if execution_report.check_results else None,
                "total_execution_time": execution_report.total_duration,
                "efficiency_score": self._calculate_efficiency_score(execution_report)
            },
            "detailed_results": raw_data,
            "recommendations": recommendations,
            "system_health_assessment": self._assess_system_health(execution_report)
        }
        
        return comprehensive_report
    
    def _determine_check_phase(self, check_name: str) -> str:
        """Determine which phase a check belongs to."""
        check_name_lower = check_name.lower()
        
        if "configuration" in check_name_lower or "validation" in check_name_lower:
            return "Configuration Validation"
        elif "blocking" in check_name_lower or "gateway" in check_name_lower:
            return "Request Blocking"
        elif "service" in check_name_lower or "activation" in check_name_lower:
            return "Service Activation"
        elif "functionality" in check_name_lower or "api" in check_name_lower or "connectivity" in check_name_lower:
            return "Functionality Testing"
        elif "workflow" in check_name_lower or "integration" in check_name_lower:
            return "Workflow Validation"
        elif "finalization" in check_name_lower:
            return "Finalization"
        else:
            return "Other"
    
    def _generate_recommendations(self, execution_report) -> List[Dict[str, Any]]:
        """Generate recommendations based on execution results."""
        recommendations = []
        
        # Check overall success
        if not execution_report.success:
            recommendations.append({
                "priority": "HIGH",
                "category": "System Failure",
                "message": "SEM execution failed. Review error details and resolve issues before attempting restart.",
                "action": "Check logs and address root cause before next startup attempt"
            })
        
        # Check for failed services
        failed_checks = [check for check in execution_report.check_results if not check.success]
        if failed_checks:
            for check in failed_checks:
                recommendations.append({
                    "priority": "MEDIUM",
                    "category": "Check Failure",
                    "message": f"Check '{check.check_name}' failed: {check.message}",
                    "action": "Investigate and resolve the specific issue"
                })
        
        # Performance recommendations
        if execution_report.total_duration and execution_report.total_duration > 120:  # 2 minutes
            recommendations.append({
                "priority": "LOW",
                "category": "Performance",
                "message": "SEM execution took longer than expected. Consider optimizing service startup sequence.",
                "action": "Review service dependencies and startup optimization"
            })
        
        # Configuration recommendations
        config_checks = [check for check in execution_report.check_results if "configuration" in check.check_name.lower()]
        if any(not check.success for check in config_checks):
            recommendations.append({
                "priority": "HIGH",
                "category": "Configuration",
                "message": "Configuration validation failed. Ensure all required settings are properly configured.",
                "action": "Review and update configuration files in ccu_setting directory"
            })
        
        return recommendations
    
    def _assess_system_health(self, execution_report) -> Dict[str, Any]:
        """Assess overall system health based on execution results."""
        health_score = 0
        max_score = 100
        
        # Success rate contributes 40 points
        successful_checks = sum(1 for check in execution_report.check_results if check.success)
        total_checks = len(execution_report.check_results)
        if total_checks > 0:
            health_score += (successful_checks / total_checks) * 40
        
        # Overall success contributes 30 points
        if execution_report.success:
            health_score += 30
        
        # Performance contributes 20 points
        if execution_report.total_duration:
            if execution_report.total_duration <= 60:  # Under 1 minute is excellent
                health_score += 20
            elif execution_report.total_duration <= 120:  # Under 2 minutes is good
                health_score += 15
            elif execution_report.total_duration <= 180:  # Under 3 minutes is acceptable
                health_score += 10
            else:
                health_score += 5
        
        # Service startup contributes 10 points
        if execution_report.services_started:
            expected_services = 7  # RLA, RCM, TPP, TD, JFA, OCM, CCU
            actual_services = len(execution_report.services_started)
            health_score += (actual_services / expected_services) * 10
        
        # Determine health status
        if health_score >= 90:
            health_status = "EXCELLENT"
        elif health_score >= 75:
            health_status = "GOOD"
        elif health_score >= 60:
            health_status = "FAIR"
        elif health_score >= 40:
            health_status = "POOR"
        else:
            health_status = "CRITICAL"
        
        return {
            "health_score": round(health_score, 1),
            "health_status": health_status,
            "assessment_time": datetime.now().isoformat(),
            "components": {
                "check_success_rate": (successful_checks / total_checks * 100) if total_checks > 0 else 0,
                "overall_execution": "PASS" if execution_report.success else "FAIL",
                "performance_rating": self._rate_performance(execution_report.total_duration),
                "service_startup": f"{len(execution_report.services_started or [])}/7 services"
            }
        }
    
    def _rate_performance(self, duration: Optional[float]) -> str:
        """Rate performance based on execution duration."""
        if not duration:
            return "UNKNOWN"
        
        if duration <= 60:
            return "EXCELLENT"
        elif duration <= 120:
            return "GOOD"
        elif duration <= 180:
            return "ACCEPTABLE"
        elif duration <= 300:
            return "SLOW"
        else:
            return "VERY_SLOW"
    
    def _calculate_efficiency_score(self, execution_report) -> float:
        """Calculate efficiency score based on execution metrics."""
        if not execution_report.check_results:
            return 0.0
        
        # Base score from success rate
        successful_checks = sum(1 for check in execution_report.check_results if check.success)
        total_checks = len(execution_report.check_results)
        success_rate = successful_checks / total_checks
        
        # Adjust for performance
        performance_multiplier = 1.0
        if execution_report.total_duration:
            if execution_report.total_duration <= 60:
                performance_multiplier = 1.2  # Bonus for fast execution
            elif execution_report.total_duration > 180:
                performance_multiplier = 0.8  # Penalty for slow execution
        
        efficiency_score = success_rate * performance_multiplier * 100
        return min(efficiency_score, 100.0)  # Cap at 100
    
    async def _generate_json_report(self, report_data: Dict[str, Any], filename: str) -> bool:
        """Generate JSON format report."""
        try:
            filepath = self.reports_dir / filename
            with open(filepath, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            return True
        except Exception as e:
            self.logger.error(f"Failed to generate JSON report: {e}")
            return False
    
    async def _generate_html_report(self, report_data: Dict[str, Any], filename: str) -> bool:
        """Generate HTML format report."""
        try:
            html_content = self._create_html_template(report_data)
            filepath = self.reports_dir / filename
            with open(filepath, 'w') as f:
                f.write(html_content)
            return True
        except Exception as e:
            self.logger.error(f"Failed to generate HTML report: {e}")
            return False
    
    async def _generate_csv_report(self, report_data: Dict[str, Any], filename: str) -> bool:
        """Generate CSV format report for data analysis."""
        try:
            filepath = self.reports_dir / filename
            
            # Extract check results for CSV
            check_results = report_data.get("detailed_results", {}).get("check_results", [])
            
            with open(filepath, 'w', newline='') as csvfile:
                fieldnames = ['check_name', 'success', 'message', 'duration_seconds', 'timestamp']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for check in check_results:
                    writer.writerow({
                        'check_name': check.get('check_name', ''),
                        'success': check.get('success', False),
                        'message': check.get('message', ''),
                        'duration_seconds': check.get('duration_seconds', 0),
                        'timestamp': check.get('timestamp', '')
                    })
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to generate CSV report: {e}")
            return False
    
    async def _generate_text_summary(self, report_data: Dict[str, Any], filename: str) -> bool:
        """Generate text summary report."""
        try:
            text_content = self._create_text_summary(report_data)
            filepath = self.reports_dir / filename
            with open(filepath, 'w') as f:
                f.write(text_content)
            return True
        except Exception as e:
            self.logger.error(f"Failed to generate text summary: {e}")
            return False
    
    def _create_html_template(self, report_data: Dict[str, Any]) -> str:
        """Create HTML report template."""
        execution_summary = report_data.get("execution_summary", {})
        check_summary = report_data.get("check_summary", {})
        health_assessment = report_data.get("system_health_assessment", {})
        recommendations = report_data.get("recommendations", [])
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Horus SEM Execution Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #2c3e50; color: white; padding: 20px; text-align: center; }}
        .summary {{ background-color: #ecf0f1; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .success {{ color: #27ae60; }}
        .failure {{ color: #e74c3c; }}
        .metric {{ display: inline-block; margin: 10px; padding: 10px; background: white; border-radius: 5px; }}
        .recommendation {{ margin: 10px 0; padding: 10px; border-left: 4px solid #3498db; background: #f8f9fa; }}
        .high-priority {{ border-left-color: #e74c3c; }}
        .medium-priority {{ border-left-color: #f39c12; }}
        .low-priority {{ border-left-color: #27ae60; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Horus SEM Execution Report</h1>
        <p>Generated: {report_data.get("report_metadata", {}).get("generated_at", "")}</p>
    </div>
    
    <div class="summary">
        <h2>Execution Summary</h2>
        <div class="metric">
            <strong>Operation:</strong> {execution_summary.get("operation", "Unknown")}
        </div>
        <div class="metric">
            <strong>Status:</strong> 
            <span class="{'success' if execution_summary.get('overall_success') else 'failure'}">
                {"SUCCESS" if execution_summary.get('overall_success') else "FAILED"}
            </span>
        </div>
        <div class="metric">
            <strong>Duration:</strong> {execution_summary.get("total_duration_seconds", 0):.2f}s
        </div>
        <div class="metric">
            <strong>Health Score:</strong> {health_assessment.get("health_score", 0)}/100 
            ({health_assessment.get("health_status", "Unknown")})
        </div>
    </div>
    
    <div class="summary">
        <h2>Check Results</h2>
        <div class="metric">
            <strong>Total Checks:</strong> {check_summary.get("total_checks", 0)}
        </div>
        <div class="metric">
            <strong>Successful:</strong> <span class="success">{check_summary.get("successful_checks", 0)}</span>
        </div>
        <div class="metric">
            <strong>Failed:</strong> <span class="failure">{check_summary.get("failed_checks", 0)}</span>
        </div>
        <div class="metric">
            <strong>Success Rate:</strong> {check_summary.get("success_rate", 0):.1f}%
        </div>
    </div>
    
    <div class="summary">
        <h2>Recommendations</h2>
        {"".join([f'''
        <div class="recommendation {rec.get("priority", "").lower()}-priority">
            <strong>[{rec.get("priority", "")}] {rec.get("category", "")}</strong><br>
            {rec.get("message", "")}<br>
            <em>Action: {rec.get("action", "")}</em>
        </div>
        ''' for rec in recommendations])}
    </div>
</body>
</html>
        """
        
        return html_content
    
    def _create_text_summary(self, report_data: Dict[str, Any]) -> str:
        """Create text summary report."""
        execution_summary = report_data.get("execution_summary", {})
        check_summary = report_data.get("check_summary", {})
        health_assessment = report_data.get("system_health_assessment", {})
        recommendations = report_data.get("recommendations", [])
        
        text_content = f"""
Horus SEM Execution Report
===========================

Generated: {report_data.get("report_metadata", {}).get("generated_at", "")}

EXECUTION SUMMARY
-----------------
Operation: {execution_summary.get("operation", "Unknown")}
Status: {"SUCCESS" if execution_summary.get('overall_success') else "FAILED"}
Duration: {execution_summary.get("total_duration_seconds", 0):.2f} seconds
Start Time: {execution_summary.get("start_time", "")}
End Time: {execution_summary.get("end_time", "")}

CHECK RESULTS
-------------
Total Checks: {check_summary.get("total_checks", 0)}
Successful: {check_summary.get("successful_checks", 0)}
Failed: {check_summary.get("failed_checks", 0)}
Success Rate: {check_summary.get("success_rate", 0):.1f}%

SYSTEM HEALTH
-------------
Health Score: {health_assessment.get("health_score", 0)}/100
Health Status: {health_assessment.get("health_status", "Unknown")}

RECOMMENDATIONS
---------------
"""
        
        for i, rec in enumerate(recommendations, 1):
            text_content += f"""
{i}. [{rec.get("priority", "")}] {rec.get("category", "")}
   {rec.get("message", "")}
   Action: {rec.get("action", "")}
"""
        
        return text_content
    
    async def _create_latest_symlinks(self, operation: str, timestamp: str):
        """Create symlinks to latest reports for easy access."""
        try:
            for format_ext in self.supported_formats:
                source_file = f"sem_execution_{operation}_{timestamp}.{format_ext}"
                symlink_file = f"latest_sem_execution.{format_ext}"
                
                source_path = self.reports_dir / source_file
                symlink_path = self.reports_dir / symlink_file
                
                # Remove existing symlink if it exists
                if symlink_path.exists() or symlink_path.is_symlink():
                    symlink_path.unlink()
                
                # Create new symlink if source exists
                if source_path.exists():
                    symlink_path.symlink_to(source_file)
                    
        except Exception as e:
            self.logger.warning(f"Failed to create symlinks: {e}")
    
    def _convert_execution_report_to_dict(self, execution_report) -> Dict[str, Any]:
        """Convert SEMExecutionReport to dictionary for JSON serialization."""
        return {
            "operation": execution_report.operation.value,
            "start_time": execution_report.start_time.isoformat(),
            "end_time": execution_report.end_time.isoformat() if execution_report.end_time else None,
            "total_duration": execution_report.total_duration,
            "phase": execution_report.phase.value,
            "success": execution_report.success,
            "error_summary": execution_report.error_summary,
            "services_started": execution_report.services_started or [],
            "check_results": [
                {
                    "check_name": check.check_name,
                    "success": check.success,
                    "message": check.message,
                    "duration_seconds": check.duration_seconds,
                    "timestamp": check.timestamp.isoformat(),
                    "details": check.details
                }
                for check in execution_report.check_results
            ]
        }
    
    def get_latest_report_path(self, format: str = "json") -> Optional[Path]:
        """
        Get path to the latest report in specified format.
        
        Args:
            format: Report format (json, html, csv, txt)
            
        Returns:
            Path to latest report or None if not found
        """
        try:
            symlink_file = f"latest_sem_execution.{format}"
            symlink_path = self.reports_dir / symlink_file
            
            if symlink_path.exists():
                return symlink_path
            return None
            
        except Exception:
            return None
    
    def list_reports(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List recent SEM reports.
        
        Args:
            limit: Maximum number of reports to return
            
        Returns:
            List of report information dictionaries
        """
        try:
            reports = []
            
            # Find all JSON report files
            json_files = list(self.reports_dir.glob("sem_execution_*.json"))
            json_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            for json_file in json_files[:limit]:
                try:
                    with open(json_file, 'r') as f:
                        report_data = json.load(f)
                    
                    reports.append({
                        "filename": json_file.name,
                        "timestamp": report_data.get("start_time", ""),
                        "operation": report_data.get("operation", ""),
                        "success": report_data.get("success", False),
                        "duration": report_data.get("total_duration", 0),
                        "file_size": json_file.stat().st_size
                    })
                except Exception as e:
                    self.logger.warning(f"Failed to read report {json_file}: {e}")
            
            return reports
            
        except Exception as e:
            self.logger.error(f"Failed to list reports: {e}")
            return []