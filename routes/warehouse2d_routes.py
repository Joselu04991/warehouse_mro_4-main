# routes/warehouse2d_routes.py

from flask import Blueprint, render_template, request, flash, redirect, url_for, session, jsonify, send_file
from flask_login import login_required
import pandas as pd
import json
from io import BytesIO
from datetime import datetime
import xlsxwriter

warehouse2d_bp = Blueprint('warehouse2d', __name__, template_folder='templates')

# Rutas principales
@warehouse2d_bp.route('/')
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
            ubicacion = item.get('Ubicación') or item.get('ubicacion') or item.get('UBICACION')
            material = item.get('Material') or item.get('material') or item.get('MATERIAL')
            
            if ubicacion:
                ubicaciones.add(str(ubicacion))
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

@warehouse2d_bp.route('/map')
@login_required
def map_view():
    """Vista del mapa (alias de index)"""
    return redirect(url_for('warehouse2d.index'))

@warehouse2d_bp.route('/upload')
@login_required
def upload_view():
    """Página para subir archivo Excel"""
    return render_template('warehouse2d/upload.html')

# Función para verificar extensiones de archivo
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@warehouse2d_bp.route('/upload', methods=['POST'])
@login_required
def upload_file():
    """Procesar archivo Excel subido"""
    if 'file' not in request.files:
        flash('No se seleccionó ningún archivo', 'error')
        return redirect(request.url)
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No se seleccionó ningún archivo', 'error')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        try:
            # Leer el archivo Excel
            if file.filename.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
            
            # Convertir a lista de diccionarios
            data = df.where(pd.notnull(df), None).to_dict('records')
            
            # Normalizar nombres de columnas (minúsculas, sin espacios)
            normalized_data = []
            for row in data:
                normalized_row = {}
                for key, value in row.items():
                    # Normalizar key
                    norm_key = str(key).strip().lower().replace(' ', '_').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
                    normalized_row[norm_key] = value
                normalized_data.append(normalized_row)
            
            # Guardar en sesión
            session['warehouse_data'] = normalized_data
            session['file_name'] = file.filename
            session['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            session['raw_columns'] = list(df.columns)  # Guardar columnas originales
            
            flash(f'Archivo "{file.filename}" cargado exitosamente. {len(data)} registros procesados.', 'success')
            return redirect(url_for('warehouse2d.index'))
            
        except Exception as e:
            flash(f'Error al procesar el archivo: {str(e)}', 'error')
            return redirect(url_for('warehouse2d.upload_view'))
    
    flash('Tipo de archivo no permitido. Use .xlsx, .xls o .csv', 'error')
    return redirect(url_for('warehouse2d.upload_view'))

@warehouse2d_bp.route('/get-data')
@login_required
def get_warehouse_data():
    """Obtener datos del almacén en formato JSON"""
    try:
        data = session.get('warehouse_data', [])
        
        return jsonify({
            'success': True,
            'data': data,
            'total': len(data),
            'columns': session.get('raw_columns', []),
            'file_name': session.get('file_name', ''),
            'last_update': session.get('last_update', ''),
            'message': 'Datos cargados correctamente'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@warehouse2d_bp.route('/clear-data', methods=['POST'])
@login_required
def clear_data():
    """Eliminar todos los datos del almacén"""
    try:
        # Limpiar datos de la sesión
        session.pop('warehouse_data', None)
        session.pop('file_name', None)
        session.pop('last_update', None)
        session.pop('raw_columns', None)
        
        return jsonify({
            'success': True,
            'message': 'Datos eliminados correctamente'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@warehouse2d_bp.route('/export-excel')
@login_required
def export_excel():
    """Exportar datos a Excel"""
    try:
        data = session.get('warehouse_data', [])
        
        if not data:
            flash('No hay datos para exportar', 'warning')
            return redirect(url_for('warehouse2d.index'))
        
        # Crear un nuevo libro de Excel
        output = BytesIO()
        
        # Convertir datos normalizados de vuelta a formato original si es necesario
        export_data = []
        for row in data:
            export_row = {}
            for key, value in row.items():
                # Revertir normalización para nombres de columnas más legibles
                pretty_key = key.replace('_', ' ').title()
                export_row[pretty_key] = value
            export_data.append(export_row)
        
        # Crear DataFrame
        df = pd.DataFrame(export_data)
        
        # Escribir a Excel
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Almacen2D', index=False)
            
            # Ajustar ancho de columnas
            worksheet = writer.sheets['Almacen2D']
            for i, col in enumerate(df.columns):
                column_width = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, min(column_width, 50))
        
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'almacen2d_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
        
    except Exception as e:
        flash(f'Error al exportar: {str(e)}', 'error')
        return redirect(url_for('warehouse2d.index'))

@warehouse2d_bp.route('/download-template')
@login_required
def download_template():
    """Descargar plantilla de Excel para carga de datos"""
    try:
        # Crear plantilla
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Plantilla')
        
        # Formato para encabezados
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#366092',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        # Formato para ejemplos
        example_format = workbook.add_format({
            'text_wrap': True,
            'border': 1,
            'align': 'left',
            'valign': 'top'
        })
        
        # Instrucciones
        worksheet.merge_range('A1:E1', 'PLANTILLA PARA CARGA DE DATOS DE ALMACÉN 2D', header_format)
        worksheet.merge_range('A2:E2', 'Complete los datos según su estructura de almacén', example_format)
        worksheet.write('A3', 'NOTA: Las columnas marcadas con * son requeridas', example_format)
        worksheet.write('A4', 'Las demás columnas son opcionales pero recomendadas', example_format)
        
        # Encabezados principales
        headers = [
            ['COLUMNA', 'DESCRIPCIÓN', 'EJEMPLO', 'TIPO', 'REQUERIDO'],
            ['ubicacion', 'Código único de ubicación', 'A-01-01, B-02-03, C-01-05', 'Texto', '*'],
            ['zona', 'Zona del almacén', 'A, B, C, PASILLO, RECEPCION', 'Texto', ''],
            ['fila', 'Número de fila', '1, 2, 3, 10, 15', 'Número', '*'],
            ['columna', 'Número de columna', '1, 2, 3, 10, 20', 'Número', '*'],
            ['material', 'Código del material', 'MAT-001, TORN-005, PROD-100', 'Texto', '*'],
            ['descripcion', 'Descripción del material', 'Tornillo M8, Tuerca, Arandela', 'Texto', ''],
            ['cantidad', 'Cantidad en stock', '100, 250, 500.5, 1000', 'Número', '*'],
            ['unidad', 'Unidad de medida', 'UN, KG, M, L, PZA', 'Texto', ''],
            ['capacidad', 'Capacidad máxima', '1000, 2000, 5000', 'Número', ''],
            ['valor_unitario', 'Valor por unidad', '0.50, 1.25, 10.99', 'Número', ''],
            ['estado', 'Estado del material', 'ACTIVO, INACTIVO, RESERVADO', 'Texto', ''],
            ['categoria', 'Categoría del material', 'HERRAMIENTA, MATERIA_PRIMA, PRODUCTO_TERMINADO', 'Texto', '']
        ]
        
        # Escribir encabezados y ejemplos
        for row_num, row_data in enumerate(headers):
            for col_num, cell_data in enumerate(row_data):
                if row_num == 0:
                    worksheet.write(row_num + 5, col_num, cell_data, header_format)
                else:
                    worksheet.write(row_num + 5, col_num, cell_data, example_format)
        
        # Ejemplos de datos reales
        worksheet.merge_range('A20:E20', 'EJEMPLOS DE DATOS COMPLETOS', header_format)
        
        examples = [
            ['ubicacion', 'zona', 'fila', 'columna', 'material', 'descripcion', 'cantidad', 'unidad', 'capacidad', 'valor_unitario', 'estado', 'categoria'],
            ['A-01-01', 'A', 1, 1, 'MAT-001', 'Tornillo M8', 100, 'UN', 1000, 0.50, 'ACTIVO', 'MATERIA_PRIMA'],
            ['A-01-02', 'A', 1, 2, 'MAT-002', 'Tuerca M8', 150, 'UN', 1000, 0.25, 'ACTIVO', 'MATERIA_PRIMA'],
            ['B-01-01', 'B', 1, 1, 'MAT-003', 'Arandela plana', 500, 'UN', 2000, 0.10, 'ACTIVO', 'MATERIA_PRIMA'],
            ['C-02-03', 'C', 2, 3, 'PROD-100', 'Producto terminado X', 50, 'PZA', 100, 25.99, 'ACTIVO', 'PRODUCTO_TERMINADO']
        ]
        
        for row_num, row_data in enumerate(examples):
            for col_num, cell_data in enumerate(row_data):
                if row_num == 0:
                    worksheet.write(row_num + 21, col_num, cell_data, header_format)
                else:
                    worksheet.write(row_num + 21, col_num, cell_data, example_format)
        
        # Ajustar ancho de columnas
        worksheet.set_column('A:A', 15)
        worksheet.set_column('B:B', 25)
        worksheet.set_column('C:C', 20)
        worksheet.set_column('D:D', 10)
        worksheet.set_column('E:E', 15)
        
        # Hoja para datos
        worksheet2 = workbook.add_worksheet('Datos')
        
        # Escribir encabezados en hoja de datos
        data_headers = ['ubicacion', 'zona', 'fila', 'columna', 'material', 'descripcion', 'cantidad', 'unidad', 'capacidad', 'valor_unitario']
        for col_num, header in enumerate(data_headers):
            worksheet2.write(0, col_num, header, header_format)
        
        workbook.close()
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='plantilla_almacen2d.xlsx'
        )
        
    except Exception as e:
        flash(f'Error al generar plantilla: {str(e)}', 'error')
        return redirect(url_for('warehouse2d.index'))

@warehouse2d_bp.route('/map-data')
@login_required
def map_data():
    """Obtener datos procesados para el mapa"""
    try:
        data = session.get('warehouse_data', [])
        
        if not data:
            return jsonify({
                'success': True,
                'locations': [],
                'stats': {
                    'total_locations': 0,
                    'total_materials': 0,
                    'occupied_locations': 0,
                    'empty_locations': 0,
                    'total_capacity': 0,
                    'used_capacity': 0
                }
            })
        
        # Procesar datos para el mapa
        locations = process_for_map(data)
        
        # Calcular estadísticas
        stats = calculate_map_statistics(locations)
        
        return jsonify({
            'success': True,
            'locations': locations,
            'stats': stats,
            'dimensions': get_warehouse_dimensions(locations)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

def process_for_map(data):
    """Procesar datos crudos para el mapa"""
    location_map = {}
    
    for row in data:
        ubicacion = row.get('ubicacion') or row.get('Ubicacion') or row.get('ubicación')
        zona = row.get('zona') or row.get('Zona') or ''
        fila = row.get('fila') or row.get('Fila') or 1
        columna = row.get('columna') or row.get('Columna') or 1
        material = row.get('material') or row.get('Material') or ''
        descripcion = row.get('descripcion') or row.get('descripción') or row.get('Descripcion') or material
        cantidad = float(row.get('cantidad') or row.get('Cantidad') or 0)
        capacidad = float(row.get('capacidad') or row.get('Capacidad') or 1000)
        unidad = row.get('unidad') or row.get('Unidad') or 'UN'
        valor_unitario = float(row.get('valor_unitario') or row.get('valor unitario') or row.get('valor') or 0)
        
        if not ubicacion:
            continue
        
        # Convertir fila y columna a enteros
        try:
            fila = int(float(fila))
            columna = int(float(columna))
        except:
            fila = 1
            columna = 1
        
        if ubicacion not in location_map:
            location_map[ubicacion] = {
                'code': ubicacion,
                'zone': zona,
                'row': fila,
                'col': columna,
                'capacity': capacidad,
                'used_capacity': 0,
                'materials': [],
                'materials_map': set()  # Para evitar duplicados
            }
        
        location = location_map[ubicacion]
        
        # Agregar material si no está duplicado
        if material and material not in location['materials_map']:
            location['materials'].append({
                'code': material,
                'description': descripcion,
                'quantity': cantidad,
                'unit': unidad,
                'unit_value': valor_unitario,
                'total_value': cantidad * valor_unitario
            })
            location['materials_map'].add(material)
            location['used_capacity'] += cantidad
    
    # Convertir a lista y calcular ocupación
    locations_list = []
    for loc in location_map.values():
        ocupation_percent = (loc['used_capacity'] / loc['capacity'] * 100) if loc['capacity'] > 0 else 0
        
        # Determinar estado basado en ocupación
        status = 'vacio'
        if loc['used_capacity'] > 0:
            if ocupation_percent < 20:
                status = 'critico'
            elif ocupation_percent < 50:
                status = 'bajo'
            else:
                status = 'normal'
        
        locations_list.append({
            **loc,
            'ocupation_percent': round(ocupation_percent, 1),
            'status': status,
            'free_capacity': loc['capacity'] - loc['used_capacity']
        })
    
    return locations_list

def calculate_map_statistics(locations):
    """Calcular estadísticas del mapa"""
    stats = {
        'total_locations': len(locations),
        'total_materials': 0,
        'occupied_locations': 0,
        'empty_locations': 0,
        'total_capacity': 0,
        'used_capacity': 0,
        'by_status': {
            'normal': 0,
            'bajo': 0,
            'critico': 0,
            'vacio': 0
        }
    }
    
    material_set = set()
    
    for loc in locations:
        stats['total_capacity'] += loc['capacity']
        stats['used_capacity'] += loc['used_capacity']
        
        if loc['used_capacity'] > 0:
            stats['occupied_locations'] += 1
        else:
            stats['empty_locations'] += 1
        
        stats['by_status'][loc['status']] += 1
        
        # Contar materiales únicos
        for mat in loc['materials']:
            material_set.add(mat['code'])
    
    stats['total_materials'] = len(material_set)
    
    return stats

def get_warehouse_dimensions(locations):
    """Obtener dimensiones del almacén"""
    if not locations:
        return {'max_row': 0, 'max_col': 0, 'zones': []}
    
    max_row = max(loc['row'] for loc in locations)
    max_col = max(loc['col'] for loc in locations)
    zones = list(set(loc['zone'] for loc in locations if loc['zone']))
    
    return {
        'max_row': max_row,
        'max_col': max_col,
        'zones': zones
    }

@warehouse2d_bp.route('/api/location/<location_code>')
@login_required
def get_location_details(location_code):
    """Obtener detalles específicos de una ubicación"""
    try:
        data = session.get('warehouse_data', [])
        locations = process_for_map(data)
        
        location = next((loc for loc in locations if loc['code'] == location_code), None)
        
        if not location:
            return jsonify({
                'success': False,
                'message': 'Ubicación no encontrada'
            }), 404
        
        return jsonify({
            'success': True,
            'location': location
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500
