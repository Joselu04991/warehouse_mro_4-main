# routes/warehouse2d_routes.py

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
            # Buscar ubicación en diferentes formatos
            ubicacion = None
            for key in ['ubicacion', 'Ubicacion', 'ubicación', 'Ubicación', 'UBICACION']:
                if key in item and item[key]:
                    ubicacion = str(item[key])
                    break
            
            # Buscar material en diferentes formatos
            material = None
            for key in ['material', 'Material', 'MATERIAL']:
                if key in item and item[key]:
                    material = str(item[key])
                    break
            
            if ubicacion:
                ubicaciones.add(ubicacion)
            if material:
                materiales.add(material)
        
        total_locations = len(ubicaciones)
        total_materials = len(materiales)
    
    return render_template('warehouse2d/map.html',
                         has_data=has_data,
                         file_name=session.get('file_name', 'Ninguno'),
                         last_update=session.get('last_update', 'Nunca'),
                         total_locations=total_locations,
                         total_materials=total_materials)

# ================= RUTAS DE SUBIDA DE ARCHIVOS =================

@warehouse2d_bp.route('/upload')
@warehouse2d_bp.route('/upload-warehouse2d')  # Ruta alternativa para compatibilidad
@login_required
def upload_view():
    """Página para subir archivo Excel"""
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
        return redirect(request.url)
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No se seleccionó ningún archivo', 'error')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        try:
            # Leer el archivo
            if file.filename.endswith('.csv'):
                df = pd.read_csv(file, encoding='utf-8')
            else:
                df = pd.read_excel(file)
            
            # Guardar columnas originales
            original_columns = list(df.columns)
            
            # Convertir a lista de diccionarios
            data = df.where(pd.notnull(df), None).to_dict('records')
            
            # Normalizar nombres de columnas
            normalized_data = []
            for row in data:
                normalized_row = {}
                for key, value in row.items():
                    if pd.isna(value):
                        value = None
                    
                    # Normalizar nombre de columna
                    norm_key = str(key).strip().lower()
                    # Reemplazar caracteres especiales
                    norm_key = norm_key.replace(' ', '_').replace('á', 'a').replace('é', 'e')\
                                      .replace('í', 'i').replace('ó', 'o').replace('ú', 'u')\
                                      .replace('ñ', 'n').replace('Á', 'a').replace('É', 'e')\
                                      .replace('Í', 'i').replace('Ó', 'o').replace('Ú', 'u')\
                                      .replace('Ñ', 'n')
                    
                    normalized_row[norm_key] = value
                normalized_data.append(normalized_row)
            
            # Guardar en sesión
            session['warehouse_data'] = normalized_data
            session['file_name'] = file.filename
            session['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            session['raw_columns'] = original_columns
            
            flash(f'✓ Archivo "{file.filename}" cargado exitosamente', 'success')
            flash(f'✓ {len(data)} registros procesados', 'success')
            flash(f'✓ {len(set(str(row.get("ubicacion", "")) for row in normalized_data if row.get("ubicacion")))} ubicaciones identificadas', 'info')
            
            return redirect(url_for('warehouse2d.index'))
            
        except UnicodeDecodeError:
            # Intentar con diferentes encodings para CSV
            try:
                file.stream.seek(0)  # Resetear stream
                df = pd.read_csv(file, encoding='latin-1')
                
                # Guardar columnas originales
                original_columns = list(df.columns)
                
                # Convertir a lista de diccionarios
                data = df.where(pd.notnull(df), None).to_dict('records')
                
                # Normalizar nombres de columnas
                normalized_data = []
                for row in data:
                    normalized_row = {}
                    for key, value in row.items():
                        if pd.isna(value):
                            value = None
                        
                        norm_key = str(key).strip().lower()
                        norm_key = norm_key.replace(' ', '_').replace('á', 'a').replace('é', 'e')\
                                          .replace('í', 'i').replace('ó', 'o').replace('ú', 'u')\
                                          .replace('ñ', 'n')
                        
                        normalized_row[norm_key] = value
                    normalized_data.append(normalized_row)
                
                # Guardar en sesión
                session['warehouse_data'] = normalized_data
                session['file_name'] = file.filename
                session['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                session['raw_columns'] = original_columns
                
                flash(f'✓ Archivo "{file.filename}" cargado exitosamente (encoding: latin-1)', 'success')
                return redirect(url_for('warehouse2d.index'))
                
            except Exception as e2:
                flash(f'Error al procesar el archivo: {str(e2)}', 'error')
                return redirect(url_for('warehouse2d.upload_view'))
                
        except Exception as e:
            flash(f'Error al procesar el archivo: {str(e)}', 'error')
            return redirect(url_for('warehouse2d.upload_view'))
    
    flash('Tipo de archivo no permitido. Use .xlsx, .xls o .csv', 'error')
    return redirect(url_for('warehouse2d.upload_view'))

# ================= RUTAS DE API =================

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

# ================= RUTAS DE GESTIÓN =================

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
        
        # Hoja de instrucciones
        worksheet = workbook.add_worksheet('Instrucciones')
        
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
        
        # Encabezados de la tabla
        headers = [
            ['COLUMNA', 'DESCRIPCIÓN', 'EJEMPLO', 'TIPO', 'REQUERIDO'],
            ['ubicacion', 'Código único de ubicación', 'A-01-01, B-02-03', 'Texto', 'Sí'],
            ['zona', 'Zona del almacén', 'A, B, C, PASILLO', 'Texto', 'No'],
            ['fila', 'Número de fila', '1, 2, 3, 10', 'Número', 'Sí'],
            ['columna', 'Número de columna', '1, 2, 3, 20', 'Número', 'Sí'],
            ['material', 'Código del material', 'MAT-001, TORN-005', 'Texto', 'Sí'],
            ['descripcion', 'Descripción del material', 'Tornillo M8, Tuerca', 'Texto', 'No'],
            ['cantidad', 'Cantidad en stock', '100, 250, 500.5', 'Número', 'Sí'],
            ['unidad', 'Unidad de medida', 'UN, KG, M, L', 'Texto', 'No'],
            ['capacidad', 'Capacidad máxima', '1000, 2000, 5000', 'Número', 'No'],
            ['valor_unitario', 'Valor por unidad', '0.50, 1.25, 10.99', 'Número', 'No']
        ]
        
        # Escribir encabezados
        for row_num, row_data in enumerate(headers):
            for col_num, cell_data in enumerate(row_data):
                if row_num == 0:
                    worksheet.write(row_num + 4, col_num, cell_data, header_format)
                else:
                    worksheet.write(row_num + 4, col_num, cell_data, example_format)
        
        # Hoja para datos
        worksheet2 = workbook.add_worksheet('Datos')
        
        # Escribir encabezados en hoja de datos
        data_headers = ['ubicacion', 'zona', 'fila', 'columna', 'material', 'descripcion', 'cantidad', 'unidad', 'capacidad', 'valor_unitario']
        for col_num, header in enumerate(data_headers):
            worksheet2.write(0, col_num, header, header_format)
        
        # Ejemplos de datos
        examples = [
            ['A-01-01', 'A', 1, 1, 'MAT-001', 'Tornillo M8', 100, 'UN', 1000, 0.50],
            ['A-01-02', 'A', 1, 2, 'MAT-002', 'Tuerca M8', 150, 'UN', 1000, 0.25],
            ['B-01-01', 'B', 1, 1, 'MAT-003', 'Arandela plana', 500, 'UN', 2000, 0.10],
            ['C-02-03', 'C', 2, 3, 'PROD-100', 'Producto X', 50, 'PZA', 100, 25.99]
        ]
        
        for row_num, row_data in enumerate(examples, start=1):
            for col_num, cell_data in enumerate(row_data):
                worksheet2.write(row_num, col_num, cell_data)
        
        # Ajustar ancho de columnas
        worksheet.set_column('A:A', 15)
        worksheet.set_column('B:B', 25)
        worksheet.set_column('C:C', 20)
        worksheet.set_column('D:D', 10)
        worksheet.set_column('E:E', 15)
        
        worksheet2.set_column('A:J', 15)
        
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

# ================= FUNCIONES AUXILIARES =================

def process_for_map(data):
    """Procesar datos crudos para el mapa"""
    location_map = {}
    
    for row in data:
        # Buscar ubicación en diferentes formatos
        ubicacion = None
        for key in ['ubicacion', 'ubicación']:
            if key in row and row[key]:
                ubicacion = str(row[key])
                break
        
        if not ubicacion:
            continue
        
        # Buscar otros campos
        zona = row.get('zona', '')
        if not zona:
            # Intentar extraer zona del código de ubicación
            if '-' in ubicacion:
                zona = ubicacion.split('-')[0]
        
        # Obtener fila y columna
        fila = row.get('fila', 1)
        columna = row.get('columna', 1)
        
        # Convertir a enteros
        try:
            fila = int(float(fila)) if fila else 1
        except:
            fila = 1
        
        try:
            columna = int(float(columna)) if columna else 1
        except:
            columna = 1
        
        # Buscar material
        material = None
        for key in ['material', 'codigo_material', 'codigo']:
            if key in row and row[key]:
                material = str(row[key])
                break
        
        if not material:
            continue
        
        # Obtener cantidad
        cantidad = 0
        for key in ['cantidad', 'stock', 'existencia']:
            if key in row and row[key]:
                try:
                    cantidad = float(row[key])
                    break
                except:
                    cantidad = 0
        
        # Obtener capacidad
        capacidad = 1000  # Valor por defecto
        for key in ['capacidad', 'capacidad_max', 'max_capacidad']:
            if key in row and row[key]:
                try:
                    capacidad = float(row[key])
                    break
                except:
                    capacidad = 1000
        
        # Obtener descripción
        descripcion = row.get('descripcion', row.get('descripción', material))
        
        if ubicacion not in location_map:
            location_map[ubicacion] = {
                'code': ubicacion,
                'zone': zona,
                'row': fila,
                'col': columna,
                'capacity': capacidad,
                'used_capacity': 0,
                'materials': []
            }
        
        location = location_map[ubicacion]
        
        # Agregar material
        location['materials'].append({
            'code': material,
            'description': descripcion,
            'quantity': cantidad,
            'unit': row.get('unidad', 'UN'),
            'unit_value': float(row.get('valor_unitario', 0) or 0)
        })
        
        location['used_capacity'] += cantidad
    
    # Convertir a lista y calcular ocupación
    locations_list = []
    for loc in location_map.values():
        ocupation_percent = 0
        if loc['capacity'] > 0:
            ocupation_percent = (loc['used_capacity'] / loc['capacity']) * 100
        
        # Determinar estado
        status = 'vacio'
        if loc['used_capacity'] > 0:
            if ocupation_percent < 20:
                status = 'critico'
            elif ocupation_percent < 50:
                status = 'bajo'
            else:
                status = 'normal'
        
        # Calcular valor total
        total_value = sum(mat['quantity'] * mat['unit_value'] for mat in loc['materials'])
        
        locations_list.append({
            'code': loc['code'],
            'zone': loc['zone'],
            'row': loc['row'],
            'col': loc['col'],
            'capacity': loc['capacity'],
            'used_capacity': loc['used_capacity'],
            'free_capacity': loc['capacity'] - loc['used_capacity'],
            'ocupation_percent': round(ocupation_percent, 1),
            'status': status,
            'materials': loc['materials'],
            'materials_count': len(loc['materials']),
            'total_value': round(total_value, 2)
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
        'total_value': 0,
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
        stats['total_value'] += loc.get('total_value', 0)
        
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
    
    max_row = max((loc['row'] for loc in locations), default=1)
    max_col = max((loc['col'] for loc in locations), default=1)
    zones = list(set(loc['zone'] for loc in locations if loc['zone']))
    
    return {
        'max_row': max_row,
        'max_col': max_col,
        'zones': zones
    }
