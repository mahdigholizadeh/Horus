"""
Debug script to test OCVM module and identify issues
"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def debug_ocvm():
    """Debug OCVM module issues."""
    try:
        print("Testing OCVM module import...")
        from OCVM.ocvm import OutputCheckValidityModule
        
        print("Creating OCVM instance...")
        config = {
            'output_validation': {
                'enabled_validations': ['content_integrity', 'format_compliance', 'completeness', 'size_limits'],
                'max_file_size_mb': 50,
                'quality_threshold': 80
            }
        }
        
        ocvm = OutputCheckValidityModule(config)
        print(f"OCVM created: {ocvm}")
        print(f"OCVM has health_check: {hasattr(ocvm, 'health_check')}")
        print(f"OCVM has validate_content: {hasattr(ocvm, 'validate_content')}")
        
        print("Starting OCVM...")
        await ocvm.start()
        print(f"OCVM is_active: {ocvm.is_active}")
        
        print("Testing health check...")
        health_result = await ocvm.health_check()
        print(f"Health result: {health_result}")
        
        print("Testing content validation...")
        test_html = "<html><head><title>Test</title></head><body><h1>Test</h1></body></html>"
        report_id = await ocvm.validate_content(
            content=test_html,
            content_type="text/html",
            content_id="test_001"
        )
        print(f"Validation report ID: {report_id}")
        
        print("Testing validation report retrieval...")
        report = await ocvm.get_validation_report(report_id)
        print(f"Report: {report}")
        
        print("Testing is_content_valid...")
        is_valid = await ocvm.is_content_valid(report_id)
        print(f"Is valid: {is_valid}")
        
        print("Testing get_status...")
        status = ocvm.get_status()
        print(f"Status: {status}")
        
        print("Testing get_quality_metrics...")
        metrics = ocvm.get_quality_metrics()
        print(f"Metrics: {metrics}")
        
        print("OCVM module test completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error testing OCVM: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(debug_ocvm()) 