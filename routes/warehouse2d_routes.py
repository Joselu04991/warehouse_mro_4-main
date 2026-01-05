# routes/warehouse2d_routes.py - VERSIÓN COMPLETA Y CORREGIDA

from flask import Blueprint, render_template, request, flash, redirect, url_for, session, jsonify, send_file
from flask_login import login_required, current_user
import pandas as pd
import json
from io import BytesIO
from datetime import datetime, timedelta
import xlsxwriter
import hashlib
import os
import tempfile
import sqlite3
import uuid
from functools import wraps

warehouse2d_bp = Blueprint('warehouse2d', __name__, template_folder='templates')

# ================= CONFIGURACIÓN =================
WAREHOUSE_DB = 'warehouse_data.db'
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
TEMP_DIR = tempfile.gettempdir() + '/warehouse_app/'

# Crear directorio temporal si no existe
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

# ================= BASE DE DATOS TEMPORAL =================
def init_warehouse_db():
    """Inicializar base de datos para almacenamiento temporal"""
    conn = sqlite3.connect(WAREHOUSE_DB)
    cursor = conn.cursor()
    
    # Tabla para datos de usuario
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS warehouse_sessions (
        session_id TEXT PRIMARY KEY,
        user_id TEXT,
        file_name TEXT,
        file_hash TEXT,
        total_records INTEGER,
        created_at TIMESTAMP,
        expires_at TIMESTAMP,
        metadata TEXT
    )
    ''')
    
    # Tabla para datos procesados (optimizado para el mapa)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS warehouse_locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        location_code TEXT,
        zone TEXT,
        row_num INTEGER,
        col_num INTEGER,
        material_code TEXT,
        material_desc TEXT,
        quantity REAL,
        capacity REAL,
        unit TEXT,
        ocupation_percent REAL,
        status TEXT,
        FOREIGN KEY (session_id) REFERENCES warehouse_sessions(session_id)
    )
    ''')
    
    # Índices para mejor rendimiento
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_session ON warehouse_locations(session_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_zone ON warehouse_locations(zone)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON warehouse_locations(status)')
    
    conn.commit()
    conn.close()

# Inicializar DB al importar
init_warehouse_db()

# ================= DECORADORES Y UTILIDADES =================
def get_user_session_id():
    """Obtener o crear ID de sesión para el usuario"""
    if 'warehouse_session_id' not in session:
        session['warehouse_session_id'] = str(uuid.uuid4())
    return session['warehouse_session_id']

def cleanup_old_sessions():
    """Limpiar sesiones antiguas (más de 24 horas)"""
    conn = sqlite3.connect(WAREHOUSE_DB)
    cursor = conn.cursor()
    
    cutoff_time = datetime.now() - timedelta(hours=24)
    cursor.execute('DELETE FROM warehouse_sessions WHERE expires_at < ?', (cutoff_time,))
    cursor.execute('DELETE FROM warehouse_locations WHERE session_id IN (SELECT session_id FROM warehouse_sessions WHERE expires_at < ?)', (cutoff_time,))
    
    conn.commit()
    conn.close()

def require_warehouse_session(f):
    """Decorador para requerir sesión de almacén"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_id = get_user_session_id()
        conn = sqlite3.connect(WAREHOUSE_DB)
        cursor = conn.cursor()
        
        cursor.execute('SELECT session_id FROM warehouse_sessions WHERE session_id = ?', (session_id,))
        has_data = cursor.fetchone() is not None
        
        conn.close()
        
        if not has_data and request.endpoint not in ['warehouse2d.upload_view', 'warehouse2d.upload_file', 'warehouse2d.upload_warehouse2d']:
            return redirect(url_for('warehouse2d.upload_view'))
        
        return f(*args, **kwargs)
    return decorated_function

# ================= RUTAS PRINCIPALES =================

@warehouse2d_bp.route('/')
@warehouse2d_bp.route('/map')
@warehouse2d_bp.route('/map-view')
@login_required
@require_warehouse_session
def index():
    """Página principal del mapa 2D"""
    session_id = get_user_session_id()
    
    conn = sqlite3.connect(WAREHOUSE_DB)
    cursor = conn.cursor()
    
    # Obtener metadata de la sesión
    cursor.execute('''
        SELECT file_name, created_at, total_records 
        FROM warehouse_sessions 
        WHERE session_id = ?
    ''', (session_id,))
    
    result = cursor.fetchone()
    
    if result:
        file_name, created_at, total_records = result
        last_update = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
        
        # Obtener estadísticas rápidas
        cursor.execute('''
            SELECT 
                COUNT(DISTINCT location_code) as total_locations,
                COUNT(DISTINCT material_code) as total_materials
            FROM warehouse_locations 
            WHERE session_id = ?
        ''', (session_id,))
        
        stats = cursor.fetchone()
        total_locations = stats[0] if stats else 0
        total_materials = stats[1] if stats else 0
        
        has_data = True
    else:
        file_name = 'Ninguno'
        last_update = 'Nunca'
        total_locations = 0
        total_materials = 0
        total_records = 0
        has_data = False
    
    conn.close()
    
    return render_template('warehouse2d/map.html',
                         has_data=has_data,
                         file_name=file_name,
                         last_update=last_update,
                         total_locations=total_locations,
                         total_materials=total_materials,
                         total_records=total_records)

# ================= ALIAS PARA COMPATIBILIDAD =================

@warehouse2d_bp.route('/map_view')
@login_required
def map_view():
    """Alias para compatibilidad - REDIRECT A INDEX"""
    return redirect(url_for('warehouse2d.index'))

# ================= RUTAS DE SUBIDA DE ARCHIVOS =================

@warehouse2d_bp.route('/upload', methods=['GET'])
@login_required
def upload_view():
    """Página para subir archivo Excel"""
    cleanup_old_sessions()  # Limpiar sesiones antiguas
    return render_template('warehouse2d/upload.html')

@warehouse2d_bp.route('/upload-warehouse2d')
@login_required
def upload_warehouse2d():
    """Alias para compatibilidad"""
    return redirect(url_for('warehouse2d.upload_view'))

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def parse_location_code(location_code):
    """Parsear código de ubicación en zona, fila y columna"""
    if not location_code:
        return 'A', 1, 1
    
    try:
        location_str = str(location_code).strip()
        
        # Diferentes formatos soportados
        if '-' in location_str:
            parts = location_str.split('-')
            zone = parts[0] if len(parts) > 0 else 'A'
            
            # Extraer números de fila
            row_num = 1
            if len(parts) > 1:
                row_part = parts[1]
                numbers = ''.join(filter(str.isdigit, row_part))
                row_num = int(numbers) if numbers else 1
            
            # Extraer números de columna
            col_num = 1
            if len(parts) > 2:
                col_part = parts[2]
                numbers = ''.join(filter(str.isdigit, col_part))
                col_num = int(numbers) if numbers else 1
            
            return zone, row_num, col_num
        
        elif location_str.isalnum():
            # Formato A0101
            zone = location_str[0] if location_str[0].isalpha() else 'A'
            numbers = ''.join(filter(str.isdigit, location_str))
            
            if len(numbers) >= 2:
                row_num = int(numbers[:2])
                col_num = int(numbers[2:4]) if len(numbers) >= 4 else 1
            else:
                row_num = 1
                col_num = 1
            
            return zone, row_num, col_num
        
        else:
            return 'A', 1, 1
            
    except Exception:
        return 'A', 1, 1

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
    
    # Verificar tamaño del archivo
    file.seek(0, 2)  # Ir al final del archivo
    file_size = file.tell()
    file.seek(0)  # Volver al inicio
    
    if file_size > MAX_FILE_SIZE:
        flash(f'El archivo es demasiado grande. Máximo permitido: {MAX_FILE_SIZE // (1024*1024)}MB', 'error')
        return redirect(url_for('warehouse2d.upload_view'))
    
    if file and allowed_file(file.filename):
        try:
            # Leer el archivo en chunks si es muy grande
            if file_size > 10 * 1024 * 1024:  # > 10MB
                chunks = []
                while True:
                    chunk = file.read(1024 * 1024)  # Leer 1MB a la vez
                    if not chunk:
                        break
                    chunks.append(chunk)
                file_content = b''.join(chunks)
                file_like = BytesIO(file_content)
            else:
                file_content = file.read()
                file_like = BytesIO(file_content)
            
            # Leer el archivo con pandas
            if file.filename.endswith('.csv'):
                df = pd.read_csv(file_like, encoding='utf-8', dtype=str, low_memory=False)
            else:
                df = pd.read_excel(file_like, dtype=str)
            
            # Normalizar nombres de columnas
            df.columns = df.columns.str.strip().str.lower()
            
            # Mapear nombres de columnas posibles
            column_mapping = {
                'ubicación': 'ubicacion',
                'location': 'ubicacion',
                'código del material': 'material',
                'codigo_material': 'material',
                'material_code': 'material',
                'stock máximo': 'capacidad',
                'stock_maximo': 'capacidad',
                'capacidad': 'capacidad',
                'libre utilización': 'cantidad',
                'libre_utilizacion': 'cantidad',
                'cantidad': 'cantidad',
                'stock': 'cantidad',
                'texto breve de material': 'descripcion',
                'descripcion': 'descripcion',
                'description': 'descripcion',
                'unidad de medida base': 'unidad',
                'unidad': 'unidad',
                'unit': 'unidad'
            }
            
            df = df.rename(columns=column_mapping)
            
            # Verificar columnas requeridas
            required_columns = ['ubicacion', 'material']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                flash(f'El archivo debe contener las columnas: {", ".join(missing_columns)}', 'error')
                return redirect(url_for('warehouse2d.upload_view'))
            
            # Limitar número de registros si es muy grande
            MAX_RECORDS = 100000
            if len(df) > MAX_RECORDS:
                df = df.head(MAX_RECORDS)
                flash(f'El archivo contiene muchos registros. Se procesarán solo los primeros {MAX_RECORDS}', 'warning')
            
            # Generar hash único del archivo
            file_hash = hashlib.md5(file_content).hexdigest()
            session_id = get_user_session_id()
            
            # Conectar a la base de datos
            conn = sqlite3.connect(WAREHOUSE_DB)
            cursor = conn.cursor()
            
            # Eliminar datos anteriores del usuario
            cursor.execute('DELETE FROM warehouse_sessions WHERE session_id = ?', (session_id,))
            cursor.execute('DELETE FROM warehouse_locations WHERE session_id = ?', (session_id,))
            
            # Procesar datos en lotes para mejor rendimiento
            batch_size = 1000
            total_inserted = 0
            
            for i in range(0, len(df), batch_size):
                batch = df.iloc[i:i + batch_size]
                locations_data = []
                
                for _, row in batch.iterrows():
                    ubicacion = str(row.get('ubicacion', '')).strip()
                    if not ubicacion:
                        continue
                    
                    # Parsear ubicación
                    zone, row_num, col_num = parse_location_code(ubicacion)
                    
                    # Obtener datos del material
                    material = str(row.get('material', '')).strip()
                    descripcion = str(row.get('descripcion', material)).strip()[:200]
                    unidad = str(row.get('unidad', 'UN')).strip()
                    
                    # Convertir cantidades
                    try:
                        cantidad = float(str(row.get('cantidad', '0')).replace(',', '.'))
                    except:
                        cantidad = 0.0
                    
                    try:
                        capacidad = float(str(row.get('capacidad', '100')).replace(',', '.'))
                    except:
                        capacidad = 100.0
                    
                    if capacidad <= 0:
                        capacidad = 100.0
                    
                    # Calcular ocupación y estado
                    ocupacion_percent = (cantidad / capacidad * 100) if capacidad > 0 else 0
                    
                    if cantidad <= 0:
                        status = 'vacio'
                    elif ocupacion_percent < 20:
                        status = 'critico'
                    elif ocupacion_percent < 50:
                        status = 'bajo'
                    else:
                        status = 'normal'
                    
                    locations_data.append((
                        session_id, ubicacion, zone, row_num, col_num,
                        material, descripcion, cantidad, capacidad, unidad,
                        round(ocupacion_percent, 2), status
                    ))
                
                # Insertar lote en la base de datos
                cursor.executemany('''
                    INSERT INTO warehouse_locations 
                    (session_id, location_code, zone, row_num, col_num, material_code, 
                     material_desc, quantity, capacity, unit, ocupation_percent, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', locations_data)
                
                total_inserted += len(locations_data)
            
            # Guardar metadata de la sesión
            created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            expires_at = (datetime.now() + timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute('''
                INSERT INTO warehouse_sessions 
                (session_id, user_id, file_name, file_hash, total_records, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (session_id, str(current_user.id) if current_user.is_authenticated else 'anonymous',
                  file.filename, file_hash, total_inserted, created_at, expires_at))
            
            conn.commit()
            conn.close()
            
            flash(f'Archivo "{file.filename}" cargado exitosamente. {total_inserted} ubicaciones procesadas.', 'success')
            return redirect(url_for('warehouse2d.index'))
            
        except Exception as e:
            flash(f'Error al procesar el archivo: {str(e)}', 'error')
            return redirect(url_for('warehouse2d.upload_view'))
    
    flash('Tipo de archivo no permitido. Use .xlsx, .xls o .csv', 'error')
    return redirect(url_for('warehouse2d.upload_view'))

# ================= RUTAS DE API Y DATOS =================

@warehouse2d_bp.route('/get-data')
@login_required
@require_warehouse_session
def get_warehouse_data():
    """Obtener datos del almacén (limitado para vista previa)"""
    try:
        session_id = get_user_session_id()
        
        conn = sqlite3.connect(WAREHOUSE_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Obtener metadata
        cursor.execute('SELECT file_name, created_at, total_records FROM warehouse_sessions WHERE session_id = ?', (session_id,))
        session_data = cursor.fetchone()
        
        if not session_data:
            return jsonify({
                'success': False,
                'message': 'No hay datos cargados'
            }), 404
        
        # Obtener muestra de datos (máximo 100 registros para vista previa)
        cursor.execute('''
            SELECT location_code, zone, row_num, col_num, material_code, 
                   material_desc, quantity, capacity, unit, ocupation_percent, status
            FROM warehouse_locations 
            WHERE session_id = ? 
            LIMIT 100
        ''', (session_id,))
        
        rows = cursor.fetchall()
        data = [dict(row) for row in rows]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': data,
            'file_name': session_data['file_name'],
            'last_update': session_data['created_at'],
            'total_records': session_data['total_records'],
            'message': 'Datos cargados correctamente'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@warehouse2d_bp.route('/map-data')
@login_required
@require_warehouse_session
def map_data():
    """Datos optimizados para el mapa"""
    try:
        session_id = get_user_session_id()
        
        conn = sqlite3.connect(WAREHOUSE_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Obtener estadísticas generales
        cursor.execute('''
            SELECT 
                COUNT(*) as total_locations,
                COUNT(DISTINCT material_code) as total_materials,
                MAX(row_num) as max_row,
                MAX(col_num) as max_col,
                GROUP_CONCAT(DISTINCT zone) as zones
            FROM warehouse_locations 
            WHERE session_id = ?
        ''', (session_id,))
        
        stats = cursor.fetchone()
        
        if not stats or stats['total_locations'] == 0:
            return jsonify({'success': True, 'locations': [], 'stats': {}})
        
        # Obtener datos para el mapa (solo campos necesarios)
        cursor.execute('''
            SELECT 
                location_code as code,
                zone,
                row_num as row,
                col_num as col,
                material_code as material,
                material_desc as description,
                quantity,
                capacity,
                unit,
                ocupation_percent,
                status
            FROM warehouse_locations 
            WHERE session_id = ?
            ORDER BY zone, row_num, col_num
        ''', (session_id,))
        
        rows = cursor.fetchall()
        locations = [dict(row) for row in rows]
        
        conn.close()
        
        # Convertir string de zonas a lista
        zones_list = stats['zones'].split(',') if stats['zones'] else []
        
        return jsonify({
            'success': True,
            'locations': locations,
            'stats': {
                'total': stats['total_locations'],
                'materials': stats['total_materials'],
                'max_row': stats['max_row'] or 0,
                'max_col': stats['max_col'] or 0,
                'zones': zones_list
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@warehouse2d_bp.route('/stats')
@login_required
@require_warehouse_session
def get_stats():
    """Obtener estadísticas detalladas"""
    try:
        session_id = get_user_session_id()
        
        conn = sqlite3.connect(WAREHOUSE_DB)
        cursor = conn.cursor()
        
        # Estadísticas por estado
        cursor.execute('''
            SELECT 
                status,
                COUNT(*) as count,
                ROUND(AVG(ocupation_percent), 2) as avg_ocupation,
                SUM(quantity) as total_quantity,
                SUM(capacity) as total_capacity
            FROM warehouse_locations 
            WHERE session_id = ?
            GROUP BY status
        ''', (session_id,))
        
        status_stats = {}
        for row in cursor.fetchall():
            status_stats[row[0]] = {
                'count': row[1],
                'avg_ocupation': row[2],
                'total_quantity': row[3],
                'total_capacity': row[4]
            }
        
        # Estadísticas por zona
        cursor.execute('''
            SELECT 
                zone,
                COUNT(*) as count,
                SUM(quantity) as total_quantity,
                SUM(capacity) as total_capacity
            FROM warehouse_locations 
            WHERE session_id = ?
            GROUP BY zone
            ORDER BY zone
        ''', (session_id,))
        
        zone_stats = []
        for row in cursor.fetchall():
            zone_stats.append({
                'zone': row[0],
                'count': row[1],
                'total_quantity': row[2],
                'total_capacity': row[3]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'status_stats': status_stats,
            'zone_stats': zone_stats
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
        
        # Formato para encabezados
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4CAF50',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        # Formato para ejemplos
        example_format = workbook.add_format({
            'border': 1,
            'align': 'left'
        })
        
        # Ancho de columnas
        worksheet.set_column('A:A', 15)
        worksheet.set_column('B:B', 20)
        worksheet.set_column('C:C', 30)
        worksheet.set_column('D:D', 15)
        worksheet.set_column('E:E', 15)
        worksheet.set_column('F:F', 15)
        worksheet.set_column('G:G', 15)
        
        # Escribir encabezados
        headers = [
            'Ubicación*', 
            'Código del Material*', 
            'Texto breve de material', 
            'Unidad de medida base', 
            'Stock de seguridad', 
            'Stock máximo', 
            'Libre utilización'
        ]
        
        for i, header in enumerate(headers):
            worksheet.write(0, i, header, header_format)
        
        # Instrucciones
        worksheet.write(2, 0, '* Campos obligatorios', workbook.add_format({'bold': True, 'font_color': 'red'}))
        worksheet.write(3, 0, 'Formato de ubicación: Zona-Fila-Columna (ej: A-01-01)')
        
        # Ejemplos
        examples = [
            ['A-01-01', 'MAT-001', 'Tornillo M8 x 20mm', 'UN', 10, 1000, 100],
            ['A-01-02', 'MAT-002', 'Tuerca M8', 'UN', 5, 1000, 150],
            ['B-02-01', 'MAT-003', 'Arandela plana 8mm', 'UN', 20, 5000, 1200],
            ['B-02-02', 'MAT-004', 'Perno hexagonal M10x50', 'UN', 8, 800, 65]
        ]
        
        for row_num, row_data in enumerate(examples, start=5):
            for col_num, cell_data in enumerate(row_data):
                worksheet.write(row_num, col_num, cell_data, example_format)
        
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
        return redirect(url_for('warehouse2d.upload_view'))

@warehouse2d_bp.route('/export-excel')
@login_required
@require_warehouse_session
def export_excel():
    """Exportar datos a Excel"""
    try:
        session_id = get_user_session_id()
        
        conn = sqlite3.connect(WAREHOUSE_DB)
        cursor = conn.cursor()
        
        # Obtener metadata
        cursor.execute('SELECT file_name FROM warehouse_sessions WHERE session_id = ?', (session_id,))
        session_data = cursor.fetchone()
        
        if not session_data:
            flash('No hay datos para exportar', 'warning')
            return redirect(url_for('warehouse2d.index'))
        
        # Obtener todos los datos
        cursor.execute('''
            SELECT 
                location_code,
                zone,
                row_num,
                col_num,
                material_code,
                material_desc,
                quantity,
                capacity,
                unit,
                ocupation_percent,
                status
            FROM warehouse_locations 
            WHERE session_id = ?
            ORDER BY zone, row_num, col_num
        ''', (session_id,))
        
        rows = cursor.fetchall()
        
        if not rows:
            flash('No hay datos para exportar', 'warning')
            return redirect(url_for('warehouse2d.index'))
        
        conn.close()
        
        # Crear DataFrame
        df = pd.DataFrame(rows, columns=[
            'Ubicación', 'Zona', 'Fila', 'Columna', 'Material',
            'Descripción', 'Cantidad', 'Capacidad', 'Unidad',
            'Ocupación %', 'Estado'
        ])
        
        # Crear archivo Excel en memoria
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Datos Almacén', index=False)
            
            # Formato
            workbook = writer.book
            worksheet = writer.sheets['Datos Almacén']
            
            # Formato para encabezados
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#366092',
                'font_color': 'white',
                'border': 1
            })
            
            # Formato para porcentajes
            percent_format = workbook.add_format({'num_format': '0.00%'})
            
            # Aplicar formatos
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
            
            # Ajustar ancho de columnas
            for i, column in enumerate(df.columns):
                column_width = max(df[column].astype(str).map(len).max(), len(column)) + 2
                worksheet.set_column(i, i, min(column_width, 50))
        
        output.seek(0)
        
        filename = f'almacen_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        flash(f'Error al exportar: {str(e)}', 'error')
        return redirect(url_for('warehouse2d.index'))

@warehouse2d_bp.route('/clear-data', methods=['POST'])
@login_required
def clear_data():
    """Limpiar datos"""
    try:
        session_id = get_user_session_id()
        
        conn = sqlite3.connect(WAREHOUSE_DB)
        cursor = conn.cursor()
        
        # Eliminar datos del usuario
        cursor.execute('DELETE FROM warehouse_sessions WHERE session_id = ?', (session_id,))
        cursor.execute('DELETE FROM warehouse_locations WHERE session_id = ?', (session_id,))
        
        conn.commit()
        conn.close()
        
        # Limpiar sesión
        session.pop('warehouse_session_id', None)
        
        return jsonify({
            'success': True, 
            'message': 'Datos eliminados correctamente'
        })
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': str(e)
        }), 500

@warehouse2d_bp.route('/search-locations')
@login_required
@require_warehouse_session
def search_locations():
    """Buscar ubicaciones"""
    try:
        query = request.args.get('q', '').strip()
        session_id = get_user_session_id()
        
        if not query or len(query) < 2:
            return jsonify({'success': True, 'results': []})
        
        conn = sqlite3.connect(WAREHOUSE_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        search_term = f'%{query}%'
        
        cursor.execute('''
            SELECT 
                location_code, zone, row_num, col_num, material_code,
                material_desc, quantity, capacity, ocupation_percent, status
            FROM warehouse_locations 
            WHERE session_id = ? AND (
                location_code LIKE ? OR
                zone LIKE ? OR
                material_code LIKE ? OR
                material_desc LIKE ?
            )
            ORDER BY location_code
            LIMIT 50
        ''', (session_id, search_term, search_term, search_term, search_term))
        
        rows = cursor.fetchall()
        results = [dict(row) for row in rows]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

# ================= TAREAS DE MANTENIMIENTO =================

@warehouse2d_bp.route('/cleanup', methods=['POST'])
@login_required
def cleanup_all():
    """Limpiar todos los datos temporales (solo admin)"""
    try:
        # Esta función debería estar protegida para solo administradores
        # En producción, añade verificación de rol
        
        conn = sqlite3.connect(WAREHOUSE_DB)
        cursor = conn.cursor()
        
        # Eliminar todas las sesiones expiradas
        cutoff_time = datetime.now() - timedelta(hours=24)
        cursor.execute('DELETE FROM warehouse_sessions WHERE expires_at < ?', (cutoff_time.strftime('%Y-%m-%d %H:%M:%S'),))
        cursor.execute('DELETE FROM warehouse_locations WHERE session_id IN (SELECT session_id FROM warehouse_sessions WHERE expires_at < ?)', (cutoff_time.strftime('%Y-%m-%d %H:%M:%S'),))
        
        # Vaciar tablas si están muy grandes (más de 1M registros)
        cursor.execute('SELECT COUNT(*) FROM warehouse_locations')
        count = cursor.fetchone()[0]
        
        if count > 1000000:
            cursor.execute('DELETE FROM warehouse_locations WHERE id IN (SELECT id FROM warehouse_locations ORDER BY id DESC LIMIT 500000 OFFSET 500000)')
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Limpieza completada. Registros eliminados: {count}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# ================= ERROR HANDLERS =================

@warehouse2d_bp.errorhandler(413)
def too_large(e):
    """Manejador para archivos demasiado grandes"""
    return jsonify({
        'success': False,
        'message': f'Archivo demasiado grande. Máximo permitido: {MAX_FILE_SIZE // (1024*1024)}MB'
    }), 413

@warehouse2d_bp.errorhandler(404)
def not_found(e):
    """Manejador para rutas no encontradas"""
    return jsonify({
        'success': False,
        'message': 'Recurso no encontrado'
    }), 404

@warehouse2d_bp.errorhandler(500)
def internal_error(e):
    """Manejador para errores internos"""
    return jsonify({
        'success': False,
        'message': 'Error interno del servidor'
    }), 500
