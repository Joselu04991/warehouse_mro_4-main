# routes/warehouse2d_routes.py - VERSIÓN COMPLETA Y CORREGIDA

from flask import Blueprint, render_template, request, flash, redirect, url_for, session, jsonify, send_file
from flask_login import login_required
import pandas as pd
import json
from io import BytesIO
from datetime import datetime
import xlsxwriter

warehouse2d_bp = Blueprint('warehouse2d', __name__, template_folder='templates')

# ================= RUTAS PRINCIPALES =================

@warehouse2d_bp.route('/')
@warehouse2d_bp.route('/map')
@warehouse2d_bp.route('/map-view')
@login_required
def index():
    """Página principal del mapa 2D"""
    has_data = 'warehouse_data' in session
    warehouse_data = session.get('warehouse_data', [])
    
    # Calcular estadísticas básicas
    total_locations = 0
    total_materials = 0
    
    if warehouse_data:
        ubicaciones = set()
        materiales = set()
        for item in warehouse_data:
            # Buscar ubicación
            ubicacion = item.get('ubicacion') or item.get('Ubicacion') or item.get('ubicación') or item.get('location')
            if ubicacion:
                ubicaciones.add(str(ubicacion))
            
            # Buscar material
            material = item.get('material') or item.get('Material') or item.get('codigo_material')
            if material:
                materiales.add(str(material))
        
        total_locations = len(ubicaciones)
        total_materials = len(materiales)
    
    return render_template('warehouse2d/map.html',
                         has_data=has_data,
                         file_name=session.get('file_name', 'Ninguno'),
                         last_update=session.get('last_update', 'Nunca'),
                         total_locations=total_locations,
                         total_materials=total_materials)

# ================= ALIAS PARA COMPATIBILIDAD =================

@warehouse2d_bp.route('/map_view')
@login_required
def map_view():
    """Alias para compatibilidad"""
    return redirect(url_for('warehouse2d.index'))

# ================= RUTAS DE SUBIDA DE ARCHIVOS =================

@warehouse2d_bp.route('/upload')
@warehouse2d_bp.route('/upload-warehouse2d')  # DOS RUTAS PARA LA MISMA FUNCIÓN
@login_required
def upload_warehouse2d():  # NOMBRE QUE COINCIDE CON TU TEMPLATE
    """Página para subir archivo Excel - compatible con map.html"""
    return render_template('warehouse2d/upload.html')

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@warehouse2d_bp.route('/upload', methods=['POST'])
@login_required
def upload_file():
    """Procesar archivo Excel subido"""
    if 'file' not in request.files:
        flash('No se seleccionó ningún archivo', 'error')
        return redirect(url_for('warehouse2d.upload_warehouse2d'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No se seleccionó ningún archivo', 'error')
        return redirect(url_for('warehouse2d.upload_warehouse2d'))
    
    if file and allowed_file(file.filename):
        try:
            # Leer el archivo
            if file.filename.endswith('.csv'):
                df = pd.read_csv(file, encoding='utf-8')
            else:
                df = pd.read_excel(file)
            
            # Verificar que tenga las columnas correctas
            if 'Ubicación' not in df.columns or 'Código del Material' not in df.columns:
                flash('El archivo debe contener las columnas "Ubicación" y "Código del Material"', 'error')
                return redirect(url_for('warehouse2d.upload_warehouse2d'))
            
            # Guardar datos procesados
            session['warehouse_data'] = df.to_dict('records')
            session['file_name'] = file.filename
            session['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            flash(f'Archivo "{file.filename}" cargado exitosamente', 'success')
            return redirect(url_for('warehouse2d.index'))
            
        except Exception as e:
            flash(f'Error al procesar el archivo: {str(e)}', 'error')
            return redirect(url_for('warehouse2d.upload_warehouse2d'))
    
    flash('Tipo de archivo no permitido', 'error')
    return redirect(url_for('warehouse2d.upload_warehouse2d'))

# ================= RUTAS DE API Y DATOS =================

@warehouse2d_bp.route('/get-data')
@login_required
def get_warehouse_data():
    """Obtener datos del almacén"""
    try:
        data = session.get('warehouse_data', [])
        return jsonify({
            'success': True,
            'data': data,
            'file_name': session.get('file_name', ''),
            'last_update': session.get('last_update', ''),
            'message': 'Datos cargados correctamente'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@warehouse2d_bp.route('/map-data')
@login_required
def map_data():
    """Datos para el mapa"""
    try:
        data = session.get('warehouse_data', [])
        if not data:
            return jsonify({'success': True, 'locations': [], 'stats': {}})
        
        # Procesar datos para el mapa (simplificado)
        locations = []
        for item in data:
            ubicacion = item.get('Ubicación', '')
            if ubicacion:
                locations.append({
                    'code': ubicacion,
                    'material': item.get('Código del Material', ''),
                    'description': item.get('Texto breve de material', ''),
                    'quantity': item.get('Libre utilización', 0),
                    'capacity': item.get('Stock máximo', 1000)
                })
        
        return jsonify({
            'success': True,
            'locations': locations,
            'stats': {'total': len(locations)}
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@warehouse2d_bp.route('/download-template')
@login_required
def download_template():
    """Descargar plantilla"""
    try:
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Plantilla')
        
        # Escribir encabezados
        headers = [
            'Ubicación', 
            'Código del Material', 
            'Texto breve de material', 
            'Unidad de medida base', 
            'Stock de seguridad', 
            'Stock máximo', 
            'Libre utilización'
        ]
        
        for i, header in enumerate(headers):
            worksheet.write(0, i, header)
        
        # Ejemplos
        examples = [
            ['A-01-01', 'MAT-001', 'Tornillo M8', 'UN', 10, 1000, 100],
            ['A-01-02', 'MAT-002', 'Tuerca M8', 'UN', 5, 1000, 150]
        ]
        
        for row_num, row_data in enumerate(examples, start=1):
            for col_num, cell_data in enumerate(row_data):
                worksheet.write(row_num, col_num, cell_data)
        
        workbook.close()
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='plantilla_almacen2d.xlsx'
        )
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('warehouse2d.index'))

@warehouse2d_bp.route('/export-excel')
@login_required
def export_excel():
    """Exportar datos"""
    try:
        data = session.get('warehouse_data', [])
        if not data:
            flash('No hay datos para exportar', 'warning')
            return redirect(url_for('warehouse2d.index'))
        
        output = BytesIO()
        df = pd.DataFrame(data)
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'export_{datetime.now().strftime("%Y%m%d")}.xlsx'
        )
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('warehouse2d.index'))

@warehouse2d_bp.route('/clear-data', methods=['POST'])
@login_required
def clear_data():
    """Limpiar datos"""
    try:
        session.pop('warehouse_data', None)
        session.pop('file_name', None)
        session.pop('last_update', None)
        return jsonify({'success': True, 'message': 'Datos eliminados'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ================= FUNCIONES SIMPLIFICADAS =================

def process_for_map(data):
    """Procesar datos para el mapa (versión simplificada)"""
    locations = []
    for item in data:
        ubicacion = item.get('Ubicación', '')
        if ubicacion:
            # Intentar extraer coordenadas
            fila = 1
            columna = 1
            zona = 'A'
            
            try:
                if '-' in ubicacion:
                    parts = ubicacion.split('-')
                    if len(parts) > 0:
                        zona = parts[0]
                    if len(parts) > 1:
                        fila = int(parts[1])
                    if len(parts) > 2:
                        columna = int(parts[2])
            except:
                pass
            
            locations.append({
                'code': ubicacion,
                'zone': zona,
                'row': fila,
                'col': columna,
                'material': item.get('Código del Material', ''),
                'quantity': float(item.get('Libre utilización', 0)),
                'capacity': float(item.get('Stock máximo', 1000))
            })
    
    return locations
