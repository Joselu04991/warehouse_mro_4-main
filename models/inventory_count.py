from models import db
from datetime import datetime

class InventoryCount(db.Model):
    __tablename__ = "inventory_count"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, nullable=False, index=True)

    material_code = db.Column(db.String(50), nullable=False, index=True)
    material_text = db.Column(db.String(255))
    base_unit = db.Column(db.String(20))
    location = db.Column(db.String(50), nullable=False)

    stock_sistema = db.Column(db.Float, default=0)
    real_count = db.Column(db.Float, default=0)

    contado_en = db.Column(db.DateTime, nullable=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint(
            "user_id", "material_code", "location",
            name="uq_inventory_count_user_mat_loc"
        ),
    )

    def __repr__(self):
        return f"<InventoryCount {self.material_code} @ {self.location} = {self.real_count}>"
