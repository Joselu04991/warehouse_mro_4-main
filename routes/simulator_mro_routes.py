# routes/simulator_mro_routes.py
from flask import Blueprint, jsonify, request, session, render_template
from flask_login import login_required, current_user
from models import db
from models.user import User
from models.scenario_mro import ScenarioMRO, UserDecisionMRO
import random
from datetime import datetime
import json

simulator_mro_bp = Blueprint('simulator_mro', __name__, url_prefix='/mro-simulator')

# ============================================
# VISTAS PRINCIPALES
# ============================================

@simulator_mro_bp.route('/')
@login_required
def dashboard():
    """Dashboard principal del simulador MRO"""
    user = User.query.get(current_user.id)
    
    # Verificar si el usuario tiene rol MRO
    if user.role not in ['aprendiz', 'tecnico_almacen', 'planificador', 'supervisor']:
        return render_template('simulator_mro/access_denied.html', 
                             message="Este simulador es solo para personal de almacén MRO")
    
    # Obtener estadísticas del usuario
    user_stats = user.to_mro_dict()
    
    # Obtener escenarios accesibles
    accessible_scenarios = ScenarioMRO.query.filter_by(is_active=True).all()
    accessible_scenarios = [s for s in accessible_scenarios if s.is_accessible_for(user.role)]
    
    # Obtener historial reciente
    recent_decisions = UserDecisionMRO.query.filter_by(
        user_id=user.id
    ).order_by(UserDecisionMRO.decision_time.desc()).limit(5).all()
    
    # Obtener leaderboard para el rol del usuario
    leaderboard = get_leaderboard_for_role(user.role, limit=10)
    
    return render_template('simulator_mro/dashboard.html',
                         user=user_stats,
                         scenarios=accessible_scenarios,
                         recent_decisions=recent_decisions,
                         leaderboard=leaderboard)


@simulator_mro_bp.route('/play/<int:scenario_id>')
@login_required
def play_scenario(scenario_id):
    """Página para jugar un escenario específico"""
    user = User.query.get(current_user.id)
    scenario = ScenarioMRO.query.get_or_404(scenario_id)
    
    # Verificar acceso
    if not scenario.is_accessible_for(user.role):
        return render_template('simulator_mro/access_denied.html',
                             message="No tienes acceso a este escenario")
    
    return render_template('simulator_mro/play.html',
                         user=user.to_mro_dict(),
                         scenario=scenario.to_dict())


@simulator_mro_bp.route('/scenario/create', methods=['GET', 'POST'])
@login_required
def create_scenario():
    """Vista para que el planificador cree escenarios (solo planificadores y supervisores)"""
    user = User.query.get(current_user.id)
    
    if user.role not in ['planificador', 'supervisor', 'admin']:
        return render_template('simulator_mro/access_denied.html',
                             message="Solo planificadores pueden crear escenarios")
    
    if request.method == 'GET':
        return render_template('simulator_mro/create_scenario.html')
    
    # POST: Crear nuevo escenario
    data = request.form
    
    # Generar código único
    last_scenario = ScenarioMRO.query.order_by(ScenarioMRO.id.desc()).first()
    next_code = f"SCEN-MRO-{str(last_scenario.id + 1).zfill(3)}" if last_scenario else "SCEN-MRO-001"
    
    # Crear escenario
    scenario = ScenarioMRO(
        scenario_code=next_code,
        title=data.get('title'),
        description=data.get('description'),
        category=data.get('category'),
        target_roles=data.get('target_roles'),
        difficulty=int(data.get('difficulty', 1)),
        estimated_time=int(data.get('estimated_time', 300)),
        warehouse_zone=data.get('warehouse_zone'),
        material_type=data.get('material_type'),
        criticality=data.get('criticality'),
        sap_transaction=data.get('sap_transaction'),
        sap_data_json=json.loads(data.get('sap_data_json', '{}')),
        option_a=data.get('option_a'),
        option_b=data.get('option_b'),
        option_c=data.get('option_c'),
        correct_option=data.get('correct_option'),
        points_aprendiz=int(data.get('points_aprendiz', 100)),
        points_tecnico=int(data.get('points_tecnico', 80)),
        points_planificador=int(data.get('points_planificador', 60)),
        feedback_correct=data.get('feedback_correct'),
        feedback_incorrect=data.get('feedback_incorrect'),
        professional_analysis=data.get('professional_analysis'),
        sap_procedure=data.get('sap_procedure'),
        safety_considerations=data.get('safety_considerations'),
        key_learning=data.get('key_learning'),
        created_by=user.id
    )
    
    db.session.add(scenario)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Escenario creado exitosamente',
        'scenario_id': scenario.id
    })


# ============================================
# API ENDPOINTS
# ============================================

@simulator_mro_bp.route('/api/random-scenario')
@login_required
def get_random_scenario():
    """Obtiene un escenario aleatorio adecuado para el rol del usuario"""
    user = User.query.get(current_user.id)
    
    # Filtrar por rol y dificultad progresiva
    accessible_scenarios = ScenarioMRO.query.filter_by(is_active=True).all()
    accessible_scenarios = [s for s in accessible_scenarios if s.is_accessible_for(user.role)]
    
    if not accessible_scenarios:
        return jsonify({'error': 'No hay escenarios disponibles para tu rol'}), 404
    
    # Ajustar dificultad según nivel del usuario
    if user.mro_xp < 500:
        difficulty_filter = [1, 2]
    elif user.mro_xp < 2000:
        difficulty_filter = [1, 2, 3]
    else:
        difficulty_filter = [2, 3, 4]
    
    # Filtrar por dificultad
    filtered_scenarios = [s for s in accessible_scenarios if s.difficulty in difficulty_filter]
    
    if not filtered_scenarios:
        filtered_scenarios = accessible_scenarios
    
    # Seleccionar escenario (ponderado por dificultad)
    weights = [6 - s.difficulty for s in filtered_scenarios]  # Más peso a menor dificultad
    selected_scenario = random.choices(filtered_scenarios, weights=weights, k=1)[0]
    
    return jsonify(selected_scenario.to_dict())


@simulator_mro_bp.route('/api/evaluate', methods=['POST'])
@login_required
def evaluate_decision():
    """Evalúa una decisión del usuario"""
    data = request.get_json()
    user = User.query.get(current_user.id)
    
    scenario_id = data.get('scenario_id')
    selected_option = data.get('selected_option')
    time_taken = data.get('time_taken', 0)
    
    scenario = ScenarioMRO.query.get(scenario_id)
    if not scenario:
        return jsonify({'error': 'Escenario no encontrado'}), 404
    
    # Evaluar decisión
    is_correct = (selected_option == scenario.correct_option)
    
    # Calcular puntos según rol
    points_earned = scenario.get_points_for_role(user.role)
    if not is_correct:
        points_earned = int(points_earned * 0.2)  # 20% de puntos por intento incorrecto
    
    # Registrar decisión
    decision = UserDecisionMRO(
        user_id=user.id,
        scenario_id=scenario_id,
        selected_option=selected_option,
        is_correct=is_correct,
        points_earned=points_earned,
        time_taken=time_taken,
        user_role_at_time=user.role
    )
    
    # Actualizar estadísticas del usuario
    user.mro_scenarios_completed += 1
    if is_correct:
        user.mro_correct_decisions += 1
        user.mro_score += points_earned
    
    # Añadir XP según resultado
    activity_type = 'decision_correct' if is_correct else 'training_completed'
    xp_gained = user.add_mro_xp(points_earned, activity_type)
    
    # Actualizar otras métricas según el escenario
    if scenario.category == 'inventario':
        if is_correct:
            user.inventory_accuracy = min(100, user.inventory_accuracy + 0.5)
    elif scenario.category == 'seguridad':
        if is_correct:
            user.safety_score = min(100, user.safety_score + 2)
        else:
            user.safety_score = max(0, user.safety_score - 5)
    
    db.session.add(decision)
    db.session.commit()
    
    # Preparar respuesta
    feedback = {
        'is_correct': is_correct,
        'points_earned': points_earned,
        'xp_gained': xp_gained,
        'new_level': user.mro_level,
        'total_xp': user.mro_xp,
        'correct_option': scenario.correct_option,
        'feedback': scenario.feedback_correct if is_correct else scenario.feedback_incorrect,
        'analysis': scenario.professional_analysis,
        'sap_procedure': scenario.sap_procedure.split('|') if scenario.sap_procedure else [],
        'key_learning': scenario.key_learning,
        'safety_considerations': scenario.safety_considerations,
        'user_stats': user.to_mro_dict()
    }
    
    return jsonify(feedback)


@simulator_mro_bp.route('/api/stats')
@login_required
def get_user_stats():
    """Obtiene estadísticas del usuario en el simulador"""
    user = User.query.get(current_user.id)
    
    # Calcular efectividad por categoría
    decisions = UserDecisionMRO.query.filter_by(user_id=user.id).all()
    
    category_stats = {}
    for decision in decisions:
        if decision.scenario:
            category = decision.scenario.category
            if category not in category_stats:
                category_stats[category] = {'total': 0, 'correct': 0}
            
            category_stats[category]['total'] += 1
            if decision.is_correct:
                category_stats[category]['correct'] += 1
    
    # Calcular porcentajes
    for category, stats in category_stats.items():
        stats['accuracy'] = round((stats['correct'] / stats['total']) * 100, 1) if stats['total'] > 0 else 0
    
    return jsonify({
        'user': user.to_mro_dict(),
        'category_stats': category_stats,
        'overall_accuracy': user.get_mro_effectiveness(),
        'performance': user.get_mro_performance()
    })


@simulator_mro_bp.route('/api/leaderboard')
def get_leaderboard():
    """Tabla de clasificación por roles"""
    role = request.args.get('role', 'all')
    limit = int(request.args.get('limit', 20))
    
    leaderboard_data = get_leaderboard_for_role(role, limit)
    
    return jsonify({
        'leaderboard': leaderboard_data,
        'role_filter': role
    })


# ============================================
# FUNCIONES AUXILIARES
# ============================================

def get_leaderboard_for_role(role, limit=20):
    """Obtiene la tabla de clasificación para un rol específico"""
    if role == 'all':
        users = User.query.filter(
            User.role.in_(['aprendiz', 'tecnico_almacen', 'planificador'])
        ).order_by(User.mro_score.desc()).limit(limit).all()
    else:
        users = User.query.filter_by(role=role).order_by(User.mro_score.desc()).limit(limit).all()
    
    leaderboard = []
    for i, user in enumerate(users, 1):
        leaderboard.append({
            'rank': i,
            'username': user.username,
            'role': user.get_role_display_name(),
            'level': user.mro_level,
            'score': user.mro_score,
            'scenarios_completed': user.mro_scenarios_completed,
            'accuracy': user.get_mro_effectiveness(),
            'department': user.department,
            'xp': user.mro_xp
        })
    
    return leaderboard
