from models import db
from datetime import datetime

class InventoryCount(db.Model):
    __tablename__ = "inventory_count"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, nullable=False, index=True)

    material_code = db.Column(db.String(50), nullable=False, index=True)
    material_text = db.Column(db.String(255), nullable=True)

    base_unit = db.Column(db.String(20), nullable=True)        # 👈 UM
    location = db.Column(db.String(50), nullable=False, index=True)

    stock_sistema = db.Column(db.Float, default=0)             # 👈 Libre utilización
    real_count = db.Column(db.Float, default=0)                # 👈 Conteo físico

    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    contado_en = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<InventoryCount {self.material_code} @ {self.location}>"
