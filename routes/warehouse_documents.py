# routes/warehouse_documents.py
from flask import Blueprint, request, jsonify, send_file, render_template
import os
import tempfile
import uuid
from werkzeug.utils import secure_filename
from datetime import datetime
import logging
import traceback

from utils.ocr_reader import AdvancedOCRReader
from utils.document_parser import parse_warehouse_document, parse_multiple_documents
from utils.excel_generator import generate_warehouse_excel

logger = logging.getLogger(__name__)

# Crear blueprint
warehouse_documents_bp = Blueprint('warehouse_documents', __name__, url_prefix='/api/warehouse')

# Configuración
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'tif'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@warehouse_documents_bp.route('/list')
def list_documents():
    """Página para listar documentos"""
    # Por ahora, datos de ejemplo
    documents = [
        {
            'id': 1,
            'filename': 'ticket_pesaje.pdf',
            'type': 'Ticket de Pesaje',
            'status': 'Procesado',
            'date': '19/01/2024',
            'items': 3
        },
        {
            'id': 2, 
            'filename': 'guia_remision.jpg',
            'type': 'Guía de Remisión',
            'status': 'Pendiente',
            'date': '18/01/2024',
            'items': 1
        }
    ]
    
    return render_template('documents/list.html',
                         title='Documentos de Almacén',
                         documents=documents,
                         active_page='documents')

@warehouse_documents_bp.route('/upload', methods=['POST'])
def upload_documents():
    """Endpoint para subir y procesar documentos REAL"""
    
    if 'files' not in request.files:
        return jsonify({
            'success': False,
            'error': 'No se enviaron archivos',
            'timestamp': datetime.now().isoformat()
        }), 400
    
    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return jsonify({
            'success': False,
            'error': 'No se seleccionaron archivos',
            'timestamp': datetime.now().isoformat()
        }), 400
    
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
                file_result['error'] = f'Archivo demasiado grande: {file.filename} ({file_size/1024/1024:.1f}MB)'
                results.append(file_result)
                continue
            
            # Guardar archivo temporalmente
            temp_filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
            temp_path = os.path.join(temp_dir, temp_filename)
            file.save(temp_path)
            
            logger.info(f"Procesando archivo: {file.filename}")
            
            # Extraer texto con OCR
            ocr_result = ocr_reader.extract_text_from_file(temp_path)
            
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
            parsed_data['ocr_text_preview'] = ocr_result['text'][:500] + '...' if len(ocr_result['text']) > 500 else ocr_result['text']
            
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
            logger.error(f"Error procesando {file.filename}: {e}\n{traceback.format_exc()}")
            file_result['error'] = str(e)
            results.append(file_result)
    
    # Limpiar directorio temporal
    try:
        os.rmdir(temp_dir)
    except:
        pass
    
    # Generar Excel si hay documentos exitosos
    excel_path = None
    if processed_files:
        try:
            excel_filename = f"documentos_almacen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            excel_path = os.path.join(tempfile.gettempdir(), excel_filename)
            
            # Generar Excel
            generate_warehouse_excel(processed_files, excel_path)
            
            # Contar estadísticas
            successful = len([r for r in results if r['success']])
            failed = len([r for r in results if not r['success']])
            
            return jsonify({
                'success': True,
                'message': f'Procesados {successful} de {len(files)} documentos',
                'total_files': len(files),
                'successful': successful,
                'failed': failed,
                'results': results,
                'excel_generated': True,
                'excel_filename': excel_filename,
                'excel_url': f'/api/warehouse/download/{excel_filename}',
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error generando Excel: {e}\n{traceback.format_exc()}")
            return jsonify({
                'success': False,
                'error': f'Error generando Excel: {str(e)}',
                'results': results,
                'timestamp': datetime.now().isoformat()
            }), 500
    
    # Si no hay documentos procesados
    return jsonify({
        'success': False,
        'error': 'No se pudo procesar ningún documento',
        'results': results,
        'timestamp': datetime.now().isoformat()
    }), 400

@warehouse_documents_bp.route('/download/<filename>', methods=['GET'])
def download_excel(filename):
    """Descargar archivo Excel generado"""
    try:
        excel_path = os.path.join(tempfile.gettempdir(), secure_filename(filename))
        
        if not os.path.exists(excel_path):
            return jsonify({
                'success': False,
                'error': 'Archivo no encontrado'
            }), 404
        
        return send_file(
            excel_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        logger.error(f"Error descargando Excel: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@warehouse_documents_bp.route('/test', methods=['GET'])
def test_endpoint():
    """Endpoint de prueba"""
    return jsonify({
        'status': 'success',
        'message': 'API de documentos de almacén funcionando',
        'version': '1.0',
        'endpoints': {
            'GET /list': 'Listar documentos',
            'POST /upload': 'Subir y procesar documentos',
            'GET /download/<filename>': 'Descargar Excel',
            'GET /test': 'Este endpoint de prueba',
            'GET /supported-formats': 'Formatos soportados',
            'GET /health': 'Health check',
            'GET /parse-test': 'Probar parser'
        },
        'timestamp': datetime.now().isoformat()
    })

@warehouse_documents_bp.route('/parse-test', methods=['GET'])
def parse_test():
    """Prueba el parser con texto de ejemplo"""
    # Texto de ejemplo del PDF que me mostraste
    test_text = """
    TICKET DE BASCULA
    PE- ML- CHIMBOTE CHIMBOTE
    PROCESO : 852752 NRO. PESAJE : 1677506 FECHA IMPRESION: Jan 14 2026 5:37PM
    TARJETA : 210528 OPERACION: 71- DESCARGA INSUMOS PLACA : CDL733 CONDUCTOR: MEDINA PEREZ JHON PROVEEDOR: EMPRESA SIDERURGICA DEL PERU S
    FECHA TIPO PESO (KG) PESAJE TARA 16910 Jan 14 2026 5:37PM BRUTO 48590 Jan 14 2026 2:51PM NETO 31880 Jan 14 2026 5:37PM
    DATOS DEL INICIO DE TRASLADO
    FECHA DE EMISION: 13/01/2026
    DIRECCION DEL PUNTO DE PARTIDA: NRO. SN CAS. APAN ALTO REF.: (A 200M CAR. BAMBAMARCA KM 113), CAJAMARCA - HUALGAYOC - BAMBAMARCA
    MOTIVO DE TRASLADO: 1 - VENTA
    MODALIDAD DE TRANSPORTE: PRIVADO
    DIRECCION DEL PUNTO DE PARTIDA:
    NRO. SN CAS. APAN ALTO REF.: (A 200M CAR. BAMBAMARCA KM 113), CAJAMARCA - HUALGAYOC - BAMBAMARCA
    DATOS DEL TRANSPORTE
    FECHA Y HORA DEL INICIO TRASLADO: 13/01/26 06:00 PM
    MARCA PLACA TIPO Y DOCUMENTO APELLIDOS Y NOMBRES VOLVO CDL733 DNI 46695131 MEDINA PÉREZ JHON BILLY
    DATOS DEL PUNTO DESTINO
    DIRECCION DEL PUNTO DE LLEGADA:
    AV. SANTIAG ANTUNEZ DE MAYOLO NRO. S/N Z.I. ZONA INDUSTRIAL, ANCASH - SANTA - CHIMBOTE
    Ruta Fiscal: 1 - PANAMERICANA NORTE
    DATOS DEL DESTINATARIO
    APELLIDOS, NOMBRES, DENOMINACION O RAZON SOCIAL:
    TIPO Y DOCUMENTO DE IDENTIDAD:
    EMPRESA SIDERURGICA DEL PERU S.A.A.
    RUC 2040288554B
    1-102200001- 000001- OXIDO DE CALCIO- OXIDO UN1910/ 000001 DE CALCIO 71.52 % MIN AL 90.80 % 8 MAX EN KILOGRAMO 1.000000 KILOGRAMO CON PESO BRUTO DE 1.000000 Y CON PESO NETO DE 1.000000 KG KG 30000 1 30000.000000 Peso Neto de la guia 30000.000000 Peso Bruto Total de la guia 30000.000000 CODI GO DE VERIFICACION: 05141511650101550 OBSERVACIONES:CONDUCTOR: MEDINA PEREZ JHON BILLY /LIC: L46695131 |PLACA TRACTO: CDL-733 |PLACA CARRETA: TPL-973
    """
    
    result = parse_warehouse_document(test_text)
    
    return jsonify({
        'status': 'success',
        'test_text_preview': test_text[:500] + '...',
        'parsed_result': result,
        'expected_values': {
            'process_number': '852752',
            'supplier': 'EMPRESA SIDERURGICA DEL PERU S.A.A.',
            'driver': 'MEDINA PEREZ JHON BILLY',
            'license_plate': 'CDL-733',
            'weights': {'tara': 16910, 'bruto': 48590, 'neto': 31880},
            'product': 'OXIDO DE CALCIO',
            'dates': ['13/01/2026', 'Jan 14 2026']
        },
        'timestamp': datetime.now().isoformat()
    })

@warehouse_documents_bp.route('/supported-formats', methods=['GET'])
def supported_formats():
    """Devuelve los formatos de archivo soportados"""
    return jsonify({
        'supported_extensions': list(ALLOWED_EXTENSIONS),
        'max_file_size_mb': MAX_FILE_SIZE / (1024 * 1024),
        'status': 'operational',
        'timestamp': datetime.now().isoformat()
    })

@warehouse_documents_bp.route('/health', methods=['GET'])
def health_check():
    """Health check para Railway"""
    # Verificar dependencias
    deps_status = {
        'flask': True,
        'ocr': False,
        'parser': False,
        'excel': False
    }
    
    try:
        from utils.ocr_reader import AdvancedOCRReader
        deps_status['ocr'] = True
    except:
        pass
    
    try:
        from utils.document_parser import parse_warehouse_document
        deps_status['parser'] = True
    except:
        pass
    
    try:
        import pandas as pd
        deps_status['excel'] = True
    except:
        pass
    
    return jsonify({
        'status': 'healthy',
        'dependencies': deps_status,
        'timestamp': datetime.now().isoformat(),
        'service': 'warehouse-documents-api'
    })
