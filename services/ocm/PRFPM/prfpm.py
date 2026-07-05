"""
PDF Report Format Producer Module (PRFPM) for OCM

This module is responsible for converting HTML reports to PDF format, handling PDF 
generation settings, page layouts, styling, and managing PDF output quality and 
optimization for different use cases.
"""

import asyncio
import logging
import json
import os
import tempfile
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
from pathlib import Path
import base64
import subprocess

try:
    import weasyprint
    # Test if WeasyPrint actually works (not just imports)
    weasyprint.HTML(string="<html><body>Test</body></html>")
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError, Exception):
    WEASYPRINT_AVAILABLE = False

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter, A4, legal
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

class PDFEngine(Enum):
    """PDF generation engines."""
    WEASYPRINT = "weasyprint"
    REPORTLAB = "reportlab"
    CHROMIUM = "chromium"

class PageSize(Enum):
    """Standard page sizes."""
    A4 = "A4"
    LETTER = "LETTER"
    LEGAL = "LEGAL"
    A3 = "A3"
    TABLOID = "TABLOID"

class Orientation(Enum):
    """Page orientation."""
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"

@dataclass
class PDFSettings:
    """PDF generation settings."""
    page_size: PageSize = PageSize.A4
    orientation: Orientation = Orientation.PORTRAIT
    margins: Dict[str, float] = None  # top, bottom, left, right in mm
    dpi: int = 300
    compress: bool = True
    embed_fonts: bool = True
    engine: PDFEngine = PDFEngine.WEASYPRINT
    custom_css: Optional[str] = None
    watermark: Optional[str] = None
    
    def __post_init__(self):
        if self.margins is None:
            self.margins = {"top": 20, "bottom": 20, "left": 20, "right": 20}

@dataclass
class GeneratedPDF:
    """Generated PDF information."""
    pdf_id: str
    source_html: str
    pdf_path: str
    settings: PDFSettings
    file_size_bytes: int
    page_count: int
    generated_at: datetime
    checksum: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class PDFReportFormatProducerModule:
    """
    PDF Report Format Producer Module (PRFPM)
    
    Handles PDF generation from HTML:
    - Multiple PDF generation engines
    - Configurable page layouts and styling
    - PDF optimization and compression
    - Quality control and validation
    - Batch processing capabilities
    - Custom watermarking and headers/footers
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the PRFPM module."""
        self.logger = logging.getLogger(__name__)
        self.module_name = "PRFPM"
        self.is_active = False
        
        # Configuration
        self.config = config
        self.pdf_config = config.get('report_generation', {}).get('pdf_settings', {})
        
        # PDF settings
        self.output_dir = self.pdf_config.get('output_directory', 'reports/pdf')
        self.temp_dir = self.pdf_config.get('temp_directory', 'temp/pdf')
        
        # Use ReportLab as default on Windows (more reliable), WeasyPrint on other platforms
        import platform
        if platform.system() == 'Windows':
            default_engine_name = self.pdf_config.get('default_engine', 'reportlab')
        else:
            default_engine_name = self.pdf_config.get('default_engine', 'weasyprint')
            
        self.default_engine = PDFEngine(default_engine_name)
        self.quality = self.pdf_config.get('quality', 'high')
        self.max_file_size_mb = self.pdf_config.get('max_file_size_mb', 50)
        
        # Default PDF settings
        self.default_settings = PDFSettings(
            page_size=PageSize(self.pdf_config.get('page_size', 'A4')),
            orientation=Orientation(self.pdf_config.get('orientation', 'portrait')),
            margins=self.pdf_config.get('margins', {"top": 20, "bottom": 20, "left": 20, "right": 20}),
            dpi=self.pdf_config.get('dpi', 300),
            compress=self.pdf_config.get('compress', True),
            embed_fonts=self.pdf_config.get('embed_fonts', True),
            engine=self.default_engine
        )
        
        # Generated PDFs tracking
        self.generated_pdfs = {}  # pdf_id -> GeneratedPDF
        
        # Available engines
        self.available_engines = []
        self._detect_available_engines()
        
        # Statistics
        self.stats = {
            'pdfs_generated': 0,
            'conversion_errors': 0,
            'total_size_bytes': 0,
            'total_pages': 0,
            'start_time': None,
            'engine_usage': {engine.value: 0 for engine in PDFEngine}
        }
        
        # Create directories
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)
        
        self.logger.info(f"{self.module_name} initialized - available engines: {[e.value for e in self.available_engines]}")
    
    async def start(self):
        """Start the PRFPM module."""
        try:
            self.is_active = True
            self.stats['start_time'] = datetime.now().isoformat()
            
            # Validate at least one engine is available
            if not self.available_engines:
                raise RuntimeError("No PDF generation engines available")
            
            # Set default engine to first available if configured engine not available
            if self.default_engine not in self.available_engines:
                # Prefer ReportLab on Windows, then WeasyPrint, then Chromium
                preferred_order = [PDFEngine.REPORTLAB, PDFEngine.WEASYPRINT, PDFEngine.CHROMIUM]
                
                for preferred_engine in preferred_order:
                    if preferred_engine in self.available_engines:
                        self.default_engine = preferred_engine
                        break
                else:
                    # If no preferred engines available, use first available
                    if self.available_engines:
                        self.default_engine = self.available_engines[0]
                    else:
                        raise RuntimeError("No PDF generation engines available")
                        
                self.default_settings.engine = self.default_engine
                self.logger.warning(f"Default engine not available, using: {self.default_engine.value}")
            
            self.logger.info("PRFPM started successfully - PDF generation ready")
            
        except Exception as e:
            self.logger.error(f"Failed to start PRFPM: {e}")
            raise
    
    async def stop(self):
        """Stop the PRFPM module gracefully."""
        try:
            self.is_active = False
            
            # Clean up temp files
            await self._cleanup_temp_files()
            
            self.logger.info("PRFPM stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping PRFPM: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            if not self.is_active or not self.available_engines:
                return {
                    'healthy': False,
                    'is_active': self.is_active,
                    'engines_available': len(self.available_engines) if self.available_engines else 0,
                    'error': 'Module not active or no engines available',
                    'module': 'prfpm'
                }
            
            # Test PDF generation with a simple HTML
            test_html = "<html><body><h1>Test</h1></body></html>"
            test_file = os.path.join(self.temp_dir, f"health_check_{uuid.uuid4().hex}.pdf")
            
            success = await self._generate_pdf_with_engine(
                html_content=test_html,
                output_path=test_file,
                engine=self.default_engine,
                settings=self.default_settings
            )
            
            # Clean up test file
            if os.path.exists(test_file):
                os.remove(test_file)
            
            return {
                'healthy': success,
                'is_active': self.is_active,
                'engines_available': len(self.available_engines),
                'default_engine': self.default_engine.value if self.default_engine else None,
                'test_pdf_generation': success,
                'module': 'prfpm'
            }
            
        except Exception as e:
            self.logger.error(f"PRFPM health check failed: {e}")
            return {
                'healthy': False,
                'error': str(e),
                'module': 'prfpm'
            }
    
    def _detect_available_engines(self):
        """Detect which PDF generation engines are available."""
        self.available_engines = []
        
        # Check WeasyPrint (may fail on Windows due to GTK+ dependencies)
        if WEASYPRINT_AVAILABLE:
            self.available_engines.append(PDFEngine.WEASYPRINT)
            self.logger.info("WeasyPrint engine available")
        else:
            self.logger.info("WeasyPrint not available (requires GTK+ runtime on Windows). Using ReportLab instead.")
        
        # Check ReportLab (more reliable on Windows)
        if REPORTLAB_AVAILABLE:
            try:
                from reportlab.pdfgen import canvas
                # Test basic functionality
                import io
                buffer = io.BytesIO()
                c = canvas.Canvas(buffer)
                c.save()
                self.available_engines.append(PDFEngine.REPORTLAB)
                self.logger.info("ReportLab engine available")
            except Exception as e:
                self.logger.warning(f"ReportLab engine not functional: {e}")
        
        # Check Chromium (headless Chrome/Chromium)
        if self._check_chromium_available():
            self.available_engines.append(PDFEngine.CHROMIUM)
            self.logger.info("Chromium engine available")
        
        # Log available engines
        if self.available_engines:
            self.logger.info(f"Available PDF engines: {[e.value for e in self.available_engines]}")
        else:
            self.logger.error("No PDF engines available. Please install WeasyPrint, ReportLab, or Chromium.")
    
    def _check_chromium_available(self) -> bool:
        """Check if Chromium/Chrome is available for PDF generation."""
        try:
            # Common Chrome/Chromium executable names
            chrome_executables = [
                'google-chrome-stable',
                'google-chrome',
                'chromium-browser',
                'chromium',
                'chrome'
            ]
            
            # Windows-specific paths
            windows_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                r"C:\Users\{}\AppData\Local\Google\Chrome\Application\chrome.exe".format(os.getenv('USERNAME', '')),
                r"C:\Program Files\Chromium\Application\chrome.exe",
                r"C:\Program Files (x86)\Chromium\Application\chrome.exe"
            ]
            
            # Check standard executables
            for executable in chrome_executables:
                try:
                    result = subprocess.run([executable, '--version'], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        return True
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    continue
            
            # Check Windows-specific paths
            for path in windows_paths:
                if os.path.exists(path):
                    try:
                        result = subprocess.run([path, '--version'], 
                                              capture_output=True, text=True, timeout=5)
                        if result.returncode == 0:
                            return True
                    except (FileNotFoundError, subprocess.TimeoutExpired):
                        continue
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Error checking Chromium availability: {e}")
            return False
    
    async def generate_pdf_from_html(self, html_content: str, settings: PDFSettings = None, 
                                   output_filename: Optional[str] = None) -> str:
        """Generate PDF from HTML content."""
        try:
            # Use provided settings or defaults
            if settings is None:
                settings = self.default_settings
            
            # Generate unique PDF ID
            pdf_id = str(uuid.uuid4())
            
            # Generate output filename if not provided
            if output_filename is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_filename = f"report_{timestamp}_{pdf_id[:8]}.pdf"
            
            output_path = os.path.join(self.output_dir, output_filename)
            
            # Generate PDF using specified engine
            success = await self._generate_pdf_with_engine(
                html_content=html_content,
                output_path=output_path,
                engine=settings.engine,
                settings=settings
            )
            
            if not success:
                raise RuntimeError("PDF generation failed")
            
            # Get file information
            file_size = os.path.getsize(output_path)
            page_count = await self._count_pdf_pages(output_path)
            checksum = await self._calculate_file_checksum(output_path)
            
            # Create PDF record
            generated_pdf = GeneratedPDF(
                pdf_id=pdf_id,
                source_html=html_content,
                pdf_path=output_path,
                settings=settings,
                file_size_bytes=file_size,
                page_count=page_count,
                generated_at=datetime.now(),
                checksum=checksum
            )
            
            self.generated_pdfs[pdf_id] = generated_pdf
            
            # Update statistics
            self.stats['pdfs_generated'] += 1
            self.stats['total_size_bytes'] += file_size
            self.stats['total_pages'] += page_count
            self.stats['engine_usage'][settings.engine.value] += 1
            
            # Validate file size
            if file_size > self.max_file_size_mb * 1024 * 1024:
                self.logger.warning(f"Generated PDF exceeds maximum size: {file_size} bytes")
            
            self.logger.info(f"Generated PDF: {pdf_id} ({file_size} bytes, {page_count} pages)")
            
            return pdf_id
            
        except Exception as e:
            self.logger.error(f"Failed to generate PDF: {e}")
            self.stats['conversion_errors'] += 1
            raise
    
    async def _generate_pdf_with_engine(self, html_content: str, output_path: str, 
                                      engine: PDFEngine, settings: PDFSettings) -> bool:
        """Generate PDF using specified engine."""
        try:
            if engine == PDFEngine.WEASYPRINT:
                return await self._generate_with_weasyprint(html_content, output_path, settings)
            elif engine == PDFEngine.REPORTLAB:
                return await self._generate_with_reportlab(html_content, output_path, settings)
            elif engine == PDFEngine.CHROMIUM:
                return await self._generate_with_chromium(html_content, output_path, settings)
            else:
                raise ValueError(f"Unsupported PDF engine: {engine}")
                
        except Exception as e:
            self.logger.error(f"PDF generation failed with engine {engine.value}: {e}")
            return False
    
    async def _generate_with_weasyprint(self, html_content: str, output_path: str, 
                                      settings: PDFSettings) -> bool:
        """Generate PDF using WeasyPrint engine."""
        try:
            if not WEASYPRINT_AVAILABLE:
                raise RuntimeError("WeasyPrint not available")
            
            import weasyprint
            
            # Prepare CSS for page settings
            css_content = self._generate_css_for_settings(settings)
            
            # Combine HTML with CSS
            full_html = self._prepare_html_with_css(html_content, css_content)
            
            # Create WeasyPrint HTML object
            html_doc = weasyprint.HTML(string=full_html, base_url='')
            
            # Generate PDF
            html_doc.write_pdf(output_path, optimize_size=settings.compress)
            
            return True
            
        except Exception as e:
            self.logger.error(f"WeasyPrint generation failed: {e}")
            return False
    
    async def _generate_with_reportlab(self, html_content: str, output_path: str, 
                                     settings: PDFSettings) -> bool:
        """Generate PDF using ReportLab engine."""
        try:
            if not REPORTLAB_AVAILABLE:
                raise RuntimeError("ReportLab not available")
            
            from reportlab.platypus import SimpleDocTemplate
            from reportlab.lib.pagesizes import A4, letter, legal
            
            # Convert page size
            page_size = A4
            if settings.page_size == PageSize.LETTER:
                page_size = letter
            elif settings.page_size == PageSize.LEGAL:
                page_size = legal
            
            # Create document
            doc = SimpleDocTemplate(
                output_path,
                pagesize=page_size,
                topMargin=settings.margins['top'],
                bottomMargin=settings.margins['bottom'],
                leftMargin=settings.margins['left'],
                rightMargin=settings.margins['right']
            )
            
            # Convert HTML to ReportLab elements (simplified)
            elements = await self._html_to_reportlab_elements(html_content)
            
            # Build PDF
            doc.build(elements)
            
            return True
            
        except Exception as e:
            self.logger.error(f"ReportLab generation failed: {e}")
            return False
    
    async def _generate_with_chromium(self, html_content: str, output_path: str, 
                                    settings: PDFSettings) -> bool:
        """Generate PDF using Chromium headless browser."""
        try:
            # Create temporary HTML file
            temp_html = os.path.join(self.temp_dir, f"temp_{uuid.uuid4().hex}.html")
            
            # Prepare CSS for page settings
            css_content = self._generate_css_for_settings(settings)
            full_html = self._prepare_html_with_css(html_content, css_content)
            
            with open(temp_html, 'w', encoding='utf-8') as f:
                f.write(full_html)
            
            # Prepare Chrome command
            chrome_cmd = [
                'google-chrome-stable',  # Try common Chrome executable
                '--headless',
                '--disable-gpu',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                f'--print-to-pdf={output_path}',
                '--print-to-pdf-no-header',
                f'--virtual-time-budget=5000',
                temp_html
            ]
            
            # Try alternative Chrome executables if first fails
            executables = ['google-chrome-stable', 'google-chrome', 'chromium-browser', 'chromium']
            
            # Windows-specific Chrome paths
            windows_chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                r"C:\Users\{}\AppData\Local\Google\Chrome\Application\chrome.exe".format(os.getenv('USERNAME', '')),
                r"C:\Program Files\Chromium\Application\chrome.exe",
                r"C:\Program Files (x86)\Chromium\Application\chrome.exe"
            ]
            
            success = False
            
            # Try standard executables first
            for executable in executables:
                try:
                    chrome_cmd[0] = executable
                    result = subprocess.run(chrome_cmd, capture_output=True, text=True, timeout=30)
                    
                    if result.returncode == 0 and os.path.exists(output_path):
                        success = True
                        break
                        
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    continue
            
            # Try Windows-specific paths if standard executables failed
            if not success:
                for chrome_path in windows_chrome_paths:
                    if os.path.exists(chrome_path):
                        try:
                            chrome_cmd[0] = chrome_path
                            result = subprocess.run(chrome_cmd, capture_output=True, text=True, timeout=30)
                            
                            if result.returncode == 0 and os.path.exists(output_path):
                                success = True
                                break
                                
                        except (FileNotFoundError, subprocess.TimeoutExpired):
                            continue
            
            # Clean up temp file
            if os.path.exists(temp_html):
                os.remove(temp_html)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Chromium generation failed: {e}")
            return False
    
    def _generate_css_for_settings(self, settings: PDFSettings) -> str:
        """Generate CSS for PDF page settings."""
        css = f"""
        @page {{
            size: {settings.page_size.value.lower()};
            margin-top: {settings.margins['top']}mm;
            margin-bottom: {settings.margins['bottom']}mm;
            margin-left: {settings.margins['left']}mm;
            margin-right: {settings.margins['right']}mm;
        }}
        
        body {{
            font-family: 'Arial', sans-serif;
            font-size: 12pt;
            line-height: 1.4;
            color: #333;
        }}
        
        .page-break {{
            page-break-before: always;
        }}
        
        .no-break {{
            page-break-inside: avoid;
        }}
        
        h1, h2, h3, h4, h5, h6 {{
            page-break-after: avoid;
        }}
        
        table {{
            page-break-inside: avoid;
        }}
        """
        
        if settings.custom_css:
            css += "\n" + settings.custom_css
        
        return css
    
    def _prepare_html_with_css(self, html_content: str, css_content: str) -> str:
        """Combine HTML content with CSS."""
        # Simple HTML preparation - could be enhanced with proper HTML parsing
        if '<head>' in html_content.lower():
            # Insert CSS into existing head
            head_end = html_content.lower().find('</head>')
            if head_end != -1:
                return (html_content[:head_end] + 
                       f'<style>{css_content}</style>' + 
                       html_content[head_end:])
        
        # Wrap in complete HTML structure
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>{css_content}</style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
    
    async def _html_to_reportlab_elements(self, html_content: str) -> List:
        """Convert HTML to ReportLab elements (simplified conversion)."""
        from reportlab.platypus import Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        
        styles = getSampleStyleSheet()
        elements = []
        
        # Very basic HTML parsing - in production, use proper HTML parser
        import re
        
        # Remove HTML tags and extract text
        text_content = re.sub(r'<[^>]+>', '', html_content)
        
        # Split into paragraphs
        paragraphs = text_content.split('\n\n')
        
        for para_text in paragraphs:
            para_text = para_text.strip()
            if para_text:
                elements.append(Paragraph(para_text, styles['Normal']))
                elements.append(Spacer(1, 12))
        
        return elements
    
    async def _count_pdf_pages(self, pdf_path: str) -> int:
        """Count pages in PDF file."""
        try:
            # Try using PyPDF2 if available
            try:
                import PyPDF2
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    return len(pdf_reader.pages)
            except ImportError:
                pass
            
            # Fallback: estimate based on file size (very rough)
            file_size = os.path.getsize(pdf_path)
            estimated_pages = max(1, file_size // (50 * 1024))  # Assume ~50KB per page
            return estimated_pages
            
        except Exception as e:
            self.logger.error(f"Failed to count PDF pages: {e}")
            return 1
    
    async def _calculate_file_checksum(self, file_path: str) -> str:
        """Calculate file checksum."""
        try:
            import hashlib
            
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            
            return hash_md5.hexdigest()
            
        except Exception as e:
            self.logger.error(f"Failed to calculate checksum: {e}")
            return ""
    
    async def convert_html_to_pdf(self, html_file_path: str, pdf_output_path: str, 
                                settings: PDFSettings = None) -> bool:
        """Convert HTML file to PDF."""
        try:
            with open(html_file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            return await self._generate_pdf_with_engine(
                html_content=html_content,
                output_path=pdf_output_path,
                engine=settings.engine if settings else self.default_engine,
                settings=settings or self.default_settings
            )
            
        except Exception as e:
            self.logger.error(f"Failed to convert HTML file to PDF: {e}")
            return False
    
    async def generate_pdf_from_report_id(self, report_id: str, hrpm_module, 
                                        settings: PDFSettings = None) -> Optional[str]:
        """Generate PDF from HTML report ID."""
        try:
            # Get HTML content from HRPM
            html_content = await hrpm_module.get_report_content(report_id)
            if not html_content:
                raise ValueError(f"Report not found: {report_id}")
            
            # Generate PDF
            pdf_id = await self.generate_pdf_from_html(html_content, settings)
            
            # Update PDF metadata with report ID
            if pdf_id in self.generated_pdfs:
                self.generated_pdfs[pdf_id].metadata['source_report_id'] = report_id
            
            return pdf_id
            
        except Exception as e:
            self.logger.error(f"Failed to generate PDF from report {report_id}: {e}")
            return None
    
    async def get_pdf_info(self, pdf_id: str) -> Optional[Dict[str, Any]]:
        """Get PDF information by ID."""
        if pdf_id in self.generated_pdfs:
            return asdict(self.generated_pdfs[pdf_id])
        return None
    
    async def get_pdf_file_path(self, pdf_id: str) -> Optional[str]:
        """Get PDF file path by ID."""
        if pdf_id in self.generated_pdfs:
            return self.generated_pdfs[pdf_id].pdf_path
        return None
    
    def list_generated_pdfs(self, limit: int = None) -> List[Dict[str, Any]]:
        """List generated PDFs."""
        pdfs = list(self.generated_pdfs.values())
        pdfs.sort(key=lambda p: p.generated_at, reverse=True)
        
        if limit:
            pdfs = pdfs[:limit]
        
        return [asdict(pdf) for pdf in pdfs]
    
    async def _cleanup_temp_files(self):
        """Clean up temporary files."""
        try:
            if os.path.exists(self.temp_dir):
                for file in os.listdir(self.temp_dir):
                    file_path = os.path.join(self.temp_dir, file)
                    try:
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                    except Exception as e:
                        self.logger.error(f"Failed to remove temp file {file_path}: {e}")
        
        except Exception as e:
            self.logger.error(f"Error cleaning up temp files: {e}")
    
    def get_available_engines(self) -> List[str]:
        """Get list of available PDF engines."""
        return [engine.value for engine in self.available_engines]
    
    def get_status(self) -> Dict[str, Any]:
        """Get current PRFPM status."""
        return {
            'module': self.module_name,
            'active': self.is_active,
            'available_engines': self.get_available_engines(),
            'default_engine': self.default_engine.value,
            'pdfs_generated': len(self.generated_pdfs),
            'total_size_mb': round(self.stats['total_size_bytes'] / (1024 * 1024), 2),
            'stats': self.stats.copy()
        } 