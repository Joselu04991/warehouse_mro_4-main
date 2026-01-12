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

    # 🏭 ROLES ESPECÍFICOS PARA ALMACÉN MRO
    role = db.Column(db.String(30), default="aprendiz")  
    # Valores posibles: 'aprendiz', 'tecnico_almacen', 'planificador', 'supervisor', 'admin'
    
    # 🔧 Campos adicionales para almacén MRO
    employee_id = db.Column(db.String(20), unique=True, nullable=True)  # Ej: MRO-001
    department = db.Column(db.String(100), default="Almacén MRO")  
    shift = db.Column(db.String(10), default="A")  # Turno A, B, C
    specialization = db.Column(db.String(100), nullable=True)  # Ej: 'Herramientas', 'Repuestos Críticos'
    
    status = db.Column(db.String(20), default="active")
    
    # 📊 SISTEMA DE PUNTAJE MEJORADO PARA MRO
    score = db.Column(db.Integer, default=20)
    score_year = db.Column(db.Integer, default=date.today().year)
    
    # 🎯 PUNTOS ESPECÍFICOS PARA SIMULADOR
    simulator_score = db.Column(db.Integer, default=0)
    scenarios_completed = db.Column(db.Integer, default=0)
    correct_decisions = db.Column(db.Integer, default=0)
    
    # 📈 NIVELES Y PROGRESIÓN
    mro_level = db.Column(db.String(50), default='Aprendiz Nivel 1')
    xp_points = db.Column(db.Integer, default=0)
    
    # 📊 MÉTRICAS DE DESEMPEÑO
    inventory_accuracy = db.Column(db.Float, default=0.0)  # % exactitud en inventarios
    order_fulfillment_rate = db.Column(db.Float, default=0.0)  # % órdenes cumplidas a tiempo
    safety_score = db.Column(db.Integer, default=100)  # Puntaje de seguridad (100 = perfecto)
    sap_proficiency = db.Column(db.Float, default=0.0)  # % dominio de transacciones SAP
    
    # 🔐 CAMPOS EXISTENTES
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
    # decisions = db.relationship('UserDecision', backref='user', lazy=True)
    # inventory_counts = db.relationship('InventoryCount', backref='user', lazy=True)

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
        elif self.role == 'supervisor':
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
                'sap_transactions': ['Todas las transacciones'],
                'can_manage_users': True,
                'can_override_all': True
            }
        else:  # admin/user por defecto
            return {
                'can_scan_items': False,
                'can_view_inventory': True,
                'can_create_orders': False,
                'can_approve_orders': False,
                'can_adjust_stock': False,
                'can_generate_reports': True
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
            if self.xp_points >= xp_required:
                current_level = level_name
                break
        
        self.mro_level = current_level
        return current_level
    
    def add_xp(self, points, activity_type):
        """Añade puntos de experiencia según la actividad realizada"""
        # Multiplicadores según tipo de actividad
        multipliers = {
            'decision_correct': 1.5,      # Decisión correcta en simulador
            'inventory_accurate': 1.2,    # Conteo preciso
            'order_completed': 1.3,       # Orden completada a tiempo
            'safety_compliant': 1.1,      # Cumplimiento de seguridad
            'training_completed': 2.0,    # Completó entrenamiento
            'problem_solved': 1.8,        # Resolvió problema complejo
            'sap_transaction': 1.4        # Uso correcto de SAP
        }
        
        multiplier = multipliers.get(activity_type, 1.0)
        
        # Rol bonus
        role_bonus = {
            'aprendiz': 1.5,      # Aprendices ganan más XP
            'tecnico_almacen': 1.2,
            'planificador': 1.0,
            'supervisor': 0.8,
            'admin': 0.5
        }
        
        role_multiplier = role_bonus.get(self.role, 1.0)
        
        total_xp = int(points * multiplier * role_multiplier)
        self.xp_points += total_xp
        
        # Actualizar nivel
        self.calculate_mro_level()
        
        return total_xp
    
    def get_simulator_effectiveness(self):
        """Calcula la efectividad en el simulador"""
        if self.scenarios_completed == 0:
            return 0
        return (self.correct_decisions / self.scenarios_completed) * 100
    
    def get_overall_performance(self):
        """Calcula el desempeño general"""
        weights = {
            'inventory_accuracy': 0.3,
            'order_fulfillment_rate': 0.3,
            'safety_score': 0.2,
            'simulator_effectiveness': 0.2
        }
        
        simulator_effectiveness = self.get_simulator_effectiveness()
        
        performance = (
            (self.inventory_accuracy * weights['inventory_accuracy']) +
            (self.order_fulfillment_rate * weights['order_fulfillment_rate']) +
            ((self.safety_score / 100) * weights['safety_score']) +
            ((simulator_effectiveness / 100) * weights['simulator_effectiveness'])
        ) * 100
        
        return round(performance, 1)
    
    def to_dict(self, include_sensitive=False):
        """Convierte el usuario a diccionario para JSON"""
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'role_display': self.get_role_display_name(),
            'employee_id': self.employee_id,
            'department': self.department,
            'shift': self.shift,
            'mro_level': self.mro_level,
            'xp_points': self.xp_points,
            'score': self.score,
            'simulator_score': self.simulator_score,
            'scenarios_completed': self.scenarios_completed,
            'correct_decisions': self.correct_decisions,
            'performance': self.get_overall_performance(),
            'inventory_accuracy': self.inventory_accuracy,
            'order_fulfillment_rate': self.order_fulfillment_rate,
            'safety_score': self.safety_score,
            'sap_proficiency': self.sap_proficiency,
            'permissions': self.get_role_permissions()
        }
        
        if include_sensitive:
            data['last_login'] = self.last_login.isoformat() if self.last_login else None
            data['created_at'] = self.created_at.isoformat() if self.created_at else None
        
        return data
