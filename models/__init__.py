# models/__init__.py
from flask_sqlalchemy import SQLAlchemy

# Crear instancia global de SQLAlchemy
db = SQLAlchemy()

# ======================================================
# IMPORTAR TODOS LOS MODELOS PARA QUE SQLAlchemy LOS REGISTRE
# ======================================================

# Modelos de usuarios y autenticación
from .user import User
from .activated import Activated  # Si este modelo existe

# Modelos de inventario y almacén
from .inventory import InventoryItem
from .inventory_history import InventoryHistory
from .inventory_count import InventoryCount
from .warehouse2d import WarehouseLocation
from .bulios import Bulto  # Archivo: bulios.py

# Modelos de equipos y operaciones
from .equipos import Equipo
from .post_registro import PostRegistro
from .productivitydad import Productividad  # Archivo: productivitydad.py

# Modelos de alertas y auditoría
from .alerts import Alert
from .alertas_ai import AlertaIA
from .technician_error import TechnicianError
from .auditoria import Auditoria

# Modelos de tareas y productividad
from .task import Task
from .score import Score

# Modelos MRO (Maintenance, Repair and Operations)
from .scenario_mro import ScenarioMRO, UserDecisionMRO

# Modelos adicionales (si existen)
from .analisis_oc import AnalisisOC  # Si el modelo existe
from .turnos import Turno  # Si el modelo existe
