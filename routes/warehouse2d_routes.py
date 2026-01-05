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
def map_view_alias():
    """Alias para compatibilidad"""
    return redirect(url_for('warehouse2d.index'))

# ================= RUTAS DE SUBIDA DE ARCHIVOS =================

@warehouse2d_bp.route('/upload')
@warehouse2d_bp.route('/upload-warehouse2d')
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
    """Procesar archivo Excel subido con las columnas específicas"""
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
            
            # Guardar columnas originales para referencia
            original_columns = list(df.columns)
            session['raw_columns'] = original_columns
            
            # Verificar columnas requeridas
            required_columns = ['Ubicación', 'Código del Material']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                flash(f'Faltan columnas requeridas: {", ".join(missing_columns)}', 'error')
                return redirect(url_for('warehouse2d.upload_view'))
            
            # Mapear columnas a nombres normalizados
            column_mapping = {
                'Código del Material': 'material',
                'Texto breve de material': 'descripcion',
                'Unidad de medida base': 'unidad',
                'Stock de seguridad': 'stock_minimo',
                'Stock máximo': 'stock_maximo',
                'Ubicación': 'ubicacion',
                'Libre utilización': 'stock_actual'
            }
            
            # Renombrar columnas
            df_renamed = df.rename(columns=column_mapping)
            
            # Filtrar solo las columnas que necesitamos
            available_columns = [col for col in column_mapping.values() if col in df_renamed.columns]
            df_filtered = df_renamed[available_columns]
            
            # Convertir a lista de diccionarios y manejar valores nulos
            data = []
            for _, row in df_filtered.iterrows():
                item = {}
                for col in available_columns:
                    value = row[col]
                    # Convertir NaN a None
                    if pd.isna(value):
                        value = None
                    # Convertir tipos numéricos
                    elif col in ['stock_minimo', 'stock_maximo', 'stock_actual']:
                        try:
                            value = float(value) if value is not None else 0
                        except:
                            value = 0
                    item[col] = value
                
                # Asegurar que tenemos ubicación y material
                if item.get('ubicacion') and item.get('material'):
                    data.append(item)
            
            # Procesar ubicaciones para extraer fila y columna
            processed_data = []
            for item in data:
                ubicacion = str(item['ubicacion']).strip()
                
                # Extraer fila y columna del código de ubicación
                # Asumimos formato como: A-01-01, B-02-03, etc.
                fila = 1
                columna = 1
                zona = 'A'
                
                try:
                    # Intentar parsear formato A-01-01
                    if '-' in ubicacion:
                        parts = ubicacion.split('-')
                        if len(parts) >= 1:
                            zona = parts[0]
                        if len(parts) >= 2:
                            fila = int(parts[1])
                        if len(parts) >= 3:
                            columna = int(parts[2])
                    # Intentar parsear formato A0101
                    elif len(ubicacion) >= 4:
                        zona = ubicacion[0]
                        try:
                            fila = int(ubicacion[1:3])
                            columna = int(ubicacion[3:5])
                        except:
                            pass
                except:
                    pass
                
                # Agregar campos calculados
                item['fila'] = fila
                item['columna'] = columna
                item['zona'] = zona
                
                # Calcular capacidad y ocupación
                capacidad = item.get('stock_maximo', 1000)
                stock_actual = item.get('stock_actual', 0)
                
                item['capacidad'] = capacidad
                item['cantidad'] = stock_actual
                
                processed_data.append(item)
            
            # Guardar en sesión
            session['warehouse_data'] = processed_data
            session['file_name'] = file.filename
            session['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Estadísticas
            total_registros = len(processed_data)
            ubicaciones_unicas = len(set(item['ubicacion'] for item in processed_data))
            materiales_unicos = len(set(item['material'] for item in processed_data))
            
            flash(f'✓ Archivo "{file.filename}" cargado exitosamente', 'success')
            flash(f'✓ {total_registros} registros procesados', 'success')
            flash(f'✓ {ubicaciones_unicas} ubicaciones únicas identificadas', 'info')
            flash(f'✓ {materiales_unicos} materiales únicos cargados', 'info')
            
            return redirect(url_for('warehouse2d.index'))
            
        except UnicodeDecodeError:
            # Intentar con encoding latin-1
            try:
                file.stream.seek(0)
                df = pd.read_csv(file, encoding='latin-1')
                
                # Repetir el procesamiento...
                original_columns = list(df.columns)
                session['raw_columns'] = original_columns
                
                # Verificar columnas requeridas
                required_columns = ['Ubicación', 'Código del Material']
                missing_columns = [col for col in required_columns if col not in df.columns]
                
                if missing_columns:
                    flash(f'Faltan columnas requeridas: {", ".join(missing_columns)}', 'error')
                    return redirect(url_for('warehouse2d.upload_view'))
                
                # Mapear columnas
                column_mapping = {
                    'Código del Material': 'material',
                    'Texto breve de material': 'descripcion',
                    'Unidad de medida base': 'unidad',
                    'Stock de seguridad': 'stock_minimo',
                    'Stock máximo': 'stock_maximo',
                    'Ubicación': 'ubicacion',
                    'Libre utilización': 'stock_actual'
                }
                
                df_renamed = df.rename(columns=column_mapping)
                available_columns = [col for col in column_mapping.values() if col in df_renamed.columns]
                df_filtered = df_renamed[available_columns]
                
                data = []
                for _, row in df_filtered.iterrows():
                    item = {}
                    for col in available_columns:
                        value = row[col]
                        if pd.isna(value):
                            value = None
                        elif col in ['stock_minimo', 'stock_maximo', 'stock_actual']:
                            try:
                                value = float(value) if value is not None else 0
                            except:
                                value = 0
                        item[col] = value
                    
                    if item.get('ubicacion') and item.get('material'):
                        data.append(item)
                
                # Procesar ubicaciones
                processed_data = []
                for item in data:
                    ubicacion = str(item['ubicacion']).strip()
                    
                    fila = 1
                    columna = 1
                    zona = 'A'
                    
                    try:
                        if '-' in ubicacion:
                            parts = ubicacion.split('-')
                            if len(parts) >= 1:
                                zona = parts[0]
                            if len(parts) >= 2:
                                fila = int(parts[1])
                            if len(parts) >= 3:
                                columna = int(parts[2])
                        elif len(ubicacion) >= 4:
                            zona = ubicacion[0]
                            try:
                                fila = int(ubicacion[1:3])
                                columna = int(ubicacion[3:5])
                            except:
                                pass
                    except:
                        pass
                    
                    item['fila'] = fila
                    item['columna'] = columna
                    item['zona'] = zona
                    
                    capacidad = item.get('stock_maximo', 1000)
                    stock_actual = item.get('stock_actual', 0)
                    
                    item['capacidad'] = capacidad
                    item['cantidad'] = stock_actual
                    
                    processed_data.append(item)
                
                session['warehouse_data'] = processed_data
                session['file_name'] = file.filename
                session['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                flash(f'✓ Archivo "{file.filename}" cargado (encoding: latin-1)', 'success')
                return redirect(url_for('warehouse2d.index'))
                
            except Exception as e2:
                flash(f'Error al procesar el archivo: {str(e2)}', 'error')
                return redirect(url_for('warehouse2d.upload_view'))
                
        except Exception as e:
            flash(f'Error al procesar el archivo: {str(e)}', 'error')
            # Mostrar primeras filas para debugging
            if 'df' in locals():
                flash(f'Columnas encontradas: {", ".join(df.columns)}', 'info')
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
        
        # Convertir de vuelta al formato original
        export_data = []
        for item in data:
            export_item = {
                'Ubicación': item.get('ubicacion', ''),
                'Código del Material': item.get('material', ''),
                'Texto breve de material': item.get('descripcion', ''),
                'Unidad de medida base': item.get('unidad', 'UN'),
                'Stock de seguridad': item.get('stock_minimo', 0),
                'Stock máximo': item.get('stock_maximo', 1000),
                'Libre utilización': item.get('stock_actual', item.get('cantidad', 0)),
                'Fila': item.get('fila', 1),
                'Columna': item.get('columna', 1),
                'Zona': item.get('zona', 'A')
            }
            export_data.append(export_item)
        
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
    """Descargar plantilla de Excel con las columnas específicas"""
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
        worksheet.merge_range('A1:G1', 'PLANTILLA PARA CARGA DE DATOS DE ALMACÉN 2D', header_format)
        worksheet.merge_range('A2:G2', 'Complete los datos según su estructura de almacén', example_format)
        
        # Encabezados de la tabla
        headers = [
            ['COLUMNA', 'DESCRIPCIÓN', 'EJEMPLO', 'TIPO', 'REQUERIDO', 'NOTAS'],
            ['Ubicación', 'Código de ubicación en almacén', 'A-01-01, B-02-03, C-01-05', 'Texto', 'Sí', 'Formato: Zona-Fila-Columna'],
            ['Código del Material', 'Código único del material', 'MAT-001, PROD-100, TOOL-005', 'Texto', 'Sí', ''],
            ['Texto breve de material', 'Descripción del material', 'Tornillo M8, Producto X, Herramienta Y', 'Texto', 'No', ''],
            ['Unidad de medida base', 'Unidad de medición', 'UN, KG, M, L, PZA', 'Texto', 'No', ''],
            ['Stock de seguridad', 'Stock mínimo permitido', '10, 50, 100', 'Número', 'No', ''],
            ['Stock máximo', 'Capacidad máxima de almacenamiento', '1000, 2000, 5000', 'Número', 'No', ''],
            ['Libre utilización', 'Stock actual disponible', '100, 250, 500.5', 'Número', 'No', 'Stock actual en la ubicación']
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
        
        # Escribir encabezados en hoja de datos (columnas exactas de tu Excel)
        data_headers = [
            'Ubicación', 
            'Código del Material', 
            'Texto breve de material', 
            'Unidad de medida base', 
            'Stock de seguridad', 
            'Stock máximo', 
            'Libre utilización'
        ]
        
        for col_num, header in enumerate(data_headers):
            worksheet2.write(0, col_num, header, header_format)
        
        # Ejemplos de datos
        examples = [
            ['A-01-01', 'MAT-001', 'Tornillo M8', 'UN', 10, 1000, 100],
            ['A-01-02', 'MAT-002', 'Tuerca M8', 'UN', 5, 1000, 150],
            ['B-01-01', 'MAT-003', 'Arandela plana', 'UN', 20, 2000, 500],
            ['C-02-03', 'PROD-100', 'Producto terminado X', 'PZA', 5, 100, 50]
        ]
        
        for row_num, row_data in enumerate(examples, start=1):
            for col_num, cell_data in enumerate(row_data):
                worksheet2.write(row_num, col_num, cell_data)
        
        # Ajustar ancho de columnas
        worksheet.set_column('A:A', 15)
        worksheet.set_column('B:B', 20)
        worksheet.set_column('C:C', 25)
        worksheet.set_column('D:D', 15)
        worksheet.set_column('E:E', 10)
        worksheet.set_column('F:F', 10)
        
        worksheet2.set_column('A:G', 15)
        
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
    
    for item in data:
        ubicacion = item.get('ubicacion')
        if not ubicacion:
            continue
        
        ubicacion = str(ubicacion).strip()
        zona = item.get('zona', 'A')
        fila = item.get('fila', 1)
        columna = item.get('columna', 1)
        
        # Asegurar que fila y columna sean enteros
        try:
            fila = int(fila)
            columna = int(columna)
        except:
            fila = 1
            columna = 1
        
        material = item.get('material')
        if not material:
            continue
        
        capacidad = item.get('capacidad', item.get('stock_maximo', 1000))
        stock_actual = item.get('cantidad', item.get('stock_actual', 0))
        descripcion = item.get('descripcion', material)
        unidad = item.get('unidad', 'UN')
        stock_minimo = item.get('stock_minimo', 0)
        
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
            'quantity': stock_actual,
            'unit': unidad,
            'min_stock': stock_minimo,
            'max_stock': capacidad,
            'unit_value': 0  # No tenemos esta información
        })
        
        location['used_capacity'] += stock_actual
    
    # Convertir a lista y calcular ocupación
    locations_list = []
    for loc in location_map.values():
        ocupation_percent = 0
        if loc['capacity'] > 0:
            ocupation_percent = (loc['used_capacity'] / loc['capacity']) * 100
        
        # Determinar estado basado en porcentaje de ocupación
        status = 'vacio'
        if loc['used_capacity'] > 0:
            if ocupation_percent < 20:
                status = 'critico'
            elif ocupation_percent < 50:
                status = 'bajo'
            else:
                status = 'normal'
        
        # Calcular si hay materiales con stock crítico
        critical_materials = 0
        for mat in loc['materials']:
            if mat['quantity'] <= mat['min_stock']:
                critical_materials += 1
        
        # Calcular valor total (estimado)
        total_value = sum(mat['quantity'] for mat in loc['materials'])  # Sin valor unitario
        
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
            'critical_materials': critical_materials,
            'total_value': round(total_value, 2)
        })
    
    # Ordenar por zona, fila y columna
    locations_list.sort(key=lambda x: (x['zone'], x['row'], x['col']))
    
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
        'critical_locations': 0,
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
        
        if loc['critical_materials'] > 0:
            stats['critical_locations'] += 1
        
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
