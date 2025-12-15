from datetime import datetime
from models import db

class Score(db.Model):
    __tablename__ = "scores"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True)

    points = db.Column(db.Integer, default=20)
    last_reset_year = db.Column(db.Integer, default=datetime.utcnow().year)
