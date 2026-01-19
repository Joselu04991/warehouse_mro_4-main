# utils/ocr_reader.py
import pytesseract
from PIL import Image
import fitz  # PyMuPDF
import cv2
import numpy as np
import io
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class AdvancedOCRReader:
    def __init__(self, tesseract_path: Optional[str] = None):
        """Inicializa el lector OCR"""
        # Configurar Tesseract si se proporciona ruta
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        
        # Configuración para español
        self.tessconfig = r'--oem 3 --psm 6 -l spa+eng'
    
    def extract_text_from_file(self, file_path: str) -> Dict[str, Any]:
        """
        Extrae texto de un archivo (PDF o imagen)
        
        Returns:
            Dict con 'success', 'text', 'file_type', 'pages', 'error'
        """
        result = {
            'success': False,
            'text': '',
            'file_type': '',
            'pages': 0,
            'error': None
        }
        
        try:
            # Determinar tipo de archivo
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == '.pdf':
                result['file_type'] = 'pdf'
                result['text'] = self._extract_from_pdf(file_path)
                result['pages'] = self._count_pdf_pages(file_path)
                
            elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']:
                result['file_type'] = 'image'
                result['text'] = self._extract_from_image(file_path)
                result['pages'] = 1
                
            else:
                result['error'] = f"Formato no soportado: {ext}"
                return result
            
            result['success'] = True
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Error procesando {file_path}: {e}")
        
        return result
    
    def _extract_from_pdf(self, pdf_path: str) -> str:
        """Extrae texto de PDF"""
        try:
            doc = fitz.open(pdf_path)
            all_text = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                # Intentar extraer texto directamente
                text = page.get_text()
                
                if text.strip():
                    all_text.append(f"=== Página {page_num + 1} ===\n{text}")
                else:
                    # Convertir a imagen y usar OCR
                    mat = fitz.Matrix(2.0, 2.0)
                    pix = page.get_pixmap(matrix=mat)
                    img_data = pix.tobytes("png")
                    image = Image.open(io.BytesIO(img_data))
                    
                    # Preprocesar imagen
                    processed = self._preprocess_image(image)
                    page_text = pytesseract.image_to_string(processed, config=self.tessconfig)
                    all_text.append(f"=== Página {page_num + 1} (OCR) ===\n{page_text}")
            
            doc.close()
            return "\n\n".join(all_text)
            
        except Exception as e:
            logger.error(f"Error extrayendo de PDF: {e}")
            return f"Error: {str(e)}"
    
    def _extract_from_image(self, image_path: str) -> str:
        """Extrae texto de imagen"""
        try:
            image = Image.open(image_path)
            processed = self._preprocess_image(image)
            text = pytesseract.image_to_string(processed, config=self.tessconfig)
            return text
        except Exception as e:
            logger.error(f"Error extrayendo de imagen: {e}")
            return f"Error: {str(e)}"
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocesa imagen para mejorar OCR"""
        try:
            # Convertir a OpenCV
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Escala de grises
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # Umbral adaptativo
            thresh = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2
            )
            
            # Convertir de nuevo a PIL
            return Image.fromarray(thresh)
            
        except Exception as e:
            logger.warning(f"Error en preprocesamiento: {e}")
            return image  # Devolver imagen original si falla
    
    def _count_pdf_pages(self, pdf_path: str) -> int:
        """Cuenta páginas de PDF"""
        try:
            doc = fitz.open(pdf_path)
            pages = len(doc)
            doc.close()
            return pages
        except:
            return 0

# Función simple para uso rápido
def extract_text_from_file(file_path: str) -> str:
    """Extrae texto de un archivo (función simplificada)"""
    reader = AdvancedOCRReader()
    result = reader.extract_text_from_file(file_path)
    
    if result['success']:
        return result['text']
    else:
        raise Exception(f"Error: {result.get('error', 'Unknown error')}")
