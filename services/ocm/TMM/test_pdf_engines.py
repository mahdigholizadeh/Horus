#!/usr/bin/env python3
"""
Test PDF Engine Detection
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_pdf_engines():
    """Test PDF engine detection."""
    print("Testing PDF Engine Detection")
    print("=" * 40)
    
    try:
        # Test WeasyPrint
        print("Testing WeasyPrint...")
        try:
            import weasyprint
            print("✅ WeasyPrint imported successfully")
            
            # Test basic functionality
            html = weasyprint.HTML(string="<html><body><h1>Test</h1></body></html>")
            print("✅ WeasyPrint HTML object created successfully")
            
        except Exception as e:
            print(f"❌ WeasyPrint failed: {e}")
        
        print()
        
        # Test ReportLab
        print("Testing ReportLab...")
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4
            print("✅ ReportLab imported successfully")
            
            # Test basic functionality
            import io
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=A4)
            c.drawString(100, 750, "Test PDF")
            c.save()
            print("✅ ReportLab PDF generation successful")
            
        except Exception as e:
            print(f"❌ ReportLab failed: {e}")
        
        print()
        
        # Test PRFPM module
        print("Testing PRFPM Module...")
        try:
            from PRFPM.prfpm import PDFReportFormatProducerModule, PDFEngine
            
            config = {
                'report_generation': {
                    'pdf_settings': {
                        'default_engine': 'reportlab',
                        'output_directory': 'test_output',
                        'temp_directory': 'test_temp'
                    }
                }
            }
            
            prfpm = PDFReportFormatProducerModule(config)
            print(f"✅ PRFPM initialized successfully")
            print(f"   Available engines: {[e.value for e in prfpm.available_engines]}")
            print(f"   Default engine: {prfpm.default_engine.value}")
            
        except Exception as e:
            print(f"❌ PRFPM failed: {e}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_pdf_engines() 