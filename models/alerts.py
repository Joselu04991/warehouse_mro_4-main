from models import db
from datetime import datetime, timedelta
import json

class Alert(db.Model):
    __tablename__ = "alertas"

    id = db.Column(db.Integer, primary_key=True)

    alert_type = db.Column(db.String(50), nullable=True)
    tipo = db.Column(db.String(50), nullable=True)

    message = db.Column(db.Text, nullable=True)
    mensaje = db.Column(db.String(255), nullable=True)

    severity = db.Column(db.String(20), default="info")
    nivel = db.Column(db.String(20), default="info")

    origen = db.Column(db.String(100), default="Sistema")
    usuario = db.Column(db.String(120), nullable=True)

    estado = db.Column(db.String(20), default="activo")

    # 👉 SE GUARDA EN UTC (CORRECTO)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    detalles = db.Column(db.Text, nullable=True)

    # ============================================================
    # COMPATIBILIDAD CON TEMPLATES (created_at)
    # ============================================================
    @property
    def created_at(self):
        return self.fecha_local

    # ============================================================
    # FECHA CONVERTIDA A HORA PERÚ (UTC - 5)
    # ============================================================
    @property
    def fecha_local(self):
        if self.fecha:
            return self.fecha - timedelta(hours=5)
        return None

    # ============================================================
    # NORMALIZADOR AUTOMÁTICO
    # ============================================================
    def __init__(self, **kwargs):
        if "alert_type" in kwargs:
            kwargs.setdefault("tipo", kwargs["alert_type"])
        if "message" in kwargs:
            kwargs.setdefault("mensaje", kwargs["message"])
        if "severity" in kwargs:
            kwargs.setdefault("nivel", kwargs["severity"])

        super().__init__(**kwargs)

    # ============================================================
    # JSON HELPERS
    # ============================================================
    def set_detalles(self, data: dict):
        self.detalles = json.dumps(data)

    def get_detalles(self):
        try:
            return json.loads(self.detalles) if self.detalles else {}
        except:
            return {}

    def __repr__(self):
        return f"<Alerta {self.tipo or self.alert_type}>"
