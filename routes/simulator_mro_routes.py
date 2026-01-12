# routes/simulator_mro_routes.py
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, timedelta
import json
import random

simulator_mro_bp = Blueprint('simulator_mro', __name__, url_prefix='/mro-simulator')

# Decorador para roles específicos
def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if current_user.role not in roles:
                flash('No tienes permisos para acceder a esta sección', 'danger')
                return redirect(url_for('simulator_mro.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ============ RUTAS PRINCIPALES ============

@simulator_mro_bp.route('/')
@login_required
def dashboard():
    return render_template('simulator_mro/dashboard.html')

@simulator_mro_bp.route('/leaderboard')
@login_required
def get_leaderboard():
    return render_template('simulator_mro/leaderboard.html')

@simulator_mro_bp.route('/create-scenario')
@login_required
@role_required(['planificador', 'supervisor', 'admin', 'owner'])
def create_scenario():
    return render_template('simulator_mro/create_scenario.html')

# ============ MÓDULOS AVANZADOS ============

@simulator_mro_bp.route('/access-directories', methods=['GET', 'POST'])
@login_required
@role_required(['planificador', 'supervisor', 'admin', 'owner'])
def access_directories():
    """Gestión de permisos de directorios del sistema"""
    
    directories = [
        {'id': 1, 'name': '/mro/config/scenarios', 'files': 24, 'size': '45.2 MB', 
         'last_modified': '2024-01-10', 'permissions': 'rwxr-xr-x', 'owner': 'admin'},
        {'id': 2, 'name': '/mro/data/decisions', 'files': 156, 'size': '128.7 MB', 
         'last_modified': '2024-01-11', 'permissions': 'rwxrwxr-x', 'owner': 'planificador'},
        {'id': 3, 'name': '/mro/logs/simulations', 'files': 89, 'size': '210.5 MB', 
         'last_modified': '2024-01-12', 'permissions': 'rw-r--r--', 'owner': 'admin'},
        {'id': 4, 'name': '/mro/templates/questions', 'files': 42, 'size': '15.8 MB', 
         'last_modified': '2024-01-09', 'permissions': 'rwxr-x---', 'owner': 'supervisor'},
        {'id': 5, 'name': '/mro/backups/daily', 'files': 7, 'size': '1.2 GB', 
         'last_modified': '2024-01-12', 'permissions': 'rwx------', 'owner': 'admin'},
        {'id': 6, 'name': '/mro/uploads/user_data', 'files': 312, 'size': '356.4 MB', 
         'last_modified': '2024-01-12', 'permissions': 'rwxrwx---', 'owner': 'owner'},
    ]
    
    if request.method == 'POST':
        directory_id = request.form.get('directory_id')
        new_permissions = request.form.get('permissions')
        
        flash(f'✅ Permisos actualizados para el directorio ID: {directory_id}', 'success')
        return redirect(url_for('simulator_mro.access_directories'))
    
    return render_template('simulator_mro/access_directories.html', 
                          directories=directories)

@simulator_mro_bp.route('/create-claims', methods=['GET', 'POST'])
@login_required
@role_required(['planificador', 'supervisor', 'admin', 'owner'])
def create_claims():
    """Crear nuevas reclamaciones de problemas"""
    
    claim_types = [
        {'id': 1, 'name': 'Falta de Material', 'code': 'FM001', 'priority': 'Alta', 'avg_resolution': '2.5 días'},
        {'id': 2, 'name': 'Daño en Equipo', 'code': 'DE002', 'priority': 'Crítica', 'avg_resolution': '1 día'},
        {'id': 3, 'name': 'Error en Documentación', 'code': 'ED003', 'priority': 'Media', 'avg_resolution': '3 días'},
        {'id': 4, 'name': 'Retraso en Entrega', 'code': 'RE004', 'priority': 'Alta', 'avg_resolution': '5 días'},
        {'id': 5, 'name': 'Problema de Calidad', 'code': 'PC005', 'priority': 'Media', 'avg_resolution': '4 días'},
    ]
    
    last_id = f"CLM-{datetime.now().strftime('%Y-%m')}-{random.randint(100, 999)}"
    
    if request.method == 'POST':
        claim_type = request.form.get('claim_type')
        priority = request.form.get('priority')
        description = request.form.get('description')
        
        flash(f'✅ Reclamación creada exitosamente! ID: {last_id}', 'success')
        return redirect(url_for('simulator_mro.database_claims'))
    
    return render_template('simulator_mro/create_claims.html', 
                          claim_types=claim_types,
                          last_id=last_id)

@simulator_mro_bp.route('/database-claims', methods=['GET', 'POST'])
@login_required
def database_claims():
    """Visualizar y gestionar reclamaciones en base de datos"""
    
    claims = [
        {
            'id': 'CLM-2024-001', 
            'type': 'Falta de Material', 
            'description': 'Faltan 15 unidades de rodamiento SKF-6205 en ubicación A-12',
            'priority': 'Alta',
            'status': 'En Proceso',
            'assigned_to': 'Juan Pérez',
            'created_date': '2024-01-10',
            'due_date': '2024-01-15'
        },
        {
            'id': 'CLM-2024-002', 
            'type': 'Daño en Equipo', 
            'description': 'Máquina CNC Haas presenta error en eje Z',
            'priority': 'Crítica',
            'status': 'Pendiente',
            'assigned_to': 'María González',
            'created_date': '2024-01-11',
            'due_date': '2024-01-12'
        },
        {
            'id': 'CLM-2024-003', 
            'type': 'Error Documentación', 
            'description': 'Orden de trabajo #WT-4587 tiene datos incorrectos de repuestos',
            'priority': 'Media',
            'status': 'Resuelta',
            'assigned_to': 'Carlos Rodríguez',
            'created_date': '2024-01-09',
            'due_date': '2024-01-10'
        },
        {
            'id': 'CLM-2024-004', 
            'type': 'Retraso Entrega', 
            'description': 'Pedido #PO-7892 de motores Siemens con retraso de 3 días',
            'priority': 'Alta',
            'status': 'En Proceso',
            'assigned_to': 'Ana Martínez',
            'created_date': '2024-01-08',
            'due_date': '2024-01-11'
        },
    ]
    
    if request.method == 'POST':
        action = request.form.get('action')
        claim_id = request.form.get('claim_id')
        
        if action == 'resolve':
            flash(f'✅ Reclamación {claim_id} marcada como resuelta', 'success')
        elif action == 'assign':
            flash(f'✅ Reclamación {claim_id} asignada a {current_user.username}', 'success')
        
        return redirect(url_for('simulator_mro.database_claims'))
    
    return render_template('simulator_mro/database_claims.html', claims=claims)

@simulator_mro_bp.route('/warehouse-claims', methods=['GET', 'POST'])
@login_required
def warehouse_claims():
    """Reclamaciones específicas del almacén físico"""
    
    warehouse_data = {
        'total_claims': 24,
        'active_claims': 8,
        'resolved_today': 3,
        'avg_resolution_time': '2.3 horas',
        'locations': [
            {'zone': 'A', 'claims': 5, 'priority': 'Alta'},
            {'zone': 'B', 'claims': 3, 'priority': 'Media'},
            {'zone': 'C', 'claims': 7, 'priority': 'Crítica'},
            {'zone': 'D', 'claims': 4, 'priority': 'Alta'},
            {'zone': 'E', 'claims': 5, 'priority': 'Media'},
        ]
    }
    
    if request.method == 'POST':
        zone = request.form.get('zone')
        flash(f'✅ Reporte generado para Zona {zone}', 'success')
        return redirect(url_for('simulator_mro.warehouse_claims'))
    
    return render_template('simulator_mro/warehouse_claims.html', 
                          data=warehouse_data,
                          today=datetime.now().strftime('%d/%m/%Y'))

@simulator_mro_bp.route('/paytime', methods=['GET', 'POST'])
@login_required
def paytime():
    """Registro de tiempos de trabajo para nómina"""
    
    today = datetime.now().strftime('%Y-%m-%d')
    current_time = datetime.now().strftime('%H:%M')
    
    # Datos de ejemplo
    time_records = [
        {'id': 1, 'task': 'Conteo de Inventario - Zona A', 'start': '08:00', 'end': '10:30', 
         'duration': '2.5h', 'employee': current_user.username, 'project': 'INV-001'},
        {'id': 2, 'task': 'Picking de Órdenes Urgentes', 'start': '10:45', 'end': '12:30', 
         'duration': '1.75h', 'employee': current_user.username, 'project': 'PICK-045'},
        {'id': 3, 'task': 'Empaque para Envío', 'start': '13:30', 'end': '15:00', 
         'duration': '1.5h', 'employee': current_user.username, 'project': 'PACK-012'},
        {'id': 4, 'task': 'Auditoría de Calidad', 'start': '15:15', 'end': '16:45', 
         'duration': '1.5h', 'employee': current_user.username, 'project': 'QUAL-003'},
    ]
    
    total_hours = 7.25
    
    if request.method == 'POST':
        task = request.form.get('task')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        
        # Calcular duración
        start = datetime.strptime(start_time, '%H:%M')
        end = datetime.strptime(end_time, '%H:%M')
        duration = (end - start).seconds / 3600
        
        flash(f'✅ Tiempo registrado: {task} - {duration:.2f} horas', 'success')
        return redirect(url_for('simulator_mro.paytime'))
    
    return render_template('simulator_mro/paytime.html', 
                          time_records=time_records, 
                          total_hours=total_hours,
                          today=today,
                          current_time=current_time)

@simulator_mro_bp.route('/abscains', methods=['GET', 'POST'])
@login_required
@role_required(['supervisor', 'admin', 'owner'])
def abscains():
    """Gestión de ausencias del personal"""
    
    absences = [
        {
            'id': 1,
            'employee': 'Juan Pérez', 
            'type': 'Vacaciones', 
            'start_date': '2024-01-15',
            'end_date': '2024-01-19',
            'days': 5,
            'status': 'Aprobada',
            'reason': 'Vacaciones programadas',
            'approved_by': 'Carlos Rodríguez'
        },
        {
            'id': 2,
            'employee': 'María González', 
            'type': 'Enfermedad', 
            'start_date': '2024-01-12',
            'end_date': '2024-01-12',
            'days': 1,
            'status': 'Justificada',
            'reason': 'Consulta médica',
            'approved_by': 'Carlos Rodríguez'
        },
        {
            'id': 3,
            'employee': 'Carlos Rodríguez', 
            'type': 'Personal', 
            'start_date': '2024-01-18',
            'end_date': '2024-01-18',
            'days': 1,
            'status': 'Pendiente',
            'reason': 'Trámite personal',
            'approved_by': None
        },
        {
            'id': 4,
            'employee': 'Ana Martínez', 
            'type': 'Capacitación', 
            'start_date': '2024-01-22',
            'end_date': '2024-01-24',
            'days': 3,
            'status': 'Aprobada',
            'reason': 'Curso de seguridad industrial',
            'approved_by': 'Carlos Rodríguez'
        },
    ]
    
    if request.method == 'POST':
        action = request.form.get('action')
        absence_id = request.form.get('absence_id')
        
        if action == 'approve':
            flash(f'✅ Ausencia ID {absence_id} aprobada', 'success')
        elif action == 'reject':
            flash(f'❌ Ausencia ID {absence_id} rechazada', 'warning')
        
        return redirect(url_for('simulator_mro.abscains'))
    
    return render_template('simulator_mro/abscains.html', 
                          absences=absences,
                          today_date=datetime.now().strftime('%Y-%m-%d'))

@simulator_mro_bp.route('/delete-sections', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'owner'])
def delete_sections():
    """Eliminación segura de secciones del sistema (solo admin)"""
    
    sections = [
        {'id': 1, 'name': 'Escenarios de Prueba', 'created': '2023-12-01', 'items': 5, 'size': '45.2 MB', 'last_access': 'Hace 2 días'},
        {'id': 2, 'name': 'Preguntas Obsoletas', 'created': '2023-11-15', 'items': 12, 'size': '12.8 MB', 'last_access': 'Hace 3 semanas'},
        {'id': 3, 'name': 'Backups Antiguos', 'created': '2023-10-20', 'items': 8, 'size': '210.5 MB', 'last_access': 'Hace 2 meses'},
        {'id': 4, 'name': 'Registros de Debug', 'created': '2023-12-25', 'items': 42, 'size': '156.7 MB', 'last_access': 'Hace 1 semana'},
    ]
    
    if request.method == 'POST':
        sections_to_delete = request.form.getlist('sections')
        reason = request.form.get('reason')
        
        if sections_to_delete and reason:
            flash(f'✅ {len(sections_to_delete)} sección(es) eliminadas correctamente', 'success')
            return redirect(url_for('simulator_mro.delete_sections'))
        else:
            flash('❌ Debe seleccionar secciones y especificar un motivo', 'danger')
    
    return render_template('simulator_mro/delete_sections.html', 
                          sections=sections)

@simulator_mro_bp.route('/delete-questions', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'owner'])
def delete_questions():
    """Eliminación de preguntas obsoletas del banco de preguntas"""
    
    questions = [
        {'id': 101, 'text': '¿Cuál es el tiempo estándar para cambio de rodamiento?', 
         'category': 'Mantenimiento', 'created': '2023-09-10', 'used': 0, 'last_used': 'Nunca'},
        {'id': 102, 'text': 'Procedimiento obsoleto de inventario 2022', 
         'category': 'Inventario', 'created': '2022-11-05', 'used': 2, 'last_used': '2023-08-15'},
        {'id': 103, 'text': 'Pregunta de prueba sobre seguridad', 
         'category': 'Seguridad', 'created': '2023-12-20', 'used': 1, 'last_used': '2023-12-25'},
        {'id': 104, 'text': 'Equipos descontinuados en almacén', 
         'category': 'Equipos', 'created': '2023-08-15', 'used': 0, 'last_used': 'Nunca'},
        {'id': 105, 'text': 'Proceso de calidad anterior a normativa ISO-9001:2023', 
         'category': 'Calidad', 'created': '2023-06-30', 'used': 3, 'last_used': '2023-11-20'},
    ]
    
    if request.method == 'POST':
        questions_to_delete = request.form.getlist('questions')
        replacement_text = request.form.get('replacement_text')
        
        if questions_to_delete:
            flash(f'✅ {len(questions_to_delete)} pregunta(s) eliminadas del sistema', 'success')
            return redirect(url_for('simulator_mro.delete_questions'))
    
    return render_template('simulator_mro/delete_questions.html', 
                          questions=questions)

# ============ API ENDPOINTS ============

@simulator_mro_bp.route('/api/get-directory-info/<int:directory_id>')
@login_required
def get_directory_info(directory_id):
    """API para obtener información de directorio"""
    return jsonify({
        'id': directory_id,
        'name': f'/mro/directory/{directory_id}',
        'size': f'{random.randint(10, 500)} MB',
        'files': random.randint(5, 100),
        'last_modified': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

@simulator_mro_bp.route('/api/export-claims/<format>')
@login_required
def export_claims(format):
    """API para exportar reclamaciones"""
    return jsonify({
        'status': 'success',
        'message': f'Exportación {format} completada',
        'download_url': f'/downloads/claims_export.{format}'
    })
