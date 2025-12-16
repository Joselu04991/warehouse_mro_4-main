from models import db
from datetime import datetime
import pytz

PERU_TZ = pytz.timezone("America/Lima")

class InventoryHistory(db.Model):
    __tablename__ = "inventory_history"

    id = db.Column(db.Integer, primary_key=True)

    snapshot_id = db.Column(db.String(64), nullable=False, index=True)

    snapshot_name = db.Column(db.String(150), nullable=False)
    snapshot_type = db.Column(
        db.String(20),
        default="DIARIO"
    )  # DIARIO | HISTORICO

    uploaded_by = db.Column(
        db.Integer,
        nullable=True
    )  # user_id

    material_code = db.Column(db.String(50), nullable=False, index=True)
    material_text = db.Column(db.String(255), nullable=False)
    base_unit = db.Column(db.String(20), nullable=False)
    location = db.Column(db.String(50), nullable=False, index=True)

    libre_utilizacion = db.Column(db.Float, default=0)

    creado_en = db.Column(
        db.DateTime,
        default=lambda: datetime.now(PERU_TZ)
    )

    def __repr__(self):
        return f"<History {self.snapshot_name} - {self.material_code}>"
