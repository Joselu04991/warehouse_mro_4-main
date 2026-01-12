# models/__init__.py
from flask_sqlalchemy import SQLAlchemy

# Crear instancia global de SQLAlchemy
db = SQLAlchemy()

# ======================================================
# IMPORTAR TODOS LOS MODELOS PARA QUE SQLAlchemy LOS REGISTRE
# ======================================================

# Solo importar los modelos que SABEMOS que existen
from .user import User
from .inventory import InventoryItem
from .bultos import Bulto  # ¡IMPORTANTE! Archivo es 'bultos.py'
from .post_registro import PostRegistro
from .alerts import Alert
from .alertas_ai import AlertaIA
from .technician_error import TechnicianError
from .equipos import Equipo
from .auditoria import Auditoria
from .inventory_history import InventoryHistory
from .warehouse2d import WarehouseLocation
from .inventory_count import InventoryCount
from .task import Task
from .score import Score
from .scenario_mro import ScenarioMRO, UserDecisionMRO

# Importar productividad si existe (el archivo se llama 'productivitydad.py')
try:
    from .productivitydad import Productividad
    print("✅ Productividad importado correctamente")
except ImportError as e:
    print(f"⚠️  No se pudo importar Productividad: {e}")
    # Puedes definir un modelo vacío o manejarlo de otra forma
    class Productividad:
        pass
