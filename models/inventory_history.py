from models import db
from datetime import datetime

class InventoryHistory(db.Model):
    __tablename__ = "inventory_history"

    id = db.Column(db.Integer, primary_key=True)

    # Usuario dueño del inventario
    user_id = db.Column(db.Integer, nullable=False, index=True)

    # Snapshot
    snapshot_id = db.Column(db.String(64), nullable=False, index=True)
    snapshot_name = db.Column(db.String(150), nullable=False)

    # Datos del material
    material_code = db.Column(db.String(50), nullable=False, index=True)
    material_text = db.Column(db.String(255), nullable=False)
    base_unit = db.Column(db.String(20), nullable=False)
    location = db.Column(db.String(50), nullable=False, index=True)

    libre_utilizacion = db.Column(db.Float, default=0)

    # Fecha Perú
    creado_en = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Metadata del origen
    source_type = db.Column(db.String(30), default="DIARIO")  
    source_filename = db.Column(db.String(255), nullable=True)

    # Cierre
    closed_by = db.Column(db.String(120), nullable=True)
    closed_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<InventoryHistory {self.snapshot_name} - {self.material_code}>"
