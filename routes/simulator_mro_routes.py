# routes/simulator_mro_routes.py
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, timedelta
from models import db, Directory, Claim, Absence, Question, User
import json
import random

simulator_mro_bp = Blueprint('simulator_mro', __name__, url_prefix='/mro-simulator')

# ... decoradores existentes ...

@simulator_mro_bp.route('/access-directories', methods=['GET', 'POST'])
@login_required
@role_required(['planificador', 'supervisor', 'admin', 'owner'])
def access_directories():
    """Gestión de permisos de directorios del sistema"""
    
    if request.method == 'POST':
        directory_id = request.form.get('directory_id')
        new_permissions = request.form.get('permissions')
        
        # Actualizar en base de datos
        directory = Directory.query.get(directory_id)
        if directory:
            directory.permissions = new_permissions
            db.session.commit()
            flash(f'✅ Permisos actualizados para el directorio: {directory.name}', 'success')
        else:
            flash('❌ Directorio no encontrado', 'danger')
        
        return redirect(url_for('simulator_mro.access_directories'))
    
    # Obtener directorios reales de la base de datos
    directories = Directory.query.all()
    
    # Si no hay datos, puedes crear algunos de ejemplo para desarrollo
    if not directories and current_app.debug:
        directories = create_sample_directories()
    
    return render_template('simulator_mro/access_directories.html', 
                          directories=directories)

def create_sample_directories():
    """Crear directorios de ejemplo solo en modo desarrollo"""
    sample_dirs = [
        Directory(
            name='/mro/config/scenarios',
            size='45.2 MB',
            files_count=24,
            permissions='rwxr-xr-x',
            owner_id=1  # ID del admin
        ),
        # ... otros directorios ...
    ]
    # Solo agregar en desarrollo
    if current_app.debug:
        for dir in sample_dirs:
            db.session.add(dir)
        db.session.commit()
    return Directory.query.all()

@simulator_mro_bp.route('/database-claims', methods=['GET', 'POST'])
@login_required
def database_claims():
    """Visualizar y gestionar reclamaciones en base de datos"""
    
    if request.method == 'POST':
        action = request.form.get('action')
        claim_id = request.form.get('claim_id')
        
        claim = Claim.query.filter_by(id=claim_id).first()
        if claim:
            if action == 'resolve':
                claim.status = 'Resuelta'
                db.session.commit()
                flash(f'✅ Reclamación {claim_id} marcada como resuelta', 'success')
            elif action == 'assign':
                claim.assigned_to_id = current_user.id
                claim.status = 'Asignada'
                db.session.commit()
                flash(f'✅ Reclamación {claim_id} asignada a {current_user.username}', 'success')
        else:
            flash('❌ Reclamación no encontrada', 'danger')
        
        return redirect(url_for('simulator_mro.database_claims'))
    
    # Obtener reclamaciones reales de la base de datos
    claims = Claim.query.order_by(Claim.created_date.desc()).all()
    
    # Si no hay datos, crear algunos de ejemplo
    if not claims and current_app.debug:
        claims = create_sample_claims()
    
    return render_template('simulator_mro/database_claims.html', claims=claims)

def create_sample_claims():
    """Crear reclamaciones de ejemplo para desarrollo"""
    from datetime import datetime, timedelta
    
    sample_claims = [
        Claim(
            id='CLM-2024-001',
            claim_type='Falta de Material',
            description='Faltan 15 unidades de rodamiento SKF-6205 en ubicación A-12',
            priority='Alta',
            status='En Proceso',
            assigned_to_id=2,  # Juan Pérez
            created_date=datetime.now() - timedelta(days=2),
            due_date=datetime.now() + timedelta(days=3)
        ),
        # ... otras reclamaciones ...
    ]
    
    if current_app.debug:
        for claim in sample_claims:
            db.session.add(claim)
        db.session.commit()
    return Claim.query.all()

@simulator_mro_bp.route('/abscains', methods=['GET', 'POST'])
@login_required
@role_required(['supervisor', 'admin', 'owner'])
def abscains():
    """Gestión de ausencias del personal"""
    
    if request.method == 'POST':
        action = request.form.get('action')
        absence_id = request.form.get('absence_id')
        
        absence = Absence.query.get(absence_id)
        if absence:
            if action == 'approve':
                absence.status = 'Aprobada'
                absence.approved_by_id = current_user.id
                db.session.commit()
                flash(f'✅ Ausencia aprobada para {absence.employee.username}', 'success')
            elif action == 'reject':
                absence.status = 'Rechazada'
                db.session.commit()
                flash(f'❌ Ausencia rechazada para {absence.employee.username}', 'warning')
        else:
            flash('❌ Ausencia no encontrada', 'danger')
        
        return redirect(url_for('simulator_mro.abscains'))
    
    # Obtener ausencias reales
    if current_user.role in ['admin', 'owner']:
        # Admins ven todas las ausencias
        absences = Absence.query.order_by(Absence.start_date.desc()).all()
    else:
        # Supervisores ven solo las de su equipo
        absences = Absence.query.filter(
            Absence.employee_id.in_(
                [user.id for user in User.query.filter_by(department=current_user.department).all()]
            )
        ).order_by(Absence.start_date.desc()).all()
    
    return render_template('simulator_mro/abscains.html', 
                          absences=absences,
                          today_date=datetime.now().strftime('%Y-%m-%d'))

@simulator_mro_bp.route('/delete-questions', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'owner'])
def delete_questions():
    """Eliminación de preguntas obsoletas del banco de preguntas"""
    
    if request.method == 'POST':
        questions_to_delete = request.form.getlist('questions')
        reason = request.form.get('reason', '').strip()
        
        if questions_to_delete:
            # Obtener las preguntas
            questions = Question.query.filter(Question.id.in_(questions_to_delete)).all()
            
            # Registrar eliminación (soft delete)
            for question in questions:
                question.status = 'Deleted'
                question.deleted_at = datetime.utcnow()
                question.deleted_reason = reason
                question.deleted_by_id = current_user.id
            
            db.session.commit()
            
            flash(f'✅ {len(questions)} pregunta(s) marcadas como eliminadas', 'success')
            return redirect(url_for('simulator_mro.delete_questions'))
        else:
            flash('❌ Debe seleccionar al menos una pregunta', 'danger')
    
    # Obtener preguntas inactivas o poco usadas
    questions = Question.query.filter(
        (Question.status == 'Inactive') | 
        (Question.usage_count == 0) |
        (Question.last_used < datetime.utcnow() - timedelta(days=365))
    ).order_by(Question.usage_count.asc()).all()
    
    return render_template('simulator_mro/delete_questions.html', 
                          questions=questions)

# Función de utilidad para el filtro de días
def days_between(date1, date2):
    """Calcular días entre dos fechas"""
    if not date1 or not date2:
        return None
    return abs((date2 - date1).days)

# Registrar filtro en Jinja2
@simulator_mro_bp.app_context_processor
def utility_processor():
    return dict(daysBetween=days_between)
