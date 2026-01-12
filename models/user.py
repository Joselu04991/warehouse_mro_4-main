# models/user.py
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

    # 🏭 ROLES ESPECÍFICOS PARA ALMACÉN MRO (actualizar valores existentes)
    role = db.Column(db.String(30), default="aprendiz")  
    # Valores: 'aprendiz', 'tecnico_almacen', 'planificador', 'supervisor', 'admin'
    
    # 🔧 Campos adicionales para almacén MRO
    employee_id = db.Column(db.String(20), unique=True, nullable=True)  # Ej: MRO-001
    department = db.Column(db.String(100), default="Almacén MRO")  
    shift = db.Column(db.String(10), default="A")  # Turno A, B, C
    specialization = db.Column(db.String(100), nullable=True)  # Ej: 'Herramientas', 'Repuestos Críticos'
    
    status = db.Column(db.String(20), default="active")
    
    # 📊 SISTEMA DE PUNTAJE MEJORADO PARA MRO
    score = db.Column(db.Integer, default=20)
    score_year = db.Column(db.Integer, default=date.today().year)
    
    # 🎯 PUNTOS ESPECÍFICOS PARA SIMULADOR MRO
    mro_score = db.Column(db.Integer, default=0)
    mro_scenarios_completed = db.Column(db.Integer, default=0)
    mro_correct_decisions = db.Column(db.Integer, default=0)
    
    # 📈 NIVELES Y PROGRESIÓN MRO
    mro_level = db.Column(db.String(50), default='Aprendiz Nivel 1')
    mro_xp = db.Column(db.Integer, default=0)
    
    # 📊 MÉTRICAS DE DESEMPEÑO MRO
    inventory_accuracy = db.Column(db.Float, default=0.0)  # % exactitud en inventarios
    order_fulfillment_rate = db.Column(db.Float, default=0.0)  # % órdenes cumplidas a tiempo
    safety_score = db.Column(db.Integer, default=100)  # Puntaje de seguridad (100 = perfecto)
    sap_proficiency = db.Column(db.Float, default=0.0)  # % dominio de transacciones SAP
    
    # 🔐 CAMPOS EXISTENTES (mantener)
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

    # 🔗 Relaciones (si las tienes definidas)
    # mro_decisions ya está definida por backref en UserDecisionMRO

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    # 🏭 MÉTODOS ESPECÍFICOS PARA MRO
    
    def get_role_display_name(self):
        """Devuelve el nombre legible del rol"""
        role_names = {
            'aprendiz': 'Aprendiz de Almacén',
            'tecnico_almacen': 'Técnico de Almacén MRO',
            'planificador': 'Planificador de Materiales',
            'supervisor': 'Supervisor de Almacén',
            'admin': 'Administrador del Sistema'
        }
        return role_names.get(self.role, self.role.title())
    
    def get_role_permissions(self):
        """Define permisos específicos según el rol en almacén MRO"""
        if self.role == 'aprendiz':
            return {
                'can_scan_items': True,
                'can_view_inventory': True,
                'can_create_orders': False,
                'can_approve_orders': False,
                'can_adjust_stock': False,
                'can_generate_reports': False,
                'max_items_per_order': 5,
                'require_approval': True,
                'allowed_zones': ['Zona A', 'Zona B'],
                'sap_transactions': ['MIGO', 'MB51']
            }
        elif self.role == 'tecnico_almacen':
            return {
                'can_scan_items': True,
                'can_view_inventory': True,
                'can_create_orders': True,
                'can_approve_orders': False,
                'can_adjust_stock': True,
                'can_generate_reports': True,
                'max_items_per_order': 20,
                'require_approval': False,
                'allowed_zones': ['Zona A', 'Zona B', 'Zona C', 'Zona Crítica'],
                'sap_transactions': ['MIGO', 'MB51', 'MB1A', 'MI04']
            }
        elif self.role == 'planificador':
            return {
                'can_scan_items': True,
                'can_view_inventory': True,
                'can_create_orders': True,
                'can_approve_orders': True,
                'can_adjust_stock': True,
                'can_generate_reports': True,
                'max_items_per_order': 100,
                'require_approval': False,
                'allowed_zones': ['Todas las zonas'],
                'sap_transactions': ['Todas las transacciones'],
                'can_manage_suppliers': True,
                'can_set_reorder_points': True
            }
        else:  # supervisor/admin
            return {
                'can_scan_items': True,
                'can_view_inventory': True,
                'can_create_orders': True,
                'can_approve_orders': True,
                'can_adjust_stock': True,
                'can_generate_reports': True,
                'max_items_per_order': 500,
                'require_approval': False,
                'allowed_zones': ['Todas las zonas'],
                'sap_transactions': ['Todas las transacciones']
            }
    
    def calculate_mro_level(self):
        """Calcula el nivel MRO basado en XP y rol"""
        if self.role == 'aprendiz':
            levels = [
                (0, 'Aprendiz Nivel 1'),
                (500, 'Aprendiz Nivel 2'),
                (1000, 'Aprendiz Nivel 3'),
                (2000, 'Aprendiz Avanzado'),
                (3500, 'Promoción a Técnico')
            ]
        elif self.role == 'tecnico_almacen':
            levels = [
                (0, 'Técnico Nivel 1'),
                (1000, 'Técnico Nivel 2'),
                (2500, 'Técnico Nivel 3'),
                (5000, 'Técnico Senior'),
                (8000, 'Especialista MRO')
            ]
        elif self.role == 'planificador':
            levels = [
                (0, 'Planificador Nivel 1'),
                (1500, 'Planificador Nivel 2'),
                (3500, 'Planificador Nivel 3'),
                (7000, 'Planificador Senior'),
                (10000, 'Planificador Master')
            ]
        else:
            levels = [(0, self.role.title())]
        
        # Encontrar el nivel actual basado en XP
        current_level = levels[0][1]
        for xp_required, level_name in reversed(levels):
            if self.mro_xp >= xp_required:
                current_level = level_name
                break
        
        self.mro_level = current_level
        return current_level
    
    def add_mro_xp(self, points, activity_type):
        """Añade puntos de experiencia MRO según la actividad realizada"""
        # Multiplicadores según tipo de actividad
        multipliers = {
            'decision_correct': 1.5,
            'inventory_accurate': 1.2,
            'order_completed': 1.3,
            'safety_compliant': 1.1,
            'training_completed': 2.0,
            'problem_solved': 1.8,
            'sap_transaction': 1.4
        }
        
        multiplier = multipliers.get(activity_type, 1.0)
        
        # Rol bonus
        role_bonus = {
            'aprendiz': 1.5,
            'tecnico_almacen': 1.2,
            'planificador': 1.0,
            'supervisor': 0.8,
            'admin': 0.5
        }
        
        role_multiplier = role_bonus.get(self.role, 1.0)
        
        total_xp = int(points * multiplier * role_multiplier)
        self.mro_xp += total_xp
        
        # Actualizar nivel
        self.calculate_mro_level()
        
        return total_xp
    
    def get_mro_effectiveness(self):
        """Calcula la efectividad en el simulador MRO"""
        if self.mro_scenarios_completed == 0:
            return 0
        return (self.mro_correct_decisions / self.mro_scenarios_completed) * 100
    
    def get_mro_performance(self):
        """Calcula el desempeño general MRO"""
        mro_effectiveness = self.get_mro_effectiveness()
        
        performance = (
            (self.inventory_accuracy * 0.3) +
            (self.order_fulfillment_rate * 0.3) +
            ((self.safety_score / 100) * 0.2) +
            ((mro_effectiveness / 100) * 0.2)
        ) * 100
        
        return round(performance, 1)
    
    def to_mro_dict(self):
        """Convierte el usuario a diccionario para JSON (solo datos MRO)"""
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'role_display': self.get_role_display_name(),
            'employee_id': self.employee_id,
            'department': self.department,
            'shift': self.shift,
            'mro_level': self.mro_level,
            'mro_xp': self.mro_xp,
            'mro_score': self.mro_score,
            'mro_scenarios_completed': self.mro_scenarios_completed,
            'mro_correct_decisions': self.mro_correct_decisions,
            'mro_effectiveness': self.get_mro_effectiveness(),
            'mro_performance': self.get_mro_performance(),
            'inventory_accuracy': self.inventory_accuracy,
            'order_fulfillment_rate': self.order_fulfillment_rate,
            'safety_score': self.safety_score,
            'sap_proficiency': self.sap_proficiency,
            'permissions': self.get_role_permissions()
        }
