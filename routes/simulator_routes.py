# routes/simulator_routes.py
from flask import Blueprint, jsonify, request, session
from models.user import User
from models.scenario import Scenario, UserDecision
from extensions import db
import random

simulator_bp = Blueprint('simulator', __name__)

# Ruta para obtener un escenario aleatorio
@simulator_bp.route('/api/simulator/scenario', methods=['GET'])
def get_scenario():
    scenarios = Scenario.query.all()
    if not scenarios:
        return jsonify({'error': 'No hay escenarios configurados'}), 404
    
    selected_scenario = random.choice(scenarios)
    
    # Datos del escenario para el frontend
    scenario_data = {
        'id': selected_scenario.id,
        'title': selected_scenario.title,
        'description': selected_scenario.description,
        'sap_data': selected_scenario.sap_data,
        'options': {
            'A': selected_scenario.option_a,
            'B': selected_scenario.option_b,
            'C': selected_scenario.option_c
        },
        'category': selected_scenario.category,
        'time_limit': selected_scenario.time_limit,
        'affected_line': selected_scenario.affected_line
    }
    return jsonify(scenario_data)

# Ruta para evaluar una decisión del usuario
@simulator_bp.route('/api/simulator/evaluate', methods=['POST'])
def evaluate_decision():
    data = request.json
    scenario_id = data.get('scenario_id')
    selected_option = data.get('selected_option')
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'Usuario no autenticado'}), 401
    
    scenario = Scenario.query.get(scenario_id)
    if not scenario:
        return jsonify({'error': 'Escenario no encontrado'}), 404
    
    is_correct = (selected_option == scenario.correct_option)
    points_earned = scenario.points_correct if is_correct else scenario.points_incorrect
    
    # Guardar la decisión y actualizar el puntaje del usuario
    new_decision = UserDecision(
        user_id=user_id,
        scenario_id=scenario_id,
        selected_option=selected_option,
        points_earned=points_earned
    )
    db.session.add(new_decision)
    
    user = User.query.get(user_id)
    user.simulator_score += points_earned
    user.scenarios_completed += 1
    db.session.commit()
    
    # Preparar feedback detallado
    feedback = {
        'is_correct': is_correct,
        'points_earned': points_earned,
        'correct_option': scenario.correct_option,
        'feedback_text': scenario.feedback_correct if is_correct else scenario.feedback_incorrect,
        'professional_analysis': scenario.professional_analysis,
        'sap_procedure': scenario.sap_procedure.split(';'), # Suponiendo que se almacena separado por ;
        'key_learning': scenario.key_learning
    }
    
    return jsonify(feedback)
