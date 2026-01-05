# routes/warehouse2d_routes.py - VERSIÓN CORREGIDA

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
            ubicacion = item.get('ubicacion') or item.get('Ubicacion') or item.get('ubicación') or item.get('Ubicación') or item.get('location')
            if ubicacion:
                ubicaciones.add(str(ubicacion))
            
            # Buscar material
            material = item.get('material') or item.get('Material') or item.get('codigo_material') or item.get('Código del Material')
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

@warehouse2d_bp.route('/upload', methods=['GET'])
@login_required
def upload_view():
    """Página para subir archivo Excel"""
    return render_template('warehouse2d/upload.html')

@warehouse2d_bp.route('/upload-warehouse2d')
@login_required
def upload_warehouse2d():
    """Alias para compatibilidad"""
    return redirect(url_for('warehouse2d.upload_view'))

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@warehouse2d_bp.route('/upload', methods=['POST'])
@login_required
def upload_file():
    """Procesar archivo Excel subido"""
    if 'file' not in request.files:
        flash('No se seleccionó ningún archivo', 'error')
        return redirect(url_for('warehouse2d.upload_view'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No se seleccionó ningún archivo', 'error')
        return redirect(url_for('warehouse2d.upload_view'))
    
    if file and allowed_file(file.filename):
        try:
            # Leer el archivo
            if file.filename.endswith('.csv'):
                df = pd.read_csv(file, encoding='utf-8')
            else:
                df = pd.read_excel(file)
            
            # Verificar que tenga las columnas mínimas requeridas
            required_columns = ['Ubicación', 'Código del Material']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                flash(f'El archivo debe contener las columnas: {", ".join(missing_columns)}', 'error')
                return redirect(url_for('warehouse2d.upload_view'))
            
            # Guardar datos procesados
            session['warehouse_data'] = df.to_dict('records')
            session['file_name'] = file.filename
            session['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            flash(f'Archivo "{file.filename}" cargado exitosamente', 'success')
            return redirect(url_for('warehouse2d.index'))
            
        except Exception as e:
            flash(f'Error al procesar el archivo: {str(e)}', 'error')
            return redirect(url_for('warehouse2d.upload_view'))
    
    flash('Tipo de archivo no permitido', 'error')
    return redirect(url_for('warehouse2d.upload_view'))

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
        
        # Procesar datos para el mapa
        locations = process_for_map(data)
        
        return jsonify({
            'success': True,
            'locations': locations,
            'stats': {
                'total': len(locations),
                'max_row': max([loc['row'] for loc in locations], default=0),
                'max_col': max([loc['col'] for loc in locations], default=0),
                'zones': list(set([loc['zone'] for loc in locations]))
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

def process_for_map(data):
    """Procesar datos para el mapa"""
    locations = []
    
    for item in data:
        # Obtener ubicación con diferentes nombres posibles
        ubicacion = item.get('Ubicación') or item.get('ubicacion') or item.get('ubicación') or item.get('location')
        
        if not ubicacion:
            continue
            
        # Extraer zona, fila y columna
        zona = 'A'
        fila = 1
        columna = 1
        
        try:
            # Intentar parsear formato como A-01-01
            if '-' in str(ubicacion):
                parts = str(ubicacion).split('-')
                if len(parts) >= 1:
                    zona = parts[0]
                if len(parts) >= 2:
                    # Extraer números de la fila
                    fila_str = parts[1]
                    fila = int(''.join(filter(str.isdigit, fila_str))) if any(c.isdigit() for c in fila_str) else 1
                if len(parts) >= 3:
                    # Extraer números de la columna
                    col_str = parts[2]
                    columna = int(''.join(filter(str.isdigit, col_str))) if any(c.isdigit() for c in col_str) else 1
        except (ValueError, IndexError) as e:
            print(f"Error procesando ubicación {ubicacion}: {e}")
        
        # Obtener datos del material
        material = item.get('Código del Material') or item.get('Material') or item.get('material')
        cantidad = float(item.get('Libre utilización') or item.get('Cantidad') or item.get('cantidad') or 0)
        capacidad = float(item.get('Stock máximo') or item.get('Capacidad') or item.get('capacidad') or 100)
        
        locations.append({
            'code': str(ubicacion),
            'zone': zona,
            'row': fila,
            'col': columna,
            'material': str(material) if material else '',
            'description': item.get('Texto breve de material') or item.get('Descripción') or '',
            'quantity': cantidad,
            'capacity': capacidad,
            'unit': item.get('Unidad de medida base') or item.get('Unidad') or 'UN'
        })
    
    return locations

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
