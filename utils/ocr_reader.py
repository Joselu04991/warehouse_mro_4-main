# utils/ocr_reader.py - VERSIÓN SIN OPENCV
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import fitz  # PyMuPDF
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
            logger.info(f"✅ Tesseract encontrado en: {self.tesseract_path}")
            
            # Probar Tesseract
            try:
                version = subprocess.run([self.tesseract_path, '--version'], 
                                       capture_output=True, text=True)
                logger.info(f"Tesseract versión: {version.stdout.split()[1] if version.stdout else 'Desconocida'}")
            except:
                logger.warning("No se pudo obtener versión de Tesseract")
        else:
            logger.error("❌ Tesseract NO disponible. El OCR no funcionará.")
        
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
        
        # 3. Buscar en ubicaciones comunes
        common_paths = [
            '/usr/bin/tesseract',
            '/usr/local/bin/tesseract',
            '/bin/tesseract',
            '/app/.apt/usr/bin/tesseract',
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
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
                result['text'] = self._process_pdf_simple(file_path)
                result['pages'] = self._count_pdf_pages(file_path)
                
            elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']:
                result['file_type'] = 'image'
                result['text'] = self._process_image_simple(file_path)
                result['pages'] = 1
                
            else:
                result['error'] = f"Formato no soportado: {ext}"
                return result
            
            result['success'] = bool(result['text'].strip())
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Error procesando {file_path}: {e}")
        
        return result
    
    def _process_pdf_simple(self, pdf_path: str) -> str:
        """Procesa PDFs de forma simple"""
        try:
            doc = fitz.open(pdf_path)
            all_text = []
            
            logger.info(f"Procesando PDF con {len(doc)} páginas")
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # 1. Intentar extraer texto directo (si el PDF tiene texto)
                text = page.get_text()
                if text and len(text.strip()) > 50:
                    all_text.append(text)
                    continue
                
                # 2. Si no hay texto, convertir a imagen y usar OCR
                # Usar resolución moderada para mejor velocidad/calidad
                zoom = 2.0
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                
                # Convertir a imagen PIL
                img_data = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_data))
                
                # Mejorar imagen para OCR (sin OpenCV)
                enhanced = self._enhance_image_pil(image)
                
                # Aplicar OCR
                page_text = pytesseract.image_to_string(
                    enhanced, 
                    config=self.config,
                    lang='spa'
                )
                
                if page_text.strip():
                    all_text.append(page_text)
                else:
                    # Intentar con la imagen original
                    page_text = pytesseract.image_to_string(
                        image,
                        config=self.config,
                        lang='spa'
                    )
                    if page_text.strip():
                        all_text.append(page_text)
            
            doc.close()
            return "\n\n".join(all_text) if all_text else "No se pudo extraer texto"
            
        except Exception as e:
            logger.error(f"Error procesando PDF {pdf_path}: {e}")
            return f"Error: {str(e)}"
    
    def _process_image_simple(self, image_path: str) -> str:
        """Procesa imágenes de forma simple"""
        try:
            image = Image.open(image_path)
            
            # Probar diferentes procesamientos
            texts = []
            
            # 1. Imagen original
            text_original = pytesseract.image_to_string(
                image, 
                config=self.config,
                lang='spa'
            )
            if text_original.strip():
                texts.append(text_original)
            
            # 2. Imagen mejorada
            enhanced = self._enhance_image_pil(image)
            text_enhanced = pytesseract.image_to_string(
                enhanced,
                config=self.config,
                lang='spa'
            )
            if text_enhanced.strip() and text_enhanced != text_original:
                texts.append(text_enhanced)
            
            # 3. Imagen en escala de grises
            gray = image.convert('L')
            text_gray = pytesseract.image_to_string(
                gray,
                config=self.config,
                lang='spa'
            )
            if text_gray.strip() and text_gray not in texts:
                texts.append(text_gray)
            
            # Usar el texto más largo encontrado
            if texts:
                return max(texts, key=len)
            else:
                return "No se pudo extraer texto"
                
        except Exception as e:
            logger.error(f"Error procesando imagen {image_path}: {e}")
            return f"Error: {str(e)}"
    
    def _enhance_image_pil(self, image: Image.Image) -> Image.Image:
        """Mejora imagen usando solo PIL (sin OpenCV)"""
        try:
            # Convertir a escala de grises si es color
            if image.mode != 'L':
                image = image.convert('L')
            
            # Aumentar contraste
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.0)
            
            # Aumentar nitidez
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(2.0)
            
            # Aumentar brillo si está muy oscuro
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(1.2)
            
            # Aplicar filtro para reducir ruido
            image = image.filter(ImageFilter.MedianFilter(size=3))
            
            return image
            
        except Exception as e:
            logger.warning(f"Error mejorando imagen con PIL: {e}")
            return image
    
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
        return f"Error: {error_msg}\nTesseract disponible: {result.get('tesseract_available')}"
