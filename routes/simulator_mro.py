# routes/simulator_mro.py
from flask import Blueprint, jsonify, request, session, render_template
from flask_login import login_required, current_user
from models import db
from models.user import User
from models.scenario_mro import ScenarioMRO, UserDecision
import random
from datetime import datetime

simulator_mro_bp = Blueprint('simulator_mro', __name__)

@simulator_mro_bp.route('/mro-simulator')
@login_required
def simulator_dashboard():
    """Dashboard principal del simulador MRO"""
    user = User.query.get(current_user.id)
    
    # Obtener estadísticas del usuario
    user_stats = user.to_dict()
    
    # Obtener escenarios accesibles para su rol
    accessible_scenarios = ScenarioMRO.query.filter(
        ScenarioMRO.is_active == True
    ).all()
    
    # Filtrar por rol
    accessible_scenarios = [
        s for s in accessible_scenarios 
        if s.is_accessible_for(user.role)
    ]
    
    # Obtener historial de decisiones recientes
    recent_decisions = UserDecision.query.filter_by(
        user_id=user.id
    ).order_by(UserDecision.decision_time.desc()).limit(5).all()
    
    return render_template('simulator_mro/dashboard.html',
                         user=user_stats,
                         scenarios=accessible_scenarios,
                         recent_decisions=recent_decisions)


@simulator_mro_bp.route('/api/mro-simulator/scenario', methods=['GET'])
@login_required
def get_scenario():
    """Obtiene un escenario aleatorio adecuado para el rol del usuario"""
    user = User.query.get(current_user.id)
    
    # Filtrar escenarios por rol y dificultad progresiva
    base_query = ScenarioMRO.query.filter_by(is_active=True)
    
    # Ajustar dificultad según nivel del usuario
    if user.xp_points < 500:
        difficulty_filter = [1, 2]  # Básico/Fácil para aprendices
    elif user.xp_points < 2000:
        difficulty_filter = [1, 2, 3]  # Incluye intermedio
    else:
        difficulty_filter = [2, 3, 4]  # Más difícil para avanzados
    
    # Obtener escenarios accesibles
    all_scenarios = base_query.filter(
        ScenarioMRO.difficulty.in_(difficulty_filter)
    ).all()
    
    # Filtrar por rol
    accessible_scenarios = [
        s for s in all_scenarios 
        if s.is_accessible_for(user.role)
    ]
    
    if not accessible_scenarios:
        return jsonify({'error': 'No hay escenarios disponibles para tu rol'}), 404
    
    # Seleccionar escenario (ponderado por dificultad)
    weights = [6 - s.difficulty for s in accessible_scenarios]  # Más peso a menor dificultad
    selected_scenario = random.choices(accessible_scenarios, weights=weights, k=1)[0]
    
    return jsonify(selected_scenario.to_dict())


@simulator_mro_bp.route('/api/mro-simulator/evaluate', methods=['POST'])
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
    decision = UserDecision(
        user_id=user.id,
        scenario_id=scenario_id,
        selected_option=selected_option,
        is_correct=is_correct,
        points_earned=points_earned,
        time_taken=time_taken,
        user_role_at_time=user.role
    )
    
    # Actualizar estadísticas del usuario
    user.scenarios_completed += 1
    if is_correct:
        user.correct_decisions += 1
        user.simulator_score += points_earned
    
    # Añadir XP según resultado
    activity_type = 'decision_correct' if is_correct else 'training_completed'
    xp_gained = user.add_xp(points_earned, activity_type)
    
    db.session.add(decision)
    db.session.commit()
    
    # Preparar respuesta
    feedback = {
        'is_correct': is_correct,
        'points_earned': points_earned,
        'xp_gained': xp_gained,
        'new_level': user.mro_level,
        'total_xp': user.xp_points,
        'correct_option': scenario.correct_option,
        'feedback': scenario.feedback_correct if is_correct else scenario.feedback_incorrect,
        'analysis': scenario.professional_analysis,
        'sap_procedure': scenario.sap_procedure.split('|') if scenario.sap_procedure else [],
        'key_learning': scenario.key_learning,
        'safety_considerations': scenario.safety_considerations,
        'user_stats': {
            'score': user.simulator_score,
            'completed': user.scenarios_completed,
            'accuracy': user.get_simulator_effectiveness(),
            'level': user.mro_level,
            'xp': user.xp_points
        }
    }
    
    return jsonify(feedback)


@simulator_mro_bp.route('/api/mro-simulator/stats', methods=['GET'])
@login_required
def get_user_stats():
    """Obtiene estadísticas del usuario en el simulador"""
    user = User.query.get(current_user.id)
    
    # Calcular efectividad por categoría
    decisions = UserDecision.query.filter_by(user_id=user.id).all()
    
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
        'user': user.to_dict(),
        'category_stats': category_stats,
        'overall_accuracy': user.get_simulator_effectiveness(),
        'performance': user.get_overall_performance()
    })


@simulator_mro_bp.route('/api/mro-simulator/leaderboard', methods=['GET'])
def get_leaderboard():
    """Tabla de clasificación por roles"""
    role = request.args.get('role', 'all')
    
    if role == 'all':
        users = User.query.filter(
            User.role.in_(['aprendiz', 'tecnico_almacen', 'planificador'])
        ).order_by(User.simulator_score.desc()).limit(20).all()
    else:
        users = User.query.filter_by(role=role).order_by(User.simulator_score.desc()).limit(20).all()
    
    leaderboard = []
    for i, user in enumerate(users, 1):
        leaderboard.append({
            'rank': i,
            'username': user.username,
            'role': user.get_role_display_name(),
            'level': user.mro_level,
            'score': user.simulator_score,
            'scenarios_completed': user.scenarios_completed,
            'accuracy': user.get_simulator_effectiveness(),
            'department': user.department
        })
    
    return jsonify({'leaderboard': leaderboard, 'role_filter': role})
