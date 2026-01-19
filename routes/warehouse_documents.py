# routes/warehouse_documents.py - SOLUCIÓN 1
from flask import Blueprint, request, jsonify, send_file
import os
import tempfile
import uuid
from werkzeug.utils import secure_filename
from datetime import datetime
import logging
from flask import render_template 

logger = logging.getLogger(__name__)

# Crear blueprint - CAMBIA warehouse_bp por warehouse_documents_bp
warehouse_documents_bp = Blueprint('warehouse_documents', __name__, url_prefix='/api/warehouse')

# Configuración
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'tif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# CAMBIA TODOS LOS DECORADORES @warehouse_bp.route por @warehouse_documents_bp.route
@warehouse_documents_bp.route('/upload', methods=['POST'])
def upload_documents():
    """Endpoint simplificado para probar"""
    return jsonify({
        'status': 'ok',
        'message': 'Endpoint funcionando',
        'timestamp': datetime.now().isoformat()
    })

@warehouse_documents_bp.route('/test', methods=['GET'])
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

@warehouse_documents_bp.route('/supported-formats', methods=['GET'])
def supported_formats():
    """Devuelve los formatos de archivo soportados"""
    return jsonify({
        'supported_extensions': list(ALLOWED_EXTENSIONS),
        'max_file_size_mb': 16,
        'status': 'operational'
    })

# Ruta de salud para Railway
@warehouse_documents_bp.route('/health', methods=['GET'])
def health_check():
    """Health check para Railway"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'warehouse-documents-api'
    })

@warehouse_documents_bp.route('/list')
def list_documents():
    """Página para listar documentos"""
    # Datos de ejemplo CORREGIDOS - sin 'created_at'
    documents = [
        {
            'id': 1,
            'filename': 'ticket_pesaje.pdf',
            'type': 'Ticket de Pesaje',
            'status': 'Procesado',
            'date': '19/01/2024',  # ← Formato string, no datetime
            'items': 3
        },
        {
            'id': 2, 
            'filename': 'guia_remision.jpg',
            'type': 'Guía de Remisión',
            'status': 'Pendiente',
            'date': '18/01/2024',  # ← Formato string
            'items': 1
        }
    ]
    
    return render_template('documents/list.html',
                         title='Documentos de Almacén',
                         documents=documents,
                         active_page='documents')

# También puedes agregar una ruta raíz
@warehouse_documents_bp.route('/')
def index():
    return list_documents()  # Redirige a list_documents
