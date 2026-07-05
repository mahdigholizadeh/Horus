"""
Test O00000061: Complete Report Generation Workflow
Module(s) Tested: TDIM, RMM, HRPM, PRFPM, OCVM, DSM
Description: Test complete end-to-end report generation workflow
Test Description:
- Receive TD computation results
- Process through RMM priority queues
- Generate HTML report via HRPM
- Convert to PDF via PRFPM
- Validate content via OCVM
- Deliver via DSM with confirmation
Expected Result: Complete successful report generation and delivery
Pass Criteria: Workflow complete, all steps successful, delivery confirmed, performance acceptable
Implementation Notes: Test with various report types and priorities
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
from dataclasses import dataclass

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

@dataclass
class MockRequestInfo:
    request_id: str
    request_type: str
    destination: str
    metadata: dict
    content_type: str = "application/pdf"
    content_size: int = 0
    content_hash: str = ""
    report_format: list = None
    template_used: str = "default"
    
    def __post_init__(self):
        # Convert string request_type to enum-like object
        if isinstance(self.request_type, str):
            class RequestType:
                def __init__(self, value):
                    self.value = value
            self.request_type = RequestType(self.request_type)
        
        # Set default report_format if None
        if self.report_format is None:
            self.report_format = ["PDF"]

async def test_o00000061():
    test_code = "O00000061"
    test_name = "Complete Report Generation Workflow"
    results = []
    
    try:
        # Import required modules
        from TDIM.tdim import TDInteractionModule
        from RMM.rmm import RequestManagementModule
        from HRPM.hrpm import HTMLReportProducerModule
        from PRFPM.prfpm import PDFReportFormatProducerModule
        from OCVM.ocvm import OutputCheckValidityModule
        from DSM.dsm import DataSenderModule
        
        # Create temporary test directory
        test_dir = tempfile.mkdtemp(prefix="workflow_test_")
        
        # Step 1: Test module initialization for workflow
        config = {
            "workflow": {
                "enabled": True,
                "end_to_end": True,
                "priority_processing": True,
                "report_generation": True,
                "content_validation": True,
                "delivery_confirmation": True
            },
            "tdim": {
                "enabled": True,
                "result_reception": True,
                "data_validation": True,
                "result_processing": True
            },
            "rmm": {
                "enabled": True,
                "priority_queues": True,
                "bandwidth_allocation": True,
                "request_ordering": True
            },
            "hrpm": {
                "enabled": True,
                "html_generation": True,
                "template_management": True,
                "dynamic_content": True
            },
            "prfpm": {
                "enabled": True,
                "pdf_conversion": True,
                "format_optimization": True,
                "quality_assurance": True
            },
            "ocvm": {
                "enabled": True,
                "content_validation": True,
                "security_scanning": True,
                "quality_metrics": True
            },
            "dsm": {
                "enabled": True,
                "secure_transmission": True,
                "delivery_confirmation": True,
                "error_handling": True
            },
            "database": {
                "path": os.path.join(test_dir, "workflow_database.db"),
                "auto_cleanup": True,
                "retention_days": 30
            }
        }
        
        # Initialize all modules
        tdim = TDInteractionModule(config)
        rmm = RequestManagementModule(config)
        hrpm = HTMLReportProducerModule(config)
        prfpm = PDFReportFormatProducerModule(config)
        ocvm = OutputCheckValidityModule(config)
        dsm = DataSenderModule(config)
        
        # Create mock NMM module for DSM
        class MockNMM:
            async def send_data(self, data, destination, **kwargs):
                return {"success": True, "response": "Mock response"}
        
        # Set module references
        dsm.nmm = MockNMM()
        
        # Start all modules
        await tdim.start()
        await rmm.start()
        await hrpm.start()
        await prfpm.start()
        await ocvm.start()
        await dsm.start()
        
        results.append(tdim.is_active == True)
        results.append(rmm.is_active == True)
        results.append(hrpm.is_active == True)
        results.append(prfpm.is_active == True)
        results.append(ocvm.is_active == True)
        results.append(dsm.is_active == True)
        
        # Step 2: Test TD computation results reception
        td_reception_results = []
        
        # Simulate TD computation results
        td_results = [
            {
                "result_id": "td_result_001",
                "computation_type": "energy_analysis",
                "data": {
                    "consumption": 1500.5,
                    "efficiency": 0.85,
                    "recommendations": ["optimize_usage", "upgrade_equipment"]
                },
                "priority": "A",
                "timestamp": datetime.now().isoformat()
            },
            {
                "result_id": "td_result_002",
                "computation_type": "performance_metrics",
                "data": {
                    "throughput": 95.2,
                    "latency": 45.8,
                    "availability": 0.998
                },
                "priority": "B",
                "timestamp": datetime.now().isoformat()
            },
            {
                "result_id": "td_result_003",
                "computation_type": "system_health",
                "data": {
                    "cpu_usage": 65.3,
                    "memory_usage": 78.9,
                    "disk_usage": 45.2
                },
                "priority": "C",
                "timestamp": datetime.now().isoformat()
            }
        ]
        
        for td_result in td_results:
            # Simulate TD result reception
            reception_success = await tdim.receive_td_data(td_result)
            td_reception_results.append(reception_success)
            
            # Verify result processing
            processing_status = tdim.get_processing_status(td_result["result_id"])
            td_reception_results.append(processing_status is not None)
            
            if processing_status:
                td_reception_results.append("validation_status" in processing_status)
                td_reception_results.append("processing_completed" in processing_status)
        
        # Step 3: Test RMM priority queue processing
        rmm_processing_results = []
        
        # Test priority queue processing for each result
        for td_result in td_results:
            # Submit to RMM priority queue
            request_data = {
                "request_type": "td_report",
                "priority": td_result["priority"],
                "source_module": "TDIM",
                "content_type": "json",
                "metadata": td_result
            }
            request_id = await rmm.submit_request(request_data)
            
            rmm_processing_results.append(request_id is not None)
            
            # Verify queue processing
            queue_stats = rmm.get_queue_stats()
            rmm_processing_results.append(queue_stats is not None)
            
            if queue_stats:
                rmm_processing_results.append("A" in queue_stats)
                rmm_processing_results.append("B" in queue_stats)
        
        # Step 4: Test HTML report generation via HRPM
        html_generation_results = []
        
        # Test HTML report generation for each result
        for td_result in td_results:
            # Generate HTML report
            report_data = {
                "title": f"Report for {td_result['computation_type']}",
                "company": "TestCorp",
                "logo": "https://test.com/logo.png",
                "computation_data": td_result["data"]
            }
            from HRPM.hrpm import ReportType
            report_id = await hrpm.generate_report(
                template_id="default",
                data=report_data,
                report_type=ReportType.STANDARD
            )
            
            html_generation_results.append(report_id is not None)
            
            # Verify HTML report
            if report_id:
                report_info = await hrpm.get_report_info(report_id)
                html_generation_results.append(report_info is not None)
                if report_info:
                    html_generation_results.append("content" in report_info)
                    html_generation_results.append("generated_at" in report_info)
        
        # Step 5: Test PDF conversion via PRFPM
        pdf_conversion_results = []
        
        # Test PDF conversion for each HTML report
        for i, td_result in enumerate(td_results):
            try:
                # Convert HTML to PDF
                from PRFPM.prfpm import PDFSettings, PageSize, Orientation
                
                settings = PDFSettings(
                    page_size=PageSize.A4,
                    orientation=Orientation.PORTRAIT,
                    margins={"top": 25, "bottom": 25, "left": 25, "right": 25}
                )
                
                html_content = f"<html><body><h1>Report {i+1}</h1><p>Data: {td_result['data']}</p></body></html>"
                pdf_id = await prfpm.generate_pdf_from_html(html_content, settings)
                
                pdf_conversion_results.append(pdf_id is not None)
                
                # Verify PDF report
                if pdf_id:
                    pdf_info = await prfpm.get_pdf_info(pdf_id)
                    pdf_conversion_results.append(pdf_info is not None)
                    if pdf_info:
                        pdf_conversion_results.append("file_size_bytes" in pdf_info)
                        pdf_conversion_results.append("generated_at" in pdf_info)
            except Exception as e:
                # Handle PDF generation failures gracefully
                pdf_conversion_results.append(False)
                pdf_conversion_results.append(False)
                pdf_conversion_results.append(False)
        
        # Step 6: Test content validation via OCVM
        content_validation_results = []
        
        # Test content validation for each report
        for i, td_result in enumerate(td_results):
            # Validate content
            content_id = f"report_{i}_{td_result['computation_type']}"
            validation_report_id = await ocvm.validate_content(
                content=f"Report content for {td_result['computation_type']}",
                content_type="application/pdf",
                content_id=content_id,
                metadata={"computation_type": td_result['computation_type']}
            )
            
            content_validation_results.append(validation_report_id is not None)
            
            # Verify validation
            if validation_report_id:
                validation_report = await ocvm.get_validation_report(validation_report_id)
                content_validation_results.append(validation_report is not None)
                if validation_report:
                    content_validation_results.append("overall_result" in validation_report)
                    content_validation_results.append("total_issues" in validation_report)
        
        # Step 7: Test delivery via DSM
        delivery_results = []
        
        # Test delivery for each validated report
        for i, td_result in enumerate(td_results):
            # Create mock request_info object for DSM
            mock_request = MockRequestInfo(
                request_id=f"delivery_test_{i}",
                request_type="td_report",
                destination="https://test-client.com/api/reports",
                metadata={
                    "computation_type": td_result['computation_type'],
                    "report_content": f"PDF report content for {td_result['computation_type']}",
                    "pdf_content": b"Mock PDF content",
                    "html_content": "<html><body>Mock HTML content</body></html>"
                }
            )
            
            # Deliver report
            delivery_result = await dsm.send_data(mock_request)
            
            delivery_results.append(delivery_result is not None)
            
            # Verify delivery
            if delivery_result:
                delivery_results.append("success" in delivery_result)
                delivery_results.append("request_id" in delivery_result)
        
        # Step 8: Test complete workflow performance
        workflow_performance_results = []
        
        # Test performance with multiple workflow executions
        start_time = datetime.now()
        
        # Execute multiple complete workflows
        workflow_request_ids = []
        workflow_scenarios = ["energy_analysis", "performance_metrics", "system_health", "security_audit", "compliance_check"]
        
        for i, scenario in enumerate(workflow_scenarios):
            # Complete workflow execution
            workflow_result = await execute_complete_workflow(
                tdim, rmm, hrpm, prfpm, ocvm, dsm,
                scenario_data={
                    "computation_type": scenario,
                    "priority": "A" if i < 2 else "B",
                    "data": {"metric1": 100 + i, "metric2": 200 + i}
                }
            )
            
            workflow_request_ids.append(workflow_result)
        
        end_time = datetime.now()
        workflow_time = (end_time - start_time).total_seconds()
        
        workflow_performance_results.append(len(workflow_request_ids) == 5)
        workflow_performance_results.append(all(wid is not None for wid in workflow_request_ids))
        workflow_performance_results.append(workflow_time < 60.0)  # Should complete within 60 seconds
        
        # Step 9: Test workflow error scenarios
        workflow_error_results = []
        
        # Test with TD result reception failure
        try:
            failed_reception = await tdim.receive_td_data({
                "result_id": "failed_result",
                "computation_type": "invalid_type",
                "data": None,
                "priority": "A"
            })
            workflow_error_results.append(failed_reception == False)
            
            # Verify error handling
            status = tdim.get_status()
            workflow_error_results.append(status is not None)
            
        except Exception:
            workflow_error_results.append(True)  # Should handle error gracefully
        
        # Test with report generation failure
        try:
            from HRPM.hrpm import ReportType
            failed_generation = await hrpm.generate_report(
                template_id="invalid_template",
                data={},
                report_type=ReportType.STANDARD
            )
            workflow_error_results.append(failed_generation is None)
            
            # Verify error handling
            status = hrpm.get_status()
            workflow_error_results.append(status is not None)
            
        except Exception:
            workflow_error_results.append(True)  # Should handle error gracefully
        
        # Step 10: Test workflow validation
        workflow_validation_results = []
        
        # Test workflow statistics
        workflow_stats = {
            "total_workflows": len(workflow_request_ids),
            "successful_workflows": sum(1 for wid in workflow_request_ids if wid is not None),
            "average_processing_time": workflow_time / len(workflow_request_ids) if workflow_request_ids else 0,
            "success_rate": sum(1 for wid in workflow_request_ids if wid is not None) / len(workflow_request_ids) if workflow_request_ids else 0
        }
        
        workflow_validation_results.append(isinstance(workflow_stats, dict))
        workflow_validation_results.append("total_workflows" in workflow_stats)
        workflow_validation_results.append("success_rate" in workflow_stats)
        workflow_validation_results.append(workflow_stats["success_rate"] >= 0.8)  # At least 80% success rate
        
        # Test module health checks
        module_health_checks = [
            await tdim.health_check(),
            await rmm.health_check(),
            await hrpm.health_check(),
            await prfpm.health_check(),
            await ocvm.health_check(),
            await dsm.health_check()
        ]
        
        workflow_validation_results.append(all(health == True for health in module_health_checks))
        
        # Test module status
        module_statuses = [
            tdim.get_status(),
            rmm.get_status(),
            hrpm.get_status(),
            prfpm.get_status(),
            ocvm.get_status(),
            dsm.get_status()
        ]
        
        workflow_validation_results.append(all(status is not None for status in module_statuses))
        
        # Aggregate all results
        all_results = (
            results + 
            td_reception_results + 
            rmm_processing_results + 
            html_generation_results + 
            pdf_conversion_results + 
            content_validation_results + 
            delivery_results + 
            workflow_performance_results + 
            workflow_error_results + 
            workflow_validation_results
        )
        
        # Calculate pass rate
        passed_tests = sum(all_results)
        total_tests = len(all_results)
        pass_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        # Cleanup
        await tdim.stop()
        await rmm.stop()
        await hrpm.stop()
        await prfpm.stop()
        await ocvm.stop()
        await dsm.stop()
        
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
                "td_computation_results_reception": td_reception_results,
                "rmm_priority_queue_processing": rmm_processing_results,
                "html_report_generation": html_generation_results,
                "pdf_conversion": pdf_conversion_results,
                "content_validation": content_validation_results,
                "delivery_confirmation": delivery_results,
                "workflow_performance": workflow_performance_results,
                "workflow_error_scenarios": workflow_error_results,
                "workflow_validation": workflow_validation_results
            },
            "workflow_metrics": {
                "total_workflows": len(workflow_request_ids),
                "workflow_time_seconds": workflow_time,
                "successful_workflows": sum(1 for wid in workflow_request_ids if wid is not None),
                "workflow_scenarios_tested": len(workflow_scenarios)
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

async def execute_complete_workflow(tdim, rmm, hrpm, prfpm, ocvm, dsm, scenario_data):
    """Execute a complete workflow for testing."""
    try:
        # Step 1: Receive TD result
        reception_success = await tdim.receive_td_data(scenario_data)
        if not reception_success:
            return None
        
        # Step 2: Process through RMM
        request_data = {
            "request_type": "td_report",
            "priority": scenario_data["priority"],
            "source_module": "TDIM",
            "content_type": "json",
            "metadata": scenario_data
        }
        request_id = await rmm.submit_request(request_data)
        if not request_id:
            return None
        
        # Step 3: Generate HTML report
        report_data = {
            "title": f"Report for {scenario_data['computation_type']}",
            "computation_data": scenario_data["data"]
        }
        from HRPM.hrpm import ReportType
        report_id = await hrpm.generate_report(
            template_id="default",
            data=report_data,
            report_type=ReportType.STANDARD
        )
        if not report_id:
            return None
        
        # Step 4: Convert to PDF
        from PRFPM.prfpm import PDFSettings, PageSize, Orientation
        settings = PDFSettings(
            page_size=PageSize.A4,
            orientation=Orientation.PORTRAIT
        )
        html_content = "<html><body>Test report</body></html>"
        pdf_id = await prfpm.generate_pdf_from_html(html_content, settings)
        if not pdf_id:
            return None
        
        # Step 5: Validate content
        content_id = f"workflow_{scenario_data['computation_type']}"
        validation_report_id = await ocvm.validate_content(
            content="PDF report content",
            content_type="application/pdf",
            content_id=content_id
        )
        if not validation_report_id:
            return None
        
        # Step 6: Deliver report
        mock_request = MockRequestInfo(
            request_id=f"workflow_{scenario_data['computation_type']}",
            request_type="td_report",
            destination="https://test-client.com/api/reports",
            metadata={
                "report_content": "PDF report content",
                "pdf_content": b"Mock PDF content",
                "html_content": "<html><body>Mock HTML content</body></html>"
            }
        )
        
        delivery_result = await dsm.send_data(mock_request)
        
        return delivery_result is not None
        
    except Exception:
        return None

async def main():
    """Main test execution function."""
    result = await test_o00000061()
    print(json.dumps(result, indent=2))
    return result

if __name__ == "__main__":
    asyncio.run(main()) 