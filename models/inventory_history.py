from models import db
from datetime import datetime

class InventoryHistory(db.Model):
    __tablename__ = "inventory_history"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, nullable=False, index=True)

    snapshot_id = db.Column(db.String(64), nullable=False, index=True)
    snapshot_name = db.Column(db.String(150), nullable=False)

    item_n = db.Column(db.String(30), nullable=True)

    material_code = db.Column(db.String(50), nullable=False, index=True)
    material_text = db.Column(db.String(255), nullable=False)
    base_unit = db.Column(db.String(20), nullable=False)
    location = db.Column(db.String(50), nullable=False, index=True)

    # Tus columnas reales
    fisico = db.Column(db.Float, default=0)
    stock_sap = db.Column(db.Float, default=0)
    difere = db.Column(db.Float, default=0)
    observacion = db.Column(db.String(255), nullable=True)

    # compat con lo que ya usabas (si algo aún lee "libre_utilizacion")
    libre_utilizacion = db.Column(db.Float, default=0)

    creado_en = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    source_type = db.Column(db.String(30), default="DIARIO")     # DIARIO / HISTORICO / CIERRE
    source_filename = db.Column(db.String(255), nullable=True)

    closed_by = db.Column(db.String(120), nullable=True)
    closed_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<History {self.snapshot_name} - {self.material_code}>"
