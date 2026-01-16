from models import db
from datetime import datetime

class DocumentRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    document_type = db.Column(db.String(50))
    process_number = db.Column(db.String(50))
    weighing_number = db.Column(db.String(50))

    provider = db.Column(db.String(200))
    driver = db.Column(db.String(150))
    plate_tractor = db.Column(db.String(20))
    plate_trailer = db.Column(db.String(20))

    gross_weight = db.Column(db.Float)
    tare_weight = db.Column(db.Float)
    net_weight = db.Column(db.Float)

    origin = db.Column(db.Text)
    destination = db.Column(db.Text)

    issue_date = db.Column(db.Date)
    issue_time = db.Column(db.String(20))

    original_file = db.Column(db.String(255))
    excel_file = db.Column(db.String(255))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
