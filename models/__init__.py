from flask_sqlalchemy import SQLAlchemy

# Crear instancia global de SQLAlchemy
db = SQLAlchemy()

# ======================================================
# IMPORTAR TODOS LOS MODELOS PARA QUE SQLAlchemy LOS REGISTRE
# ======================================================

from .user import User
from .inventory import InventoryItem
from .bultos import Bulto
from .post_registro import PostRegistro
from .alerts import Alert
from .alertas_ai import AlertaIA
from .technician_error import TechnicianError
from .equipos import Equipo
from .productividad import Productividad
from .auditoria import Auditoria
from .inventory_history import InventoryHistory
from .warehouse2d import WarehouseLocation
from .actividad import ActividadUsuario
from .inventory_count import InventoryCount

