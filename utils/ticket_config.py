import json
import os

class TicketConfig:
    """Maneja configuración de campos para tickets"""
    
    CONFIG_FILE = 'ticket_fields_config.json'
    
    DEFAULT_FIELDS = {
        'proceso': {'extract': True, 'display': 'PROCESO', 'required': True},
        'nro_pesaje': {'extract': True, 'display': 'NRO. PESAJE', 'required': True},
        'fecha': {'extract': True, 'display': 'FECHA', 'required': True},
        'placa': {'extract': True, 'display': 'PLACA', 'required': True},
        'conductor': {'extract': True, 'display': 'CONDUCTOR', 'required': True},
        'proveedor': {'extract': True, 'display': 'PROVEEDOR', 'required': False},
        'peso_tara': {'extract': True, 'display': 'TARA (KG)', 'required': True},
        'peso_bruto': {'extract': True, 'display': 'BRUTO (KG)', 'required': True},
        'peso_neto': {'extract': True, 'display': 'NETO (KG)', 'required': True},
        'material': {'extract': True, 'display': 'MATERIAL', 'required': False},
        'origen': {'extract': True, 'display': 'ORIGEN', 'required': False},
        'destino': {'extract': True, 'display': 'DESTINO', 'required': False},
        'ruc_destinatario': {'extract': True, 'display': 'RUC', 'required': False}
    }
    
    def __init__(self):
        self.config = self.load_config()
    
    def load_config(self):
        """Carga configuración desde archivo JSON"""
        if os.path.exists(self.CONFIG_FILE):
            with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return self.DEFAULT_FIELDS
    
    def save_config(self):
        """Guarda configuración a archivo JSON"""
        with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def get_selected_fields(self):
        """Obtiene campos seleccionados para extracción"""
        return [field for field, settings in self.config.items() 
                if settings.get('extract', True)]
    
    def update_field(self, field_name, settings):
        """Actualiza configuración de un campo"""
        if field_name in self.config:
            self.config[field_name].update(settings)
            self.save_config()
    
    def get_field_display_name(self, field_name):
        """Obtiene nombre para mostrar de un campo"""
        return self.config.get(field_name, {}).get('display', field_name)
