import logging
from typing import Optional, Union
import tempfile
import os

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_text(path: str, lang: str = "spa", dpi: int = 300, 
                 use_temp_dir: bool = True) -> Optional[str]:
    """
    Extrae texto de archivos PDF o imágenes usando OCR.
    
    Args:
        path: Ruta del archivo (PDF o imagen)
        lang: Idioma para OCR (por defecto español)
        dpi: Resolución para conversión de PDF (por defecto 300)
        use_temp_dir: Usar directorio temporal para archivos intermedios
        
    Returns:
        Texto extraído o None si hay error
    """
    try:
        # Importaciones dentro del try para mejor manejo de dependencias
        import pytesseract
        from PIL import Image
        import pdf2image
    except ImportError as e:
        logger.error(f"Dependencias faltantes: {e}")
        raise RuntimeError(
            "OCR no disponible. Instala las dependencias necesarias:\n"
            "pip install pytesseract pillow pdf2image"
        ) from e
    
    # Verificar que el archivo existe
    if not os.path.exists(path):
        logger.error(f"Archivo no encontrado: {path}")
        raise FileNotFoundError(f"Archivo no encontrado: {path}")
    
    text_parts = []
    temp_dir = None
    
    try:
        path_lower = path.lower()
        
        if path_lower.endswith(".pdf"):
            # Configurar parámetros de conversión PDF
            convert_params = {
                'dpi': dpi,
                'fmt': 'jpeg',  # Formato más eficiente en memoria
                'thread_count': 2,  # Paralelismo controlado
                'size': (1654, None)  # Ancho fijo para consistencia
            }
            
            if use_temp_dir:
                temp_dir = tempfile.mkdtemp(prefix="pdf2image_")
                convert_params['output_folder'] = temp_dir
                convert_params['paths_only'] = True
            
            logger.info(f"Convirtiendo PDF: {path} (DPI: {dpi})")
            images = pdf2image.convert_from_path(path, **convert_params)
            
            # Procesar cada página con manejo de progreso
            total_pages = len(images)
            for i, img in enumerate(images, 1):
                try:
                    page_text = pytesseract.image_to_string(
                        img, 
                        lang=lang,
                        config='--oem 3 --psm 6'  # Configuración optimizada
                    )
                    text_parts.append(page_text)
                    
                    # Log de progreso cada 10 páginas o al final
                    if i % 10 == 0 or i == total_pages:
                        logger.info(f"Procesada página {i}/{total_pages}")
                        
                except Exception as page_error:
                    logger.warning(f"Error en página {i}: {page_error}")
                    text_parts.append(f"\n[ERROR EN PÁGINA {i}]\n")
                
                # Liberar memoria de la imagen procesada
                if hasattr(img, 'close'):
                    img.close()
        
        else:
            # Procesar archivo de imagen
            logger.info(f"Procesando imagen: {path}")
            try:
                with Image.open(path) as img:
                    # Convertir a RGB si es necesario (para imágenes RGBA, L, etc.)
                    if img.mode not in ('RGB', 'L'):
                        img = img.convert('RGB')
                    
                    # Mejorar contraste para mejor OCR
                    from PIL import ImageEnhance
                    enhancer = ImageEnhance.Contrast(img)
                    img = enhancer.enhance(1.5)  # Aumentar contraste 50%
                    
                    text = pytesseract.image_to_string(
                        img, 
                        lang=lang,
                        config='--oem 3 --psm 3'
                    )
                    text_parts.append(text)
                    
            except Exception as img_error:
                logger.error(f"Error procesando imagen {path}: {img_error}")
                raise
    
    except pdf2image.exceptions.PDFPageCountError as e:
        logger.error(f"Error en PDF (posiblemente corrupto): {e}")
        raise RuntimeError(f"Error al procesar PDF: {e}") from e
    
    except pytesseract.TesseractNotFoundError:
        logger.error("Tesseract no está instalado en el sistema")
        raise RuntimeError(
            "Tesseract OCR no está instalado. "
            "Instálalo desde: https://github.com/tesseract-ocr/tesseract"
        )
    
    except Exception as e:
        logger.error(f"Error inesperado procesando {path}: {e}")
        raise
    
    finally:
        # Limpiar directorio temporal si se creó
        if temp_dir and os.path.exists(temp_dir):
            try:
                import shutil
                shutil.rmtree(temp_dir)
                logger.debug(f"Directorio temporal eliminado: {temp_dir}")
            except Exception as e:
                logger.warning(f"No se pudo eliminar directorio temporal: {e}")
    
    # Unir y limpiar texto
    if text_parts:
        full_text = "\n".join(text_parts)
        
        # Limpiar texto: eliminar líneas vacías múltiples
        import re
        full_text = re.sub(r'\n\s*\n+', '\n\n', full_text)
        
        logger.info(f"Texto extraído: {len(full_text)} caracteres")
        return full_text.strip()
    
    return None


# Versión simplificada para compatibilidad
def extract_text_simple(path: str) -> str:
    """Versión simple compatible con el código original"""
    result = extract_text(path)
    return result if result is not None else ""


# Ejemplo de uso y prueba
if __name__ == "__main__":
    # Uso básico
    text = extract_text("documento.pdf")
    if text:
        print(f"Primeros 500 caracteres:\n{text[:500]}...")
    
    # Con configuración personalizada
    text = extract_text("imagen.png", lang="spa+eng", dpi=400)
