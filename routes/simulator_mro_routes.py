# routes/simulator_mro_routes.py - VERSIÓN CORREGIDA
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

simulator_mro_bp = Blueprint('simulator_mro', __name__, url_prefix='/mro-simulator')

@simulator_mro_bp.route('/')
@login_required
def dashboard():
    """Dashboard principal del simulador MRO"""
    # Verificar si el usuario tiene rol MRO válido
    if current_user.role not in ['aprendiz', 'tecnico_almacen', 'planificador', 'supervisor', 'admin', 'owner', 'user']:
        return render_template('simulator_mro/access_denied.html')
    
    return render_template('simulator_mro/dashboard.html')

@simulator_mro_bp.route('/play/<int:scenario_id>')
@login_required
def play_scenario(scenario_id):
    """Página para jugar un escenario"""
    if current_user.role not in ['aprendiz', 'tecnico_almacen', 'planificador', 'supervisor', 'admin', 'owner', 'user']:
        return render_template('simulator_mro/access_denied.html')
    
    return render_template('simulator_mro/play.html', scenario_id=scenario_id)

@simulator_mro_bp.route('/create')
@login_required 
def create_scenario():
    """Vista para crear escenarios (solo planificadores)"""
    if current_user.role not in ['planificador', 'supervisor', 'admin', 'owner']:
        return render_template('simulator_mro/access_denied.html')
    
    return render_template('simulator_mro/create_scenario.html')

@simulator_mro_bp.route('/leaderboard')
@login_required
def get_leaderboard():
    """Tabla de clasificación"""
    if current_user.role not in ['aprendiz', 'tecnico_almacen', 'planificador', 'supervisor', 'admin', 'owner', 'user']:
        return render_template('simulator_mro/access_denied.html')
    
    return render_template('simulator_mro/leaderboard.html')

# Ruta adicional para estadísticas
@simulator_mro_bp.route('/stats')
@login_required
def stats():
    """Estadísticas del usuario"""
    if current_user.role not in ['aprendiz', 'tecnico_almacen', 'planificador', 'supervisor', 'admin', 'owner', 'user']:
        return render_template('simulator_mro/access_denied.html')
    
    return render_template('simulator_mro/stats.html')
