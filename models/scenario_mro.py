# models/scenario_mro.py
from datetime import datetime
from models import db

class ScenarioMRO(db.Model):
    """Escenarios de entrenamiento para almacén MRO"""
    __tablename__ = "scenarios_mro"
    
    id = db.Column(db.Integer, primary_key=True)
    scenario_code = db.Column(db.String(20), unique=True, nullable=False)  # SCEN-MRO-001
    
    # Información básica
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    
    # Roles objetivo
    target_roles = db.Column(db.String(200), default='aprendiz,tecnico_almacen,planificador')
    difficulty = db.Column(db.Integer, default=1)
    estimated_time = db.Column(db.Integer, default=300)
    
    # Contexto específico
    warehouse_zone = db.Column(db.String(50))
    material_type = db.Column(db.String(50))
    criticality = db.Column(db.String(20))
    
    # Datos SAP
    sap_transaction = db.Column(db.String(20))
    sap_data_json = db.Column(db.JSON, default=dict)
    
    # Opciones de decisión
    option_a = db.Column(db.Text, nullable=False)
    option_b = db.Column(db.Text, nullable=False)
    option_c = db.Column(db.Text, nullable=False)
    correct_option = db.Column(db.String(1), nullable=False)
    
    # Puntos por rol
    points_aprendiz = db.Column(db.Integer, default=100)
    points_tecnico = db.Column(db.Integer, default=80)
    points_planificador = db.Column(db.Integer, default=60)
    points_supervisor = db.Column(db.Integer, default=40)
    
    # Feedback educativo
    feedback_correct = db.Column(db.Text)
    feedback_incorrect = db.Column(db.Text)
    professional_analysis = db.Column(db.Text)
    sap_procedure = db.Column(db.Text)
    safety_considerations = db.Column(db.Text)
    key_learning = db.Column(db.Text)
    
    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # 🔥 CORREGIR LA RELACIÓN - Usar strings para evitar importación circular
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_scenarios')
    
    def to_dict(self):
        """Convierte a diccionario para JSON"""
        return {
            'id': self.id,
            'code': self.scenario_code,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'target_roles': self.target_roles.split(','),
            'difficulty': self.difficulty,
            'estimated_time': self.estimated_time,
            'warehouse_zone': self.warehouse_zone,
            'material_type': self.material_type,
            'criticality': self.criticality,
            'sap_transaction': self.sap_transaction,
            'sap_data': self.sap_data_json or {},
            'options': {
                'A': self.option_a,
                'B': self.option_b,
                'C': self.option_c
            },
            'correct_option': self.correct_option,
            'points': {
                'aprendiz': self.points_aprendiz,
                'tecnico': self.points_tecnico,
                'planificador': self.points_planificador
            },
            'educational': {
                'analysis': self.professional_analysis,
                'sap_procedure': self.sap_procedure.split('|') if self.sap_procedure else [],
                'safety': self.safety_considerations,
                'key_learning': self.key_learning
            },
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active
        }


class UserDecisionMRO(db.Model):
    """Decisiones tomadas por usuarios en el simulador MRO"""
    __tablename__ = "user_decisions_mro"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    scenario_id = db.Column(db.Integer, db.ForeignKey('scenarios_mro.id'), nullable=False)
    
    # Decisión
    selected_option = db.Column(db.String(1), nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False)
    points_earned = db.Column(db.Integer, default=0)
    
    # Tiempo
    time_taken = db.Column(db.Integer)
    user_role_at_time = db.Column(db.String(30))
    
    # Metadata
    decision_time = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 🔥 CORREGIR RELACIONES - Usar strings y lazy='joined' para mejor rendimiento
    user = db.relationship('User', foreign_keys=[user_id], backref='mro_decisions', lazy='joined')
    scenario = db.relationship('ScenarioMRO', foreign_keys=[scenario_id], backref='decisions', lazy='joined')
    
    def to_dict(self):
        return {
            'id': self.id,
            'scenario_title': self.scenario.title if self.scenario else None,
            'selected_option': self.selected_option,
            'is_correct': self.is_correct,
            'points_earned': self.points_earned,
            'time_taken': self.time_taken,
            'decision_time': self.decision_time.isoformat() if self.decision_time else None
        }
