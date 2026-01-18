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
from .document_record import DocumentRecord

# Importar productividad si existe (el archivo se llama 'productivitydad.py')
try:
    from .productivitydad import Productividad
    print("✅ Productividad importado correctamente")
except ImportError as e:
    print(f"⚠️  No se pudo importar Productividad: {e}")
    # Crear un modelo dummy para evitar errores
    class Productividad(db.Model):
        __tablename__ = 'productividad_dummy'
        id = db.Column(db.Integer, primary_key=True)
        # Campos mínimos para que no falle
        fecha = db.Column(db.Date)
        usuario_id = db.Column(db.Integer)

# Si no tienes el archivo simulator_mro_routes.py, crea uno dummy
try:
    from .scenario_mro import ScenarioMRO, UserDecisionMRO
except ImportError:
    print("⚠️  scenario_mro.py no encontrado - creando modelos dummy")
    
    # Crear modelos dummy
    class ScenarioMRO(db.Model):
        __tablename__ = 'scenarios_mro_dummy'
        id = db.Column(db.Integer, primary_key=True)
        nombre = db.Column(db.String(100))
    
    class UserDecisionMRO(db.Model):
        __tablename__ = 'user_decisions_mro_dummy'
        id = db.Column(db.Integer, primary_key=True)
        usuario_id = db.Column(db.Integer)

# Opcional: También corregir el nombre del archivo si prefieres
# Puedes renombrar 'productivitydad.py' a 'productividad.py' y actualizar la importación

