# utils/ocr_reader.py - VERSIÓN LIGERA PARA RAILWAY
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import fitz  # PyMuPDF
import io
import os
import subprocess
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class RailwayOCRReader:
    def __init__(self):
        """Inicializa el lector OCR optimizado para Railway"""
        self.tesseract_path = self._find_tesseract()
        self.tesseract_available = bool(self.tesseract_path)
        
        if self.tesseract_available:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_path
            logger.info(f"✅ Tesseract encontrado en Railway: {self.tesseract_path}")
        else:
            logger.error("❌ Tesseract NO disponible en Railway")
        
        # Configuración optimizada
        self.config = r'--oem 3 --psm 6 -l spa'
    
    def _find_tesseract(self) -> Optional[str]:
        """Busca Tesseract en Railway"""
        # Railway generalmente instala Tesseract en /usr/bin
        possible_paths = [
            '/usr/bin/tesseract',
            '/usr/local/bin/tesseract',
            '/bin/tesseract',
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # Si no se encuentra, intentar usar 'which'
        try:
            result = subprocess.run(['which', 'tesseract'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        
        return None
    
    def extract_text_from_file(self, file_path: str) -> Dict[str, Any]:
        """Extrae texto de archivos en Railway"""
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
                'Tesseract OCR no está instalado en Railway.\n'
                'Railway necesita instalar dependencias del sistema.\n'
                'Crea un archivo "aptfile" con:\n'
                'tesseract-ocr\ntesseract-ocr-spa\npoppler-utils'
            )
            return result
        
        try:
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == '.pdf':
                result['file_type'] = 'pdf'
                text, pages = self._process_pdf_railway(file_path)
                result['text'] = text
                result['pages'] = pages
                
            elif ext in ['.jpg', '.jpeg', '.png', '.bmp']:
                result['file_type'] = 'image'
                result['text'] = self._process_image_railway(file_path)
                result['pages'] = 1
                
            else:
                result['error'] = f"Formato no soportado: {ext}"
                return result
            
            result['success'] = bool(result['text'].strip())
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Error en Railway procesando {file_path}: {e}")
        
        return result
    
    def _process_pdf_railway(self, pdf_path: str):
        """Procesa PDFs optimizado para Railway"""
        try:
            doc = fitz.open(pdf_path)
            all_text = []
            total_pages = len(doc)
            
            # Procesar máximo 10 páginas para eficiencia
            max_pages = min(total_pages, 10)
            
            for page_num in range(max_pages):
                page = doc.load_page(page_num)
                
                # 1. Intentar texto directo
                text = page.get_text()
                if text and len(text.strip()) > 30:
                    all_text.append(text)
                    continue
                
                # 2. OCR si no hay texto
                zoom = 1.5  # Resolución moderada para Railway
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                
                img_data = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_data))
                
                # Optimizar imagen para Railway
                image = self._optimize_image_railway(image)
                
                page_text = pytesseract.image_to_string(
                    image, 
                    config=self.config,
                    lang='spa'
                )
                
                if page_text.strip():
                    all_text.append(page_text)
            
            doc.close()
            return "\n\n".join(all_text), total_pages
            
        except Exception as e:
            logger.error(f"Error procesando PDF en Railway: {e}")
            return f"Error PDF: {str(e)}", 0
    
    def _process_image_railway(self, image_path: str) -> str:
        """Procesa imágenes optimizado para Railway"""
        try:
            image = Image.open(image_path)
            
            # Optimizar para Railway
            image = self._optimize_image_railway(image)
            
            # OCR simple - un solo intento para eficiencia
            text = pytesseract.image_to_string(
                image,
                config=self.config,
                lang='spa'
            )
            
            return text.strip() if text.strip() else "No se pudo extraer texto"
                
        except Exception as e:
            logger.error(f"Error procesando imagen en Railway: {e}")
            return f"Error imagen: {str(e)}"
    
    def _optimize_image_railway(self, image: Image.Image) -> Image.Image:
        """Optimiza imagen para OCR en Railway (sin OpenCV)"""
        try:
            # Convertir a escala de grises
            if image.mode != 'L':
                image = image.convert('L')
            
            # Mejorar contraste (simple)
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)
            
            # Redimensionar si es muy grande (para eficiencia)
            max_size = 2000
            if image.width > max_size or image.height > max_size:
                ratio = max_size / max(image.width, image.height)
                new_size = (int(image.width * ratio), int(image.height * ratio))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            return image
            
        except Exception as e:
            logger.warning(f"Error optimizando imagen: {e}")
            return image
    
    def test_tesseract(self) -> Dict[str, Any]:
        """Prueba Tesseract en Railway"""
        result = {
            'available': self.tesseract_available,
            'path': self.tesseract_path,
            'version': None,
            'test_ocr': False,
            'error': None
        }
        
        if not self.tesseract_available:
            result['error'] = 'Tesseract no disponible'
            return result
        
        try:
            # Obtener versión
            version = subprocess.run([self.tesseract_path, '--version'], 
                                   capture_output=True, text=True)
            result['version'] = version.stdout.split('\n')[0] if version.stdout else None
            
            # Probar OCR simple
            img = Image.new('RGB', (200, 50), color='white')
            from PIL import ImageDraw
            d = ImageDraw.Draw(img)
            d.text((10, 10), "TEST 123", fill='black')
            
            text = pytesseract.image_to_string(img, lang='spa')
            result['test_ocr'] = '123' in text
            
            return result
            
        except Exception as e:
            result['error'] = str(e)
            return result

# Instancia global para Railway
railway_ocr_reader = RailwayOCRReader()

def extract_text_from_file(file_path: str) -> Dict[str, Any]:
    """Función principal para Railway"""
    return railway_ocr_reader.extract_text_from_file(file_path)

def get_ocr_reader() -> RailwayOCRReader:
    """Obtiene el lector OCR configurado para Railway"""
    return railway_ocr_reader

# Compatibilidad: algunas partes del código original esperan una clase
# llamada AdvancedOCRReader con una interfaz más completa. Exponemos
# esa clase aquí como un wrapper alrededor de RailwayOCRReader para
# mantener la compatibilidad y mejorar el comportamiento cuando sea
# posible.
class AdvancedOCRReader(RailwayOCRReader):
    """Wrapper backward-compatible que añade métodos esperados por el
    resto de la aplicación y mejoras menores.
    """
    def __init__(self):
        super().__init__()

    # Mantener el mismo nombre de método usado en rutas
    def extract_text_from_file(self, file_path: str):
        return super().extract_text_from_file(file_path)

    # Alias para compatibilidad con código que llama get_ocr_reader()
    @staticmethod
    def get_instance():
        return railway_ocr_reader

# También exportar el nombre AdvancedOCRReader para imports directos
AdvancedOCRReader = AdvancedOCRReader
class AdvancedOCRReader(RailwayOCRReader):
    """Clase compatibilidad retroactiva.

    Provee la misma interfaz que el proyecto original esperaba
    (método extract_text_from_file que devuelve un dict con keys
    'success','text','pages','error'). Internamente usa las
    implementaciones optimizadas para entornos sin tesseract.
    """
    def __init__(self, prefer_tesseract: bool = True):
        super().__init__()
        self.prefer_tesseract = prefer_tesseract

    def extract_text_from_file(self, file_path: str) -> Dict[str, Any]:
        # Intentar extracción con PyMuPDF (texto directo) como primera opción
        try:
            ext = os.path.splitext(file_path)[1].lower()
            if ext == '.pdf':
                try:
                    doc = fitz.open(file_path)
                    full_text = []
                    for page in doc:
                        txt = page.get_text()
                        if txt and len(txt.strip())>10:
                            full_text.append(txt)
                    doc.close()
                    text = "\n\n".join(full_text).strip()
                    if text:
                        return {'success': True, 'text': text, 'pages': len(full_text), 'error': None}
                except Exception:
                    pass

            # Fallback al comportamiento Railway (que puede usar tesseract si está disponible)
            return super().extract_text_from_file(file_path)
        except Exception as e:
            return {'success': False, 'text': '', 'pages': 0, 'error': str(e)}

# Exportar nombres compatibles
__all__ = ['railway_ocr_reader', 'extract_text_from_file', 'get_ocr_reader', 'AdvancedOCRReader']
