"""
Debug version of test_o00000038 to identify issues
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

async def debug_test_o00000038():
    """Debug version of test_o00000038"""
    
    try:
        # Import PRFPM module
        from PRFPM.prfpm import PDFReportFormatProducerModule, PDFEngine, PDFSettings, PageSize, Orientation
        
        print("✅ PRFPM module imported successfully")
        
        # Create temporary test directory
        test_dir = tempfile.mkdtemp(prefix="debug_prfpm_")
        output_dir = os.path.join(test_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"✅ Test directory created: {test_dir}")
        
        # Simple configuration
        config = {
            "pdf_generation": {
                "output_directory": output_dir,
                "temp_directory": os.path.join(test_dir, "temp"),
                "default_engine": "reportlab",
                "enable_compression": True,
                "enable_optimization": True
            }
        }
        
        print("✅ Configuration created")
        
        # Initialize PRFPM
        prfpm = PDFReportFormatProducerModule(config)
        await prfpm.start()
        
        print(f"✅ PRFPM initialized, is_active: {prfpm.is_active}")
        
        # Check available engines
        available_engines = prfpm.get_available_engines()
        print(f"✅ Available engines: {available_engines}")
        
        if not available_engines:
            print("❌ No PDF engines available")
            return
        
        # Use the first available engine
        first_engine = available_engines[0]
        if first_engine == "weasyprint":
            engine = PDFEngine.WEASYPRINT
        elif first_engine == "reportlab":
            engine = PDFEngine.REPORTLAB
        elif first_engine == "chromium":
            engine = PDFEngine.CHROMIUM
        else:
            engine = PDFEngine.REPORTLAB
        
        print(f"✅ Using engine: {engine.value}")
        
        # Simple HTML content
        simple_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Document</title>
        </head>
        <body>
            <h1>Test Document</h1>
            <p>This is a simple test document.</p>
        </body>
        </html>
        """
        
        print("✅ HTML content created")
        
        # Create PDF settings
        pdf_settings = PDFSettings(
            page_size=PageSize.A4,
            orientation=Orientation.PORTRAIT,
            dpi=300,
            compress=True,
            engine=engine
        )
        
        print("✅ PDF settings created")
        
        # Try to generate PDF
        print("🔄 Attempting PDF generation...")
        pdf_id = await prfpm.generate_pdf_from_html(
            html_content=simple_html,
            settings=pdf_settings
        )
        
        print(f"✅ PDF generated successfully, ID: {pdf_id}")
        
        # Get PDF info
        pdf_info = await prfpm.get_pdf_info(pdf_id)
        print(f"✅ PDF info: {pdf_info}")
        
        # Cleanup
        await prfpm.stop()
        
        # Clean up test directory
        try:
            import shutil
            shutil.rmtree(test_dir)
            print("✅ Test directory cleaned up")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")
        
        print("✅ Debug test completed successfully")
        
    except Exception as e:
        print(f"❌ Error in debug test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_test_o00000038()) 