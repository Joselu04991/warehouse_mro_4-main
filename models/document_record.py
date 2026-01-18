from datetime import datetime
from models import db

class DocumentRecord(db.Model):
    __tablename__ = 'document_records'
    
    id = db.Column(db.Integer, primary_key=True)
    process_number = db.Column(db.String(100), nullable=False)
    provider = db.Column(db.String(200))
    driver = db.Column(db.String(150))
    plate_tractor = db.Column(db.String(50))
    net_weight = db.Column(db.Float)
    original_file = db.Column(db.String(500))
    excel_file = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    file_size = db.Column(db.Integer)
    uploaded_by = db.Column(db.Integer)  # ID del usuario
    
    def __repr__(self):
        return f'<DocumentRecord {self.process_number}>'
