# models/__init__.py
from flask_sqlalchemy import SQLAlchemy

# Crear instancia global de SQLAlchemy
db = SQLAlchemy()

# ======================================================
# IMPORTAR TODOS LOS MODELOS PARA QUE SQLAlchemy LOS REGISTRE
# ======================================================

# Modelos existentes (basados en tus archivos)
from .user import User
from .inventory import InventoryItem
from .bulios import Bulto  # Archivo: bulios.py
from .post_registro import PostRegistro
from .alerts import Alert
from .alertas_ai import AlertaIA
from .technician_error import TechnicianError
from .equipos import Equipo
from .productivitydad import Productividad  # Archivo: productivitydad.py
from .auditoria import Auditoria
from .inventory_history import InventoryHistory
from .warehouse2d import WarehouseLocation
from .inventory_count import InventoryCount
from .task import Task
from .score import Score
from .scenario_mro import ScenarioMRO, UserDecisionMRO

# Modelos adicionales que tienes pero no están en las importaciones originales
from .analisis_oc import AnalisisOC  # Si existe este modelo
from .turnos import Turno  # Si existe este modelo

# NOTA: NO importar 'activated' porque no existe ese archivo
# El archivo 'activated.py' existe pero puede que no tenga un modelo llamado 'Activated'
# Si necesitas importarlo, primero verifica qué contiene ese archivo
