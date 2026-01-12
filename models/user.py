# models/user.py - AÑADIR ESTOS CAMPOS
from datetime import datetime, date
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from models import db

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    # 🏭 ROLES MRO - ACTUALIZAR ESTOS VALORES
    role = db.Column(db.String(30), default="aprendiz")  
    # Valores: 'aprendiz', 'tecnico_almacen', 'planificador', 'supervisor', 'admin', 'owner', 'user'
    
    # 🔧 Campos MRO (añadir al final, antes de los métodos)
    employee_id = db.Column(db.String(20), unique=True, nullable=True)
    department = db.Column(db.String(100), default="Almacén MRO")  
    shift = db.Column(db.String(10), default="A")
    specialization = db.Column(db.String(100), nullable=True)
    
    # 📊 Campos de puntuación MRO
    mro_score = db.Column(db.Integer, default=0)
    mro_scenarios_completed = db.Column(db.Integer, default=0)
    mro_correct_decisions = db.Column(db.Integer, default=0)
    
    # 📈 Progresión MRO
    mro_level = db.Column(db.String(50), default='Aprendiz Nivel 1')
    mro_xp = db.Column(db.Integer, default=0)
    
    # 📊 Métricas de desempeño
    inventory_accuracy = db.Column(db.Float, default=0.0)
    order_fulfillment_rate = db.Column(db.Float, default=0.0)
    safety_score = db.Column(db.Integer, default=100)
    sap_proficiency = db.Column(db.Float, default=0.0)
    
    # 🔐 Campos existentes (mantener igual)
    status = db.Column(db.String(20), default="active")
    email_confirmed = db.Column(db.Boolean, default=True)
    email_token = db.Column(db.String(255), nullable=True)
    twofa_secret = db.Column(db.String(50), nullable=True)
    twofa_enabled = db.Column(db.Boolean, default=False)
    failed_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    last_login = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    phone = db.Column(db.String(20), nullable=True)
    location = db.Column(db.String(100), nullable=True)
    area = db.Column(db.String(100), nullable=True)
    photo = db.Column(db.String(255), nullable=True)
    theme = db.Column(db.String(20), default="light")
    perfil_completado = db.Column(db.Boolean, default=False)

    # 📊 Sistema de puntuación existente
    score = db.Column(db.Integer, default=20)
    score_year = db.Column(db.Integer, default=date.today().year)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    # 🏭 MÉTODOS MRO NUEVOS (añadir al final)
    
    def get_role_display_name(self):
        """Devuelve el nombre legible del rol"""
        role_names = {
            'aprendiz': 'Aprendiz de Almacén',
            'tecnico_almacen': 'Técnico de Almacén',
            'planificador': 'Planificador MRO',
            'supervisor': 'Supervisor de Almacén',
            'admin': 'Administrador',
            'owner': 'Propietario',
            'user': 'Usuario'
        }
        return role_names.get(self.role, self.role)
    
    def get_mro_effectiveness(self):
        """Calcula la efectividad en el simulador MRO"""
        if self.mro_scenarios_completed == 0:
            return 0
        return round((self.mro_correct_decisions / self.mro_scenarios_completed) * 100, 1)
    
    def calculate_mro_level(self):
        """Calcula el nivel MRO basado en XP"""
        if self.role == 'aprendiz':
            levels = [(0, 'Aprendiz N1'), (500, 'Aprendiz N2'), (1000, 'Aprendiz N3')]
        elif self.role == 'tecnico_almacen':
            levels = [(0, 'Técnico N1'), (1000, 'Técnico N2'), (2500, 'Técnico Senior')]
        elif self.role == 'planificador':
            levels = [(0, 'Planificador N1'), (1500, 'Planificador N2'), (3500, 'Planificador Senior')]
        else:
            levels = [(0, self.role)]
        
        current_level = levels[0][1]
        for xp_required, level_name in reversed(levels):
            if self.mro_xp >= xp_required:
                current_level = level_name
                break
        
        self.mro_level = current_level
        return current_level
    
    def to_mro_dict(self):
        """Convierte a diccionario para MRO"""
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'role_display': self.get_role_display_name(),
            'employee_id': self.employee_id,
            'department': self.department,
            'mro_level': self.mro_level,
            'mro_xp': self.mro_xp,
            'mro_score': self.mro_score,
            'mro_scenarios_completed': self.mro_scenarios_completed,
            'mro_correct_decisions': self.mro_correct_decisions,
            'mro_effectiveness': self.get_mro_effectiveness()
        }
