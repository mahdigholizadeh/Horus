"""
Test T00000006: OPM (Output Processing Module) Unit Test
Module(s) Tested: OPM
Description: To ensure the OPM correctly formats the final output, including analysis results and the legacy JFA_flag.
Success Criteria: Output is well-structured JSON, contains JFA_flag, encapsulates all analysis metadata.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from OPM.opm import OutputProcessingModule

async def test_t00000006():
    test_code = "T00000006"
    test_name = "OPM - Output Processing Module Unit Test"
    results = []
    
    opm = OutputProcessingModule()
    await opm.start()
    
    try:
        # Step 1: Provide the OPM with a set of analysis results from the DAM and BDM
        analysis_results = {
            "validation": {
                "valid": True,
                "processing_time": 0.15,
                "validation_rules_passed": 12,
                "validation_rules_failed": 0
            },
            "binary_generation": {
                "success": True,
                "file_path": "/tmp/analysis_result_001.bin",
                "file_size": 2048,
                "checksum": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
                "compression_ratio": 0.75
            },
            "analysis": {
                "quality_score": 0.92,
                "decision": "approve",
                "anomalies_detected": [],
                "recommendations": [
                    "System configuration is optimal",
                    "Consider adding battery storage for better efficiency"
                ],
                "technical_metrics": {
                    "efficiency_rating": "A+",
                    "reliability_score": 0.95,
                    "performance_index": 0.88
                }
            },
            "metadata": {
                "request_id": "REQ-001",
                "processing_timestamp": "2024-01-15T10:30:00Z",
                "modules_used": ["JDPM", "TVM", "BDM", "DAM"],
                "version": "1.0.0"
            }
        }
        
        result = await opm.generate_output(analysis_results, analysis_results)
        
        # Check if output generation was successful
        results.append(result.get("success", False))
        
        if result.get("success", False):
            output_data = result.get("output", {})
            
            # Check if output is well-structured JSON
            results.append(isinstance(output_data, dict))
            
            # Check if output contains JFA_flag
            results.append("JFA_flag" in output_data)
            
            # Check if JFA_flag has appropriate value
            jfa_flag = output_data.get("JFA_flag", None)
            results.append(jfa_flag in [0, 1, True, False])
            
            # Check if output encapsulates all analysis metadata
            required_fields = [
                "validation", "binary_generation", "analysis", 
                "metadata", "processing_summary", "modules_used"
            ]
            
            fields_present = all(field in output_data for field in required_fields)
            results.append(fields_present)
            
            # Check if processing summary is included
            processing_summary = output_data.get("processing_summary", {})
            summary_fields = ["total_processing_time", "success", "modules_executed"]
            summary_complete = all(field in processing_summary for field in summary_fields)
            results.append(summary_complete)
            
            # Check if modules used are correctly listed
            modules_used = output_data.get("modules_used", [])
            expected_modules = ["JDPM", "TVM", "BDM", "DAM"]
            modules_correct = all(module in modules_used for module in expected_modules)
            results.append(modules_correct)
        else:
            # If output generation failed, all subsequent checks should be False
            results.extend([False, False, False, False, False, False])
        
        success = all(results)
        
        return {
            "success": success,
            "test_code": test_code,
            "test_name": test_name,
            "message": "OPM unit test passed" if success else "OPM unit test failed",
            "details": {
                "output_generation_successful": results[0],
                "output_is_structured_json": results[1] if len(results) > 1 else False,
                "contains_jfa_flag": results[2] if len(results) > 2 else False,
                "jfa_flag_has_valid_value": results[3] if len(results) > 3 else False,
                "encapsulates_analysis_metadata": results[4] if len(results) > 4 else False,
                "processing_summary_included": results[5] if len(results) > 5 else False,
                "modules_used_correctly_listed": results[6] if len(results) > 6 else False,
                "output_structure": result.get("output", {}) if result.get("success") else {},
                "results": results
            }
        }
        
    finally:
        await opm.stop()