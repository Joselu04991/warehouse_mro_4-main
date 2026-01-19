# routes/warehouse_documents.py
from flask import Blueprint, request, jsonify, send_file, current_app
import os
import tempfile
import uuid
from werkzeug.utils import secure_filename
from datetime import datetime
import logging

from utils.ocr_reader import AdvancedOCRReader
from utils.document_parser import parse_warehouse_document, parse_multiple_documents
from utils.excel_generator import generate_warehouse_excel

warehouse_bp = Blueprint('warehouse', __name__, url_prefix='/api/warehouse')

# Configuración
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'tif'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

logger = logging.getLogger(__name__)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@warehouse_bp.route('/upload', methods=['POST'])
def upload_documents():
    """Endpoint para subir documentos (PDFs o imágenes)"""
    if 'files' not in request.files:
        return jsonify({'error': 'No se enviaron archivos'}), 400
    
    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return jsonify({'error': 'No se seleccionaron archivos'}), 400
    
    # Crear carpeta temporal para procesamiento
    temp_dir = tempfile.mkdtemp()
    results = []
    processed_files = []
    
    # Inicializar OCR reader
    ocr_reader = AdvancedOCRReader()
    
    for file in files:
        file_result = {
            'filename': file.filename,
            'success': False,
            'error': None,
            'parsed_data': None
        }
        
        try:
            # Validar archivo
            if not allowed_file(file.filename):
                file_result['error'] = f'Tipo de archivo no permitido: {file.filename}'
                results.append(file_result)
                continue
            
            # Validar tamaño
            file.seek(0, 2)  # Ir al final
            file_size = file.tell()
            file.seek(0)  # Volver al inicio
            
            if file_size > MAX_FILE_SIZE:
                file_result['error'] = f'Archivo demasiado grande: {file.filename}'
                results.append(file_result)
                continue
            
            # Guardar archivo temporalmente
            temp_filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
            temp_path = os.path.join(temp_dir, temp_filename)
            file.save(temp_path)
            
            logger.info(f"Procesando archivo: {file.filename}")
            
            # Extraer texto con OCR
            ocr_result = ocr_reader.extract_text_from_upload(temp_path)
            
            if not ocr_result['success']:
                file_result['error'] = f"Error en OCR: {ocr_result.get('error')}"
                results.append(file_result)
                continue
            
            # Parsear documento
            parsed_data = parse_warehouse_document(ocr_result['text'])
            
            # Agregar metadatos
            parsed_data['filename'] = file.filename
            parsed_data['file_type'] = ocr_result['file_type']
            parsed_data['pages'] = ocr_result['pages']
            parsed_data['ocr_success'] = ocr_result['success']
            
            file_result['success'] = True
            file_result['parsed_data'] = parsed_data
            file_result['pages'] = ocr_result['pages']
            file_result['text_length'] = ocr_result.get('text_length', 0)
            
            # Agregar a lista para Excel
            if parsed_data.get('parse_success', False):
                processed_files.append(parsed_data)
            
            results.append(file_result)
            
            # Limpiar archivo temporal
            os.remove(temp_path)
            
        except Exception as e:
            logger.error(f"Error procesando {file.filename}: {e}")
            file_result['error'] = str(e)
            results.append(file_result)
    
    # Limpiar directorio temporal
    try:
        os.rmdir(temp_dir)
    except:
        pass
    
    # Generar Excel si se solicita y hay documentos exitosos
    excel_path = None
    if request.args.get('generate_excel', 'true').lower() == 'true' and processed_files:
        try:
            excel_filename = f"documentos_almacen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            excel_path = os.path.join(tempfile.gettempdir(), excel_filename)
            
            generate_warehouse_excel(processed_files, excel_path)
            
            # Enviar Excel como respuesta
            return send_file(
                excel_path,
                as_attachment=True,
                download_name=excel_filename,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
        except Exception as e:
            logger.error(f"Error generando Excel: {e}")
    
    # Respuesta JSON
    response = {
        'total_files': len(files),
        'successful': len([r for r in results if r['success']]),
        'failed': len([r for r in results if not r['success']]),
        'results': results,
        'excel_generated': excel_path is not None
    }
    
    return jsonify(response)

@warehouse_bp.route('/test-ocr', methods=['POST'])
def test_ocr():
    """Endpoint para probar OCR sin parsing completo"""
    if 'file' not in request.files:
        return jsonify({'error': 'No se envió archivo'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No se seleccionó archivo'}), 400
    
    # Guardar temporalmente
    temp_path = os.path.join(tempfile.gettempdir(), secure_filename(file.filename))
    file.save(temp_path)
    
    # Probar OCR
    ocr_reader = AdvancedOCRReader()
    result = ocr_reader.extract_text_from_upload(temp_path)
    
    # Limpiar
    os.remove(temp_path)
    
    return jsonify(result)

@warehouse_bp.route('/supported-formats', methods=['GET'])
def supported_formats():
    """Devuelve los formatos de archivo soportados"""
    return jsonify({
        'supported_extensions': list(ALLOWED_EXTENSIONS),
        'max_file_size_mb': MAX_FILE_SIZE / (1024 * 1024),
        'document_types': [
            'ticket_pesaje',
            'guia_remision', 
            'factura',
            'recepcion'
        ]
    })
