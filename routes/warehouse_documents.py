# routes/warehouse_documents.py - Versión simplificada para copiar/pegar
from flask import Blueprint, request, jsonify, render_template
import os
import tempfile
import uuid
from werkzeug.utils import secure_filename
from datetime import datetime
import logging
import traceback

from utils.ocr_reader import AdvancedOCRReader
from utils.document_parser import parse_warehouse_document

logger = logging.getLogger(__name__)

warehouse_documents_bp = Blueprint('warehouse_documents', __name__, url_prefix='/api/warehouse')

# Configuración
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'tif'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@warehouse_documents_bp.route('/list')
def list_documents():
    """Página principal"""
    return render_template('documents/list.html',
                         title='Extracción de Datos de Documentos',
                         active_page='documents')

@warehouse_documents_bp.route('/upload', methods=['POST'])
def upload_documents():
    """Procesa documentos y extrae los 9 campos específicos"""
    
    if 'files' not in request.files:
        return jsonify({
            'success': False,
            'error': 'No se enviaron archivos'
        }), 400
    
    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return jsonify({
            'success': False,
            'error': 'No se seleccionaron archivos'
        }), 400
    
    temp_dir = tempfile.mkdtemp()
    resultados = []
    
    ocr_reader = AdvancedOCRReader()
    
    for file in files:
        file_result = {
            'filename': file.filename,
            'success': False,
            'error': None,
            'campos_extraidos': {},
            'campos_faltantes': [],
            'texto_copiable': ''
        }
        
        try:
            # Validaciones
            if not allowed_file(file.filename):
                file_result['error'] = f'Tipo de archivo no permitido'
                resultados.append(file_result)
                continue
            
            file.seek(0, 2)
            file_size = file.tell()
            file.seek(0)
            
            if file_size > MAX_FILE_SIZE:
                file_result['error'] = f'Archivo demasiado grande ({file_size/1024/1024:.1f}MB)'
                resultados.append(file_result)
                continue
            
            # Guardar temporalmente
            temp_filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
            temp_path = os.path.join(temp_dir, temp_filename)
            file.save(temp_path)
            
            logger.info(f"Procesando: {file.filename}")
            
            # Extraer texto con OCR
            ocr_result = ocr_reader.extract_text_from_file(temp_path)
            
            if not ocr_result['success']:
                file_result['error'] = f"Error OCR: {ocr_result.get('error')}"
                resultados.append(file_result)
                continue
            
            # Parsear documento - extraer los 9 campos
            parsed_data = parse_warehouse_document(ocr_result['text'])
            
            if parsed_data.get('parse_success'):
                file_result['success'] = True
                file_result['campos_extraidos'] = parsed_data.get('campos_extraidos', {})
                file_result['campos_faltantes'] = parsed_data.get('campos_faltantes', [])
                file_result['porcentaje_exito'] = parsed_data.get('porcentaje_exito', '0%')
                
                # Generar texto copiable para Excel
                file_result['texto_copiable'] = _generar_texto_copiable(file_result['campos_extraidos'])
                
            else:
                file_result['error'] = parsed_data.get('parse_error', 'Error desconocido al parsear')
            
            resultados.append(file_result)
            
            # Limpiar
            os.remove(temp_path)
            
        except Exception as e:
            logger.error(f"Error procesando {file.filename}: {e}\n{traceback.format_exc()}")
            file_result['error'] = str(e)
            resultados.append(file_result)
    
    # Limpiar directorio
    try:
        os.rmdir(temp_dir)
    except:
        pass
    
    # Preparar respuesta
    successful = len([r for r in resultados if r['success']])
    
    return jsonify({
        'success': successful > 0,
        'total_files': len(files),
        'successful': successful,
        'failed': len(files) - successful,
        'resultados': resultados,
        'timestamp': datetime.now().isoformat()
    })

def _generar_texto_copiable(campos: dict) -> str:
    """Genera texto formateado para copiar y pegar en Excel"""
    
    # Orden de columnas según lo solicitado
    columnas = [
        "N° de Guía",
        "Fecha",
        "CANTIDAD DE PRESENTACION", 
        "Unidad (kg)",
        "Material",
        "Número de RUC del PROVEEDOR",
        "Número de RUC del transportista",
        "Placa del vehículo",
        "Número de licencia de conducir del conductor"
    ]
    
    # Crear fila con valores o espacios vacíos
    valores = []
    for columna in columnas:
        valor = campos.get(columna, '')
        # Si es una fecha, formatear adecuadamente
        if columna == 'Fecha' and valor:
            try:
                # Intentar convertir a formato dd/mm/yyyy
                if '/' in valor:
                    partes = valor.split('/')
                    if len(partes) == 3:
                        dia, mes, anio = partes
                        if len(anio) == 2:
                            anio = '20' + anio
                        valor = f"{dia}/{mes}/{anio}"
            except:
                pass
        valores.append(str(valor))
    
    # Formato tabulado para Excel
    return '\t'.join(valores)

@warehouse_documents_bp.route('/test-parser', methods=['GET'])
def test_parser():
    """Prueba el parser con el documento de ejemplo"""
    test_text = """
    TICKET DE BASCULA
    PROCESO : 852752 NRO. PESAJE : 1677506
    FECHA IMPRESION: Jan 14 2026 5:37PM
    CONDUCTOR: MEDINA PEREZ JHON
    PROVEEDOR: EMPRESA SIDERURGICA DEL PERU S
    PLACA : CDL733
    TARA 16910 BRUTO 48590 NETO 31880
    OXIDO DE CALCIO 71.52% MIN AL 90.80%
    RUC 2040288554B
    DNI 46695131
    """
    
    resultado = parse_warehouse_document(test_text)
    
    # Generar texto copiable
    texto_copiable = _generar_texto_copiable(resultado.get('campos_extraidos', {}))
    
    return jsonify({
        'test_text': test_text,
        'parsed_result': resultado,
        'texto_copiable': texto_copiable,
        'instrucciones': 'Copia la línea de arriba y pégalo en tu Excel en la fila correspondiente'
    })

@warehouse_documents_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@warehouse_documents_bp.route('/supported-formats', methods=['GET'])
def supported_formats():
    return jsonify({
        'formats': list(ALLOWED_EXTENSIONS),
        'max_size_mb': MAX_FILE_SIZE / (1024 * 1024)
    })

@warehouse_documents_bp.route('/diagnostic', methods=['GET'])
def diagnostic():
    """Endpoint de diagnóstico completo"""
    import platform
    import sys
    import subprocess
    
    info = {
        'system': {
            'platform': platform.platform(),
            'python_version': sys.version,
            'python_executable': sys.executable
        },
        'tesseract': {
            'available': False,
            'path': None,
            'version': None,
            'error': None
        },
        'libraries': {
            'pytesseract': False,
            'pymupdf': False,
            'opencv': False,
            'pillow': False
        }
    }
    
    # Verificar librerías Python
    try:
        import pytesseract
        info['libraries']['pytesseract'] = True
    except:
        info['libraries']['pytesseract'] = False
    
    try:
        import fitz
        info['libraries']['pymupdf'] = True
    except:
        pass
    
    try:
        import cv2
        info['libraries']['opencv'] = True
    except:
        pass
    
    try:
        from PIL import Image
        info['libraries']['pillow'] = True
    except:
        pass
    
    # Buscar Tesseract
    from utils.ocr_reader import AdvancedOCRReader
    reader = AdvancedOCRReader()
    
    info['tesseract']['available'] = reader.tesseract_available
    info['tesseract']['path'] = reader.tesseract_path
    
    if reader.tesseract_available and reader.tesseract_path:
        try:
            version = subprocess.run([reader.tesseract_path, '--version'], 
                                   capture_output=True, text=True)
            info['tesseract']['version'] = version.stdout.split('\n')[0] if version.stdout else None
        except:
            info['tesseract']['error'] = "No se pudo obtener versión"
    
    # Verificar archivos del sistema
    info['system_files'] = {}
    common_files = [
        '/usr/bin/tesseract',
        '/usr/local/bin/tesseract',
        '/etc/os-release',
        '/usr/share/tesseract-ocr'
    ]
    
    for file_path in common_files:
        info['system_files'][file_path] = os.path.exists(file_path)
    
    return jsonify(info)

# routes/warehouse_documents.py
@warehouse_documents_bp.route('/test-ocr-simple', methods=['GET'])
def test_ocr_simple():
    """Prueba OCR simple sin procesamiento complejo"""
    from utils.ocr_reader import AdvancedOCRReader
    
    reader = AdvancedOCRReader()
    
    # Crear imagen de prueba en memoria
    from PIL import Image, ImageDraw
    import io
    
    img = Image.new('RGB', (400, 100), color='white')
    d = ImageDraw.Draw(img)
    d.text((10, 10), "PRUEBA OCR 12345 ABC", fill='black')
    d.text((10, 40), "TICKET DE PESAJE", fill='black')
    d.text((10, 70), "PLACA: CDL-733", fill='black')
    
    # Guardar en bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    # Guardar temporalmente
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        img.save(tmp.name)
        
        # Probar OCR
        result = reader.extract_text_from_file(tmp.name)
    
    return jsonify({
        'tesseract_available': reader.tesseract_available,
        'tesseract_path': reader.tesseract_path,
        'ocr_result': result,
        'test_image_text': ['PRUEBA OCR 12345 ABC', 'TICKET DE PESAJE', 'PLACA: CDL-733'],
        'timestamp': datetime.now().isoformat()
    })
