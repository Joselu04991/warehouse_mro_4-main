from models import db
from datetime import datetime

class DocumentRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    process_number = db.Column(db.String(50))
    provider = db.Column(db.String(200))
    driver = db.Column(db.String(150))
    plate_tractor = db.Column(db.String(20))
    net_weight = db.Column(db.Float)
    original_file = db.Column(db.String(255))
    excel_file = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)