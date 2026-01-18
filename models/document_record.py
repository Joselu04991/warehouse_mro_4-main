from datetime import datetime, date, time
from app import db  # Importar db desde app, NO desde models

class DocumentRecord(db.Model):
    __tablename__ = 'document_records'
    
    # ====== TODOS LOS CAMPOS DE LAS 3 PÁGINAS ======
    id = db.Column(db.Integer, primary_key=True)
    
    # Página 1 - Ticket de Pesaje
    process_number = db.Column(db.String(100))
    weigh_number = db.Column(db.String(50))
    card = db.Column(db.String(50))
    operation = db.Column(db.String(100))
    tare_weight = db.Column(db.Float)
    bruto_weight = db.Column(db.Float)
    net_weight = db.Column(db.Float)
    tare_date = db.Column(db.DateTime)
    bruto_date = db.Column(db.DateTime)
    net_date = db.Column(db.DateTime)
    weigh_date = db.Column(db.DateTime)
    
    # Página 2 - Traslado
    issue_date = db.Column(db.Date)
    origin_address = db.Column(db.Text)
    transfer_reason = db.Column(db.String(100))
    transport_mode = db.Column(db.String(50))
    transfer_start = db.Column(db.DateTime)
    vehicle_brand = db.Column(db.String(50))
    plate_tractor = db.Column(db.String(50))
    driver_document_type = db.Column(db.String(20))
    driver = db.Column(db.String(150))
    driver_id = db.Column(db.String(50))
    destination_address = db.Column(db.Text)
    fiscal_route = db.Column(db.String(100))
    recipient = db.Column(db.String(200))
    provider_nit = db.Column(db.String(100))
    
    # Página 3 - Mercancía
    product = db.Column(db.String(200))
    product_code = db.Column(db.String(50))
    un_code = db.Column(db.String(20))
    concentration = db.Column(db.String(100))
    unit = db.Column(db.String(50))
    guide_net_weight = db.Column(db.Float)
    guide_gross_weight = db.Column(db.Float)
    verification_code = db.Column(db.String(100))
    plate_trailer = db.Column(db.String(50))
    observations = db.Column(db.Text)
    
    # Sistema
    original_file = db.Column(db.String(500))
    excel_file = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    file_size = db.Column(db.Integer)
    uploaded_by = db.Column(db.Integer)
    status = db.Column(db.String(50), default='PROCESADO')
    
    def __repr__(self):
        return f'<DocumentRecord {self.process_number}>'
    
    def to_excel_dict(self):
        """Convierte a diccionario para Excel"""
        return {
            'NÚMERO DE PROCESO': self.process_number or '',
            'PROVEEDOR': self.recipient or '',
            'CONDUCTOR': self.driver or '',
            'PLACA TRACTO': self.plate_tractor or '',
            'PLACA REMOLQUE': self.plate_trailer or '',
            'PESO NETO': self.net_weight or 0.0,
            'PESO BRUTO': self.bruto_weight or 0.0,
            'TARA': self.tare_weight or 0.0,
            'PRODUCTO': self.product or '',
            'CANTIDAD': self.guide_net_weight or 0.0,
            'UNIDAD': self.unit or 'KILOGRAMO',
            'HUMEDAD': None,  # Estos vienen de otro lugar
            'IMPUREZAS': None,
            'TEMPERATURA': None,
            'ESTADO': self.status or 'APROBADO',
            'FECHA RECEPCIÓN': self.weigh_date.date() if self.weigh_date else date.today(),
            'HORA RECEPCIÓN': self.weigh_date.time() if self.weigh_date else datetime.now().time(),
            'TRANSPORTADORA': self.transport_mode or '',
            'NIT PROVEEDOR': self.provider_nit or '',
            'CÉDULA CONDUCTOR': self.driver_id or ''
        }
