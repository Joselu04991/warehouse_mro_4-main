# routes/warehouse_documents.py - VERSIÓN SIMPLIFICADA
from flask import Blueprint, request, jsonify, send_file
import os
import tempfile
import uuid
from werkzeug.utils import secure_filename
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Crear blueprint
warehouse_bp = Blueprint('warehouse', __name__, url_prefix='/api/warehouse')

# Configuración
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'tif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@warehouse_bp.route('/upload', methods=['POST'])
def upload_documents():
    """Endpoint simplificado para probar"""
    return jsonify({
        'status': 'ok',
        'message': 'Endpoint funcionando',
        'timestamp': datetime.now().isoformat()
    })

@warehouse_bp.route('/test', methods=['GET'])
def test_endpoint():
    """Endpoint de prueba"""
    return jsonify({
        'status': 'success',
        'message': 'API de documentos de almacén funcionando',
        'version': '1.0',
        'endpoints': {
            'POST /upload': 'Subir documentos PDF/imágenes',
            'GET /test': 'Este endpoint de prueba',
            'GET /supported-formats': 'Formatos soportados'
        }
    })

@warehouse_bp.route('/supported-formats', methods=['GET'])
def supported_formats():
    """Devuelve los formatos de archivo soportados"""
    return jsonify({
        'supported_extensions': list(ALLOWED_EXTENSIONS),
        'max_file_size_mb': 16,
        'status': 'operational'
    })

# Ruta de salud para Railway
@warehouse_bp.route('/health', methods=['GET'])
def health_check():
    """Health check para Railway"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'warehouse-documents-api'
    })
