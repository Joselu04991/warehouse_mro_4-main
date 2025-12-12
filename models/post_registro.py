from models import db
from datetime import datetime

class PostRegistro(db.Model):
    __tablename__ = "post_registro"

    id = db.Column(db.Integer, primary_key=True)
    bulto_id = db.Column(db.Integer, db.ForeignKey("bultos.id"), nullable=False)

    codigo_material = db.Column(db.String(120))
    cantidad_sistema = db.Column(db.Integer)
    cantidad_real = db.Column(db.Integer)
    diferencia = db.Column(db.Integer)

    observacion = db.Column(db.String(255))   # ← 🔥 ESTA LÍNEA ES LA QUE TE FALTABA

    registrado_por = db.Column(db.String(100))
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<PostRegistro {self.id}>"
