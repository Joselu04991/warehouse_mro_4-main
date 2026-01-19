# utils/ocr_reader.py
import pytesseract
from PIL import Image
import fitz  # PyMuPDF
import cv2
import numpy as np
import io
import os
import tempfile
import logging
from typing import List, Optional, Union

logger = logging.getLogger(__name__)

class AdvancedOCRReader:
    def __init__(self, tesseract_path: Optional[str] = None):
        """
        Inicializa el lector OCR avanzado
        
        Args:
            tesseract_path: Ruta al ejecutable de Tesseract (opcional)
        """
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        else:
            # Intentar encontrar Tesseract automáticamente
            try:
                # Para Windows
                pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            except:
                pass
        
        # Configuración para documentos en español
        self.tessconfig = r'--oem 3 --psm 6 -l spa+eng'
        
    def extract_text_from_pdf_images(self, pdf_path: str) -> str:
        """
        Extrae texto de un PDF que contiene solo imágenes (cada página es una imagen)
        
        Args:
            pdf_path: Ruta al archivo PDF
            
        Returns:
            Texto de todas las páginas concatenado
        """
        all_text = []
        
        try:
            # Abrir PDF
            pdf_document = fitz.open(pdf_path)
            
            logger.info(f"Procesando PDF con {len(pdf_document)} páginas...")
            
            for page_num in range(len(pdf_document)):
                page = pdf_document.load_page(page_num)
                
                # Obtener la imagen de la página con alta resolución
                mat = fitz.Matrix(2.0, 2.0)  # Escala 2x para mejor calidad
                pix = page.get_pixmap(matrix=mat)
                
                # Convertir a bytes
                img_data = pix.tobytes("png")
                
                # Convertir a imagen PIL
                image = Image.open(io.BytesIO(img_data))
                
                # Preprocesar y hacer OCR
                page_text = self._ocr_from_image(image)
                
                if page_text.strip():
                    all_text.append(f"=== PÁGINA {page_num + 1} ===\n{page_text}")
                else:
                    logger.warning(f"Página {page_num + 1} no produjo texto")
            
            pdf_document.close()
            
        except Exception as e:
            logger.error(f"Error procesando PDF {pdf_path}: {e}")
            return f"Error: {str(e)}"
        
        return "\n\n".join(all_text)
    
    def extract_text_from_image_file(self, image_path: str) -> str:
        """
        Extrae texto de un archivo de imagen
        
        Args:
            image_path: Ruta al archivo de imagen
            
        Returns:
            Texto extraído
        """
        try:
            # Abrir imagen
            image = Image.open(image_path)
            
            # Preprocesar y hacer OCR
            text = self._ocr_from_image(image)
            
            return text
            
        except Exception as e:
            logger.error(f"Error procesando imagen {image_path}: {e}")
            return f"Error: {str(e)}"
    
    def extract_text_from_upload(self, file_path: str) -> Dict[str, Any]:
        """
        Extrae texto de cualquier archivo subido (PDF o imagen)
        
        Args:
            file_path: Ruta al archivo
            
        Returns:
            Diccionario con texto y metadatos
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
                # Verificar si el PDF tiene texto o solo imágenes
                if self._pdf_has_text(file_path):
                    # Extraer texto directo
                    result['text'] = self._extract_pdf_text(file_path)
                else:
                    # PDF con imágenes, usar OCR
                    result['text'] = self.extract_text_from_pdf_images(file_path)
                
                # Contar páginas
                pdf_doc = fitz.open(file_path)
                result['pages'] = len(pdf_doc)
                pdf_doc.close()
                
            elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp']:
                result['file_type'] = 'image'
                result['text'] = self.extract_text_from_image_file(file_path)
                result['pages'] = 1
                
            else:
                result['error'] = f"Formato no soportado: {ext}"
                return result
            
            result['success'] = True
            result['text_length'] = len(result['text'])
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Error procesando archivo {file_path}: {e}")
        
        return result
    
    def _pdf_has_text(self, pdf_path: str) -> bool:
        """Verifica si un PDF tiene texto seleccionable"""
        try:
            pdf_doc = fitz.open(pdf_path)
            has_text = False
            
            for page_num in range(min(3, len(pdf_doc))):  # Revisar primeras 3 páginas
                page = pdf_doc.load_page(page_num)
                text = page.get_text()
                if text.strip():
                    has_text = True
                    break
            
            pdf_doc.close()
            return has_text
            
        except:
            return False
    
    def _extract_pdf_text(self, pdf_path: str) -> str:
        """Extrae texto directo de PDF con texto seleccionable"""
        all_text = []
        
        try:
            pdf_doc = fitz.open(pdf_path)
            
            for page_num in range(len(pdf_doc)):
                page = pdf_doc.load_page(page_num)
                text = page.get_text()
                if text.strip():
                    all_text.append(f"=== PÁGINA {page_num + 1} ===\n{text}")
            
            pdf_doc.close()
            
        except Exception as e:
            logger.error(f"Error extrayendo texto de PDF: {e}")
            return f"Error: {str(e)}"
        
        return "\n\n".join(all_text)
    
    def _ocr_from_image(self, image: Image.Image) -> str:
        """
        Realiza OCR en una imagen PIL con preprocesamiento avanzado
        
        Args:
            image: Imagen PIL
            
        Returns:
            Texto extraído
        """
        try:
            # Convertir a OpenCV para preprocesamiento
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Preprocesamiento
            processed = self._preprocess_image(cv_image)
            
            # Convertir de nuevo a PIL
            pil_image = Image.fromarray(processed)
            
            # Configuración para documentos
            custom_config = r'--oem 3 --psm 6'
            
            # Intentar con español primero, luego inglés
            try:
                text = pytesseract.image_to_string(pil_image, config=custom_config, lang='spa')
                if len(text.strip()) < 20:  # Si no hay suficiente texto
                    text = pytesseract.image_to_string(pil_image, config=custom_config, lang='eng')
            except:
                # Fallback a solo inglés
                text = pytesseract.image_to_string(pil_image, config=custom_config, lang='eng')
            
            return text
            
        except Exception as e:
            logger.error(f"Error en OCR: {e}")
            return ""
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocesa imagen para mejorar OCR
        
        Args:
            image: Imagen OpenCV (BGR)
            
        Returns:
            Imagen preprocesada (RGB)
        """
        try:
            # Convertir a escala de grises
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Aplicar desenfoque para reducir ruido
            blurred = cv2.GaussianBlur(gray, (3, 3), 0)
            
            # Aplicar umbral adaptativo
            thresh = cv2.adaptiveThreshold(
                blurred, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2
            )
            
            # Dilatación para conectar caracteres rotos
            kernel = np.ones((1, 1), np.uint8)
            dilated = cv2.dilate(thresh, kernel, iterations=1)
            
            # Erosión para reducir ruido
            eroded = cv2.erode(dilated, kernel, iterations=1)
            
            # Aumentar contraste
            alpha = 1.5  # Factor de contraste
            beta = 0    # Brillo
            contrasted = cv2.convertScaleAbs(eroded, alpha=alpha, beta=beta)
            
            # Convertir de nuevo a RGB
            result = cv2.cvtColor(contrasted, cv2.COLOR_GRAY2RGB)
            
            return result
            
        except Exception as e:
            logger.warning(f"Error en preprocesamiento: {e}, usando imagen original")
            return image

# Función principal simplificada
def extract_text_from_file(file_path: str) -> str:
    """
    Función principal para extraer texto de archivos
    
    Args:
        file_path: Ruta al archivo
        
    Returns:
        Texto extraído
    """
    reader = AdvancedOCRReader()
    result = reader.extract_text_from_upload(file_path)
    
    if result['success']:
        return result['text']
    else:
        raise Exception(f"Error extrayendo texto: {result.get('error', 'Unknown error')}")
