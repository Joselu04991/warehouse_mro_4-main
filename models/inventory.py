from models import db
from datetime import datetime

class InventoryItem(db.Model):
    __tablename__ = "inventory"

    id = db.Column(db.Integer, primary_key=True)

    material_code = db.Column(db.String(50), nullable=False, index=True)
    material_text = db.Column(db.String(255), nullable=False)
    base_unit = db.Column(db.String(20), nullable=False)

    location = db.Column(db.String(50), nullable=False, index=True)

    libre_utilizacion = db.Column(db.Float, default=0)

    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def status(self):
        if self.libre_utilizacion <= 0:
            return "CRÍTICO"
        if self.libre_utilizacion <= 5:
            return "BAJO"
        if self.libre_utilizacion <= 15:
            return "MEDIO"
        return "NORMAL"

    def __repr__(self):
        return f"<InventoryItem {self.material_code} - {self.location}>"

