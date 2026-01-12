# models/scenario.py
from extensions import db
from datetime import datetime

class Scenario(db.Model):
    __tablename__ = 'scenarios'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    sap_data = db.Column(db.String(300)) # Ej: "Material: MX-450 | Stock: 0"
    option_a = db.Column(db.Text, nullable=False)
    option_b = db.Column(db.Text, nullable=False)
    option_c = db.Column(db.Text, nullable=False)
    correct_option = db.Column(db.String(1), nullable=False) # 'A', 'B' o 'C'
    feedback_correct = db.Column(db.Text)
    feedback_incorrect = db.Column(db.Text)
    professional_analysis = db.Column(db.Text)
    sap_procedure = db.Column(db.Text) # Pasos separados por punto y coma
    key_learning = db.Column(db.Text)
    category = db.Column(db.String(50)) # 'Inventario', 'Seguridad', etc.
    time_limit = db.Column(db.Integer) # Tiempo en segundos
    affected_line = db.Column(db.String(50)) # Línea de producción afectada
    difficulty = db.Column(db.Integer, default=1)
    points_correct = db.Column(db.Integer, default=100)
    points_incorrect = db.Column(db.Integer, default=-50)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class UserDecision(db.Model):
    __tablename__ = 'user_decisions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    scenario_id = db.Column(db.Integer, db.ForeignKey('scenarios.id'), nullable=False)
    selected_option = db.Column(db.String(1), nullable=False)
    points_earned = db.Column(db.Integer)
    time_taken = db.Column(db.Integer) # Tiempo que tardó en responder (segundos)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    user = db.relationship('User', backref='decisions')
    scenario = db.relationship('Scenario', backref='decisions')
