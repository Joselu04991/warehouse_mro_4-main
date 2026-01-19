# utils/ocr_reader.py - VERSIÓN CON BÚSQUEDA AVANZADA
import pytesseract
from PIL import Image
import fitz
import cv2
import numpy as np
import io
import os
import subprocess
import logging
from typing import Dict, Any, Optional
import tempfile

logger = logging.getLogger(__name__)

class AdvancedOCRReader:
    def __init__(self, tesseract_path: Optional[str] = None):
        """Inicializa el lector OCR con búsqueda automática"""
        self.tesseract_path = self._find_tesseract(tesseract_path)
        self.tesseract_available = bool(self.tesseract_path)
        
        if self.tesseract_available:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_path
            logger.info(f"Tesseract encontrado en: {self.tesseract_path}")
        else:
            logger.error("Tesseract NO disponible. El OCR no funcionará.")
        
        # Configuración OCR
        self.config = r'--oem 3 --psm 6 -l spa+eng'
    
    def _find_tesseract(self, custom_path: Optional[str] = None) -> Optional[str]:
        """Busca Tesseract en múltiples ubicaciones"""
        # 1. Usar ruta personalizada si se proporciona
        if custom_path and os.path.exists(custom_path):
            return custom_path
        
        # 2. Buscar en PATH
        try:
            result = subprocess.run(['which', 'tesseract'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        
        # 3. Buscar en ubicaciones comunes de Railway/Ubuntu
        common_paths = [
            '/usr/bin/tesseract',
            '/usr/local/bin/tesseract',
            '/bin/tesseract',
            '/app/.apt/usr/bin/tesseract',
            '/opt/homebrew/bin/tesseract',  # macOS
            '/usr/local/Cellar/tesseract/*/bin/tesseract',  # Homebrew
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        # 4. Expandir glob patterns
        import glob
        glob_paths = [
            '/usr/local/Cellar/tesseract/*/bin/tesseract',
            '/opt/homebrew/Cellar/tesseract/*/bin/tesseract',
        ]
        
        for pattern in glob_paths:
            matches = glob.glob(pattern)
            if matches:
                return matches[0]
        
        return None
    
    def extract_text_from_file(self, file_path: str) -> Dict[str, Any]:
        """Extrae texto de archivos"""
        result = {
            'success': False,
            'text': '',
            'file_type': '',
            'pages': 0,
            'error': None,
            'tesseract_available': self.tesseract_available,
            'tesseract_path': self.tesseract_path
        }
        
        if not self.tesseract_available:
            result['error'] = (
                'Tesseract OCR no está instalado.\n'
                'En Railway, agrega esto a nixpacks.toml:\n'
                'apt-get install -y tesseract-ocr tesseract-ocr-spa'
            )
            return result
        
        try:
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == '.pdf':
                result['file_type'] = 'pdf'
                result['text'] = self._process_pdf(file_path)
                result['pages'] = self._count_pdf_pages(file_path)
                
            elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']:
                result['file_type'] = 'image'
                result['text'] = self._process_image(file_path)
                result['pages'] = 1
                
            else:
                result['error'] = f"Formato no soportado: {ext}"
                return result
            
            result['success'] = bool(result['text'].strip())
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Error procesando {file_path}: {e}")
        
        return result
    
    def _process_pdf(self, pdf_path: str) -> str:
        """Procesa PDFs"""
        try:
            doc = fitz.open(pdf_path)
            all_text = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Intentar texto directo primero
                text = page.get_text()
                if text and len(text.strip()) > 20:
                    all_text.append(f"=== Página {page_num + 1} ===\n{text}")
                    continue
                
                # Convertir a imagen para OCR
                zoom = 2.0
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                
                img_data = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_data))
                
                # OCR
                page_text = pytesseract.image_to_string(image, config=self.config, lang='spa')
                if page_text.strip():
                    all_text.append(f"=== Página {page_num + 1} (OCR) ===\n{page_text}")
            
            doc.close()
            return "\n\n".join(all_text) if all_text else ""
            
        except Exception as e:
            logger.error(f"Error procesando PDF: {e}")
            return f"Error: {str(e)}"
    
    def _process_image(self, image_path: str) -> str:
        """Procesa imágenes"""
        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image, config=self.config, lang='spa')
            return text.strip()
        except Exception as e:
            logger.error(f"Error procesando imagen: {e}")
            return f"Error: {str(e)}"
    
    def _count_pdf_pages(self, pdf_path: str) -> int:
        try:
            doc = fitz.open(pdf_path)
            pages = len(doc)
            doc.close()
            return pages
        except:
            return 0

def extract_text_from_file(file_path: str) -> str:
    reader = AdvancedOCRReader()
    result = reader.extract_text_from_file(file_path)
    
    if result['success']:
        return result['text']
    else:
        error_msg = result.get('error', 'Error desconocido')
        tesseract_info = f"\nTesseract disponible: {result.get('tesseract_available')}"
        tesseract_path = f"\nTesseract path: {result.get('tesseract_path')}"
        return f"Error: {error_msg}{tesseract_info}{tesseract_path}"
