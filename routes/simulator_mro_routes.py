# routes/simulator_mro_routes.py
from flask import Blueprint, render_template
from flask_login import login_required, current_user

simulator_mro_bp = Blueprint('simulator_mro', __name__, url_prefix='/mro-simulator')

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
def create_scenario():
    # Solo roles específicos pueden crear escenarios
    if current_user.role not in ['planificador', 'supervisor', 'admin', 'owner']:
        from flask import abort
        abort(403)
    return render_template('simulator_mro/create_scenario.html')

# NO añadas más rutas por ahora
