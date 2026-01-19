from datetime import date
from models import db

class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)

    titulo = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)

    assigned_to_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    assigned_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    fecha_creacion = db.Column(db.Date, default=date.today)
    fecha_limite = db.Column(db.Date, nullable=False)
    fecha_completado = db.Column(db.Date, nullable=True)

    estado = db.Column(db.String(20), default="pendiente")  # pendiente | completada

    @property
    def days_left(self):
        return (self.fecha_limite - date.today()).days

    @property
    def is_overdue(self):
        return self.estado != "completada" and self.fecha_limite < date.today()
