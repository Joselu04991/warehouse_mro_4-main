from datetime import datetime
from models import db

class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)

    assigned_to = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))

    due_date = db.Column(db.Date, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)

    status = db.Column(db.String(20), default="pendiente")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_late(self):
        if self.completed_at:
            return self.completed_at.date() > self.due_date
        return datetime.utcnow().date() > self.due_date
