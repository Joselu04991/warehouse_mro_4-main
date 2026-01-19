# utils/ocr_reader.py - VERSIÓN MEJORADA PARA PDFs CON IMÁGENES
import pytesseract
from PIL import Image
import fitz  # PyMuPDF
import cv2
import numpy as np
import io
import os
import logging
from typing import Dict, Any, Optional, List
import tempfile

logger = logging.getLogger(__name__)

class AdvancedOCRReader:
    def __init__(self, tesseract_path: Optional[str] = None):
        """Inicializa el lector OCR"""
        self.tesseract_available = False
        
        try:
            if tesseract_path:
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
                self.tesseract_available = True
            else:
                # Intentar auto-detectar
                pytesseract.get_tesseract_version()
                self.tesseract_available = True
        except:
            logger.warning("Tesseract no disponible. El OCR no funcionará.")
            self.tesseract_available = False
        
        # Configuración OCR
        self.config = r'--oem 3 --psm 6 -l spa+eng'
    
    def extract_text_from_file(self, file_path: str) -> Dict[str, Any]:
        """Extrae texto de archivos (PDF o imagen)"""
        result = {
            'success': False,
            'text': '',
            'file_type': '',
            'pages': 0,
            'error': None
        }
        
        if not self.tesseract_available:
            result['error'] = 'Tesseract OCR no está instalado. Instala: apt-get install tesseract-ocr tesseract-ocr-spa'
            return result
        
        try:
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == '.pdf':
                result['file_type'] = 'pdf'
                # PDFs con imágenes necesitan procesamiento especial
                result['text'] = self._process_pdf_with_images(file_path)
                result['pages'] = self._count_pdf_pages(file_path)
                
            elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']:
                result['file_type'] = 'image'
                result['text'] = self._process_image_file(file_path)
                result['pages'] = 1
                
            else:
                result['error'] = f"Formato no soportado: {ext}"
                return result
            
            result['success'] = bool(result['text'].strip())
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Error procesando {file_path}: {e}")
        
        return result
    
    def _process_pdf_with_images(self, pdf_path: str) -> str:
        """Procesa PDFs que son imágenes (no texto seleccionable)"""
        try:
            doc = fitz.open(pdf_path)
            all_text = []
            
            logger.info(f"Procesando PDF con {len(doc)} páginas...")
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # PRIMERO: Intentar extraer texto directamente (si el PDF tiene texto)
                text = page.get_text()
                if text and len(text.strip()) > 50:  # Si hay suficiente texto
                    all_text.append(f"=== Página {page_num + 1} (Texto directo) ===\n{text}")
                    continue
                
                # SEGUNDO: Si no hay texto, convertir página a imagen y usar OCR
                # Usar alta resolución para mejor OCR
                zoom = 3.0  # 300% de zoom para mejor calidad
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                
                # Convertir a imagen PIL
                img_data = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_data))
                
                # Preprocesar imagen
                processed_image = self._preprocess_image_for_ocr(image)
                
                # Aplicar OCR
                page_text = pytesseract.image_to_string(
                    processed_image, 
                    config=self.config,
                    lang='spa'
                )
                
                if page_text.strip():
                    all_text.append(f"=== Página {page_num + 1} (OCR) ===\n{page_text}")
                else:
                    # Intentar con configuración diferente
                    page_text = pytesseract.image_to_string(
                        image,  # Imagen original
                        config=r'--oem 3 --psm 3',  # Modo automático
                        lang='spa'
                    )
                    if page_text.strip():
                        all_text.append(f"=== Página {page_num + 1} (OCR PSM 3) ===\n{page_text}")
            
            doc.close()
            return "\n\n".join(all_text) if all_text else "No se pudo extraer texto del PDF"
            
        except Exception as e:
            logger.error(f"Error procesando PDF {pdf_path}: {e}")
            return f"Error: {str(e)}"
    
    def _process_image_file(self, image_path: str) -> str:
        """Procesa archivos de imagen"""
        try:
            image = Image.open(image_path)
            
            # Probar diferentes preprocesamientos
            texts = []
            
            # 1. Imagen original
            text1 = pytesseract.image_to_string(image, config=self.config, lang='spa')
            if text1.strip():
                texts.append(text1)
            
            # 2. Imagen preprocesada
            processed = self._preprocess_image_for_ocr(image)
            text2 = pytesseract.image_to_string(processed, config=self.config, lang='spa')
            if text2.strip() and text2 != text1:
                texts.append(text2)
            
            # 3. Imagen en escala de grises
            gray = image.convert('L')
            text3 = pytesseract.image_to_string(gray, config=self.config, lang='spa')
            if text3.strip() and text3 not in [text1, text2]:
                texts.append(text3)
            
            # Combinar todos los textos únicos
            unique_texts = []
            for text in texts:
                if text.strip() and text not in unique_texts:
                    unique_texts.append(text)
            
            return "\n---\n".join(unique_texts) if unique_texts else "No se pudo extraer texto de la imagen"
            
        except Exception as e:
            logger.error(f"Error procesando imagen {image_path}: {e}")
            return f"Error: {str(e)}"
    
    def _preprocess_image_for_ocr(self, image: Image.Image) -> Image.Image:
        """Preprocesa imagen para mejorar OCR"""
        try:
            # Convertir a OpenCV
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Escala de grises
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # Reducir ruido
            denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
            
            # Umbral adaptativo para manejar diferentes iluminaciones
            thresh = cv2.adaptiveThreshold(
                denoised, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2
            )
            
            # Dilatación para conectar caracteres rotos
            kernel = np.ones((1, 1), np.uint8)
            dilated = cv2.dilate(thresh, kernel, iterations=1)
            
            # Erosión para reducir ruido
            eroded = cv2.erode(dilated, kernel, iterations=1)
            
            # Aumentar contraste
            alpha = 1.5  # Contraste
            beta = 0     # Brillo
            contrasted = cv2.convertScaleAbs(eroded, alpha=alpha, beta=beta)
            
            # Convertir de nuevo a PIL
            return Image.fromarray(contrasted)
            
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

# Función simple
def extract_text_from_file(file_path: str) -> str:
    reader = AdvancedOCRReader()
    result = reader.extract_text_from_file(file_path)
    return result['text'] if result['success'] else f"Error: {result.get('error', 'Desconocido')}"
