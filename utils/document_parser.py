# utils/document_parser.py
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class WarehouseDocumentParser:
    def __init__(self):
        # Patrones básicos para extraer información
        self.patterns = {
            'process_number': r'PROCESO\s*[:]?\s*(\d+)',
            'supplier': r'PROVEEDOR\s*[:]?\s*([^\n]+)',
            'driver': r'CONDUCTOR\s*[:]?\s*([^\n]+)',
            'license_plate': r'PLACA\s*[:]?\s*([A-Z0-9-]+)',
            'tara': r'TARA\s*(\d+)',
            'bruto': r'BRUTO\s*(\d+)',
            'neto': r'NETO\s*(\d+)',
            'product': r'PRODUCTO\s*[:]?\s*([^\n]+)',
            'date': r'(\d{1,2}/\d{1,2}/\d{2,4})',
        }
    
    def parse_document(self, text: str) -> Dict[str, Any]:
        """Parsea texto extraído de documento"""
        result = {
            'process_number': None,
            'supplier': None,
            'driver': None,
            'license_plate': None,
            'weights': {},
            'product': None,
            'dates': [],
            'parse_success': False,
            'parse_error': None
        }
        
        try:
            # Limpiar texto
            text = text.upper()
            
            # Buscar cada campo
            result['process_number'] = self._search_pattern(text, 'process_number')
            result['supplier'] = self._search_pattern(text, 'supplier')
            result['driver'] = self._search_pattern(text, 'driver')
            result['license_plate'] = self._search_pattern(text, 'license_plate')
            result['product'] = self._search_pattern(text, 'product')
            
            # Extraer pesos
            tara = self._search_pattern(text, 'tara')
            bruto = self._search_pattern(text, 'bruto')
            neto = self._search_pattern(text, 'neto')
            
            if tara:
                result['weights']['tara'] = float(tara)
            if bruto:
                result['weights']['bruto'] = float(bruto)
            if neto:
                result['weights']['neto'] = float(neto)
            
            # Extraer fechas
            date_matches = re.findall(self.patterns['date'], text)
            result['dates'] = list(set(date_matches))
            
            # Calcular neto si falta
            if 'neto' not in result['weights'] and 'tara' in result['weights'] and 'bruto' in result['weights']:
                result['weights']['neto'] = result['weights']['bruto'] - result['weights']['tara']
            
            result['parse_success'] = True
            
        except Exception as e:
            result['parse_error'] = str(e)
            logger.error(f"Error parseando documento: {e}")
        
        return result
    
    def _search_pattern(self, text: str, pattern_name: str) -> Optional[str]:
        """Busca un patrón en el texto"""
        if pattern_name not in self.patterns:
            return None
        
        match = re.search(self.patterns[pattern_name], text)
        if match and match.groups():
            return match.group(1).strip()
        return None

# Funciones de conveniencia
def parse_warehouse_document(text: str) -> Dict[str, Any]:
    """Parsea un documento de almacén"""
    parser = WarehouseDocumentParser()
    return parser.parse_document(text)

def parse_multiple_documents(texts: List[str]) -> List[Dict[str, Any]]:
    """Parsea múltiples documentos"""
    parser = WarehouseDocumentParser()
    return [parser.parse_document(text) for text in texts]
