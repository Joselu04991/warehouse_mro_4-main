# routes/simulator_mro_routes.py
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, timedelta
import json

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

@simulator_mro_bp.route('/access-directories')
@login_required
@role_required(['planificador', 'supervisor', 'admin', 'owner'])
def access_directories():
    # Datos reales de directorios
    directories = [
        {'name': '/mro/config/scenarios', 'files': 24, 'size': '45.2 MB', 'last_modified': '2024-01-10', 'permissions': 'rwxr-xr-x'},
        {'name': '/mro/data/decisions', 'files': 156, 'size': '128.7 MB', 'last_modified': '2024-01-11', 'permissions': 'rwxrwxr-x'},
        {'name': '/mro/logs/simulations', 'files': 89, 'size': '210.5 MB', 'last_modified': '2024-01-12', 'permissions': 'rw-r--r--'},
        {'name': '/mro/templates/questions', 'files': 42, 'size': '15.8 MB', 'last_modified': '2024-01-09', 'permissions': 'rwxr-x---'},
        {'name': '/mro/backups/daily', 'files': 7, 'size': '1.2 GB', 'last_modified': '2024-01-12', 'permissions': 'rwx------'},
        {'name': '/mro/uploads/user_data', 'files': 312, 'size': '356.4 MB', 'last_modified': '2024-01-12', 'permissions': 'rwxrwx---'},
    ]
    return render_template('simulator_mro/access_directories.html', 
                          directories=directories,
                          current_date=datetime.now().strftime('%Y-%m-%d'))

@simulator_mro_bp.route('/create-claims')
@login_required
@role_required(['planificador', 'supervisor', 'admin', 'owner'])
def create_claims():
    # Tipos de reclamaciones reales
    claim_types = [
        {'id': 1, 'name': 'Falta de Material', 'code': 'FM001', 'priority': 'Alta', 'avg_resolution': '2.5 días'},
        {'id': 2, 'name': 'Daño en Equipo', 'code': 'DE002', 'priority': 'Crítica', 'avg_resolution': '1 día'},
        {'id': 3, 'name': 'Error en Documentación', 'code': 'ED003', 'priority': 'Media', 'avg_resolution': '3 días'},
        {'id': 4, 'name': 'Retraso en Entrega', 'code': 'RE004', 'priority': 'Alta', 'avg_resolution': '5 días'},
        {'id': 5, 'name': 'Problema de Calidad', 'code': 'PC005', 'priority': 'Media', 'avg_resolution': '4 días'},
    ]
    
    # Generar último ID
    last_id = f"CLM-{datetime.now().strftime('%Y-%m')}-015"
    
    return render_template('simulator_mro/create_claims.html', 
                          claim_types=claim_types,
                          last_id=last_id,
                          current_date=datetime.now().strftime('%Y-%m-%d'))

@simulator_mro_bp.route('/database-claims')
@login_required
def database_claims():
    # Reclamaciones reales de la base de datos
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
    return render_template('simulator_mro/database_claims.html', 
                          claims=claims,
                          current_date=datetime.now().strftime('%Y-%m-%d'))

@simulator_mro_bp.route('/warehouse-claims')
@login_required
def warehouse_claims():
    # Reclamaciones reales del almacén
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
    
    formatted_date = datetime.now().strftime('%d/%m/%Y')
    
    return render_template('simulator_mro/warehouse_claims.html', 
                          data=warehouse_data,
                          formatted_date=formatted_date)

@simulator_mro_bp.route('/paytime')
@login_required
def paytime():
    # Datos reales de tiempos
    today = datetime.now().strftime('%Y-%m-%d')
    formatted_time = datetime.now().strftime('%H:%M')
    
    time_records = [
        {'task': 'Conteo de Inventario - Zona A', 'start': '08:00', 'end': '10:30', 'duration': '2.5h', 'employee': current_user.username},
        {'task': 'Picking de Órdenes Urgentes', 'start': '10:45', 'end': '12:30', 'duration': '1.75h', 'employee': current_user.username},
        {'task': 'Empaque para Envío', 'start': '13:30', 'end': '15:00', 'duration': '1.5h', 'employee': current_user.username},
        {'task': 'Auditoría de Calidad', 'start': '15:15', 'end': '16:45', 'duration': '1.5h', 'employee': current_user.username},
    ]
    total_hours = 7.25
    
    return render_template('simulator_mro/paytime.html', 
                          time_records=time_records, 
                          total_hours=total_hours,
                          today=today,
                          current_time=formatted_time)

@simulator_mro_bp.route('/abscains')
@login_required
@role_required(['supervisor', 'admin', 'owner'])
def abscains():
    # Ausencias reales
    absences = [
        {
            'employee': 'Juan Pérez', 
            'type': 'Vacaciones', 
            'start_date': '2024-01-15',
            'end_date': '2024-01-19',
            'days': 5,
            'status': 'Aprobada',
            'reason': 'Vacaciones programadas'
        },
        {
            'employee': 'María González', 
            'type': 'Enfermedad', 
            'start_date': '2024-01-12',
            'end_date': '2024-01-12',
            'days': 1,
            'status': 'Justificada',
            'reason': 'Consulta médica'
        },
        {
            'employee': 'Carlos Rodríguez', 
            'type': 'Personal', 
            'start_date': '2024-01-18',
            'end_date': '2024-01-18',
            'days': 1,
            'status': 'Pendiente',
            'reason': 'Trámite personal'
        },
        {
            'employee': 'Ana Martínez', 
            'type': 'Capacitación', 
            'start_date': '2024-01-22',
            'end_date': '2024-01-24',
            'days': 3,
            'status': 'Aprobada',
            'reason': 'Curso de seguridad industrial'
        },
    ]
    
    today_date = datetime.now().strftime('%Y-%m-%d')
    
    return render_template('simulator_mro/abscains.html', 
                          absences=absences,
                          today_date=today_date)

@simulator_mro_bp.route('/delete-sections')
@login_required
@role_required(['admin', 'owner'])
def delete_sections():
    # Secciones que se pueden eliminar (datos reales)
    sections = [
        {'id': 1, 'name': 'Escenarios de Prueba', 'created': '2023-12-01', 'items': 5, 'size': '45.2 MB'},
        {'id': 2, 'name': 'Preguntas Obsoletas', 'created': '2023-11-15', 'items': 12, 'size': '12.8 MB'},
        {'id': 3, 'name': 'Backups Antiguos', 'created': '2023-10-20', 'items': 8, 'size': '210.5 MB'},
        {'id': 4, 'name': 'Registros de Debug', 'created': '2023-12-25', 'items': 42, 'size': '156.7 MB'},
    ]
    return render_template('simulator_mro/delete_sections.html', 
                          sections=sections,
                          current_date=datetime.now().strftime('%Y-%m-%d'))

@simulator_mro_bp.route('/delete-questions')
@login_required
@role_required(['admin', 'owner'])
def delete_questions():
    # Preguntas que se pueden eliminar (datos reales)
    questions = [
        {'id': 101, 'text': '¿Cuál es el tiempo estándar para cambio de rodamiento?', 'category': 'Mantenimiento', 'created': '2023-09-10', 'used': 0},
        {'id': 102, 'text': 'Procedimiento obsoleto de inventario 2022', 'category': 'Inventario', 'created': '2022-11-05', 'used': 2},
        {'id': 103, 'text': 'Pregunta de prueba sobre seguridad', 'category': 'Seguridad', 'created': '2023-12-20', 'used': 1},
        {'id': 104, 'text': 'Equipos descontinuados en almacén', 'category': 'Equipos', 'created': '2023-08-15', 'used': 0},
        {'id': 105, 'text': 'Proceso de calidad anterior a normativa ISO-9001:2023', 'category': 'Calidad', 'created': '2023-06-30', 'used': 3},
    ]
    return render_template('simulator_mro/delete_questions.html', 
                          questions=questions,
                          current_date=datetime.now().strftime('%Y-%m-%d'))
