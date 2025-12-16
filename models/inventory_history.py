from models import db
from datetime import datetime


class InventoryHistory(db.Model):
    __tablename__ = "inventory_history"

    id = db.Column(db.Integer, primary_key=True)

    # Identificador del grupo (snapshot)
    snapshot_id = db.Column(db.String(64), nullable=False, index=True)

    # Nombre visible
    snapshot_name = db.Column(db.String(150), nullable=False)

    # Tipo de inventario
    tipo = db.Column(
        db.String(20),
        default="HISTORICO"
    )  # DIARIO | HISTORICO

    # Usuario que lo subió
    uploaded_by = db.Column(db.Integer, nullable=True)

    # Datos del material
    material_code = db.Column(db.String(50), nullable=False, index=True)
    material_text = db.Column(db.String(255), nullable=False)
    base_unit = db.Column(db.String(20), nullable=False)
    location = db.Column(db.String(50), nullable=False, index=True)

    libre_utilizacion = db.Column(db.Float, default=0)

    # Fecha REAL del inventario
    fecha_inventario = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    # Fecha de carga al sistema
    creado_en = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    def __repr__(self):
        return (
            f"<InventoryHistory {self.snapshot_name} "
            f"({self.tipo})>"
        )
