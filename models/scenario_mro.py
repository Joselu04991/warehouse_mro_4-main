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
    category = db.Column(db.String(50), nullable=False)  # inventario, seguridad, sap, calidad, emergencia
    
    # Roles objetivo (puede tener múltiples separados por coma)
    target_roles = db.Column(db.String(200), default='aprendiz,tecnico_almacen,planificador')
    difficulty = db.Column(db.Integer, default=1)  # 1-5
    estimated_time = db.Column(db.Integer, default=300)  # segundos
    
    # Contexto específico de almacén
    warehouse_zone = db.Column(db.String(50))  # Zona A, Zona Crítica, etc.
    material_type = db.Column(db.String(50))  # Herramienta, Repuesto, Consumible
    criticality = db.Column(db.String(20))  # alto, medio, bajo
    
    # Datos de simulación SAP
    sap_transaction = db.Column(db.String(20))  # MIGO, MB1A, MI04, etc.
    sap_data_json = db.Column(db.JSON, default=dict)  # Datos flexibles en JSON
    
    # Opciones de decisión
    option_a = db.Column(db.Text, nullable=False)
    option_b = db.Column(db.Text, nullable=False)
    option_c = db.Column(db.Text, nullable=False)
    correct_option = db.Column(db.String(1), nullable=False)  # A, B, o C
    
    # Puntos por rol (diferentes valores según experiencia)
    points_aprendiz = db.Column(db.Integer, default=100)
    points_tecnico = db.Column(db.Integer, default=80)
    points_planificador = db.Column(db.Integer, default=60)
    points_supervisor = db.Column(db.Integer, default=40)
    
    # Feedback educativo
    feedback_correct = db.Column(db.Text)
    feedback_incorrect = db.Column(db.Text)
    professional_analysis = db.Column(db.Text)
    sap_procedure = db.Column(db.Text)  # Pasos en SAP separados por |
    safety_considerations = db.Column(db.Text)
    key_learning = db.Column(db.Text)
    
    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Métodos
    def get_points_for_role(self, role):
        """Devuelve puntos según el rol del usuario"""
        points_map = {
            'aprendiz': self.points_aprendiz,
            'tecnico_almacen': self.points_tecnico,
            'planificador': self.points_planificador,
            'supervisor': self.points_supervisor,
            'admin': 0
        }
        return points_map.get(role, self.points_aprendiz)
    
    def is_accessible_for(self, role):
        """Verifica si el escenario es accesible para un rol"""
        roles = [r.strip() for r in self.target_roles.split(',')]
        return role in roles or 'all' in roles
    
    def get_difficulty_label(self):
        """Etiqueta legible de dificultad"""
        labels = {
            1: 'Básico',
            2: 'Fácil',
            3: 'Intermedio',
            4: 'Difícil',
            5: 'Avanzado'
        }
        return labels.get(self.difficulty, 'Básico')
    
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
            'difficulty_label': self.get_difficulty_label(),
            'estimated_time': self.estimated_time,
            'warehouse_zone': self.warehouse_zone,
            'material_type': self.material_type,
            'criticality': self.criticality,
            'sap_transaction': self.sap_transaction,
            'sap_data': self.sap_data_json,
            'options': {
                'A': self.option_a,
                'B': self.option_b,
                'C': self.option_c
            },
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
    
    # Decisión tomada
    selected_option = db.Column(db.String(1), nullable=False)  # A, B, o C
    is_correct = db.Column(db.Boolean, nullable=False)
    points_earned = db.Column(db.Integer, default=0)
    
    # Tiempo y contexto
    time_taken = db.Column(db.Integer)  # segundos
    user_role_at_time = db.Column(db.String(30))  # rol al momento de la decisión
    
    # Metadata
    decision_time = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    user = db.relationship('User', backref='mro_decisions')
    scenario = db.relationship('ScenarioMRO', backref='decisions')
    
    def to_dict(self):
        return {
            'id': self.id,
            'scenario': self.scenario.title if self.scenario else None,
            'selected_option': self.selected_option,
            'is_correct': self.is_correct,
            'points_earned': self.points_earned,
            'time_taken': self.time_taken,
            'decision_time': self.decision_time.isoformat() if self.decision_time else None
        }
