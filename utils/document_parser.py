# utils/document_parser.py
import re
from datetime import datetime
from typing import Dict, Any, List, Optional 
import logging

logger = logging.getLogger(__name__)

class WarehouseDocumentParser:
    def __init__(self):
        # Patrones robustos para texto de OCR (con posibles errores)
        self.patterns = {
            'process_number': [
                r'(?:PROCESO|PESO|TICKET)[\s:]*[#]?[\s:]*(\d{5,})',
                r'N(?:UMERO|RO|°)?[\.\s]*PESAJE[\s:]*(\d{6,})',
                r'PESO[\s:]*(\d{5,})',
                r'CODIGO[\s:]*(\d{5,})',
            ],
            'supplier': [
                r'PROVEEDOR[\s:]*([^\n]{3,50})(?=\n|$)',
                r'RAZON[\s]+SOCIAL[\s:]*([^\n]{3,50})(?=\n|$)',
                r'EMPRESA[\s:]*([^\n]{3,50})(?=\n|$)',
                r'DESTINATARIO[\s:]*([^\n]{3,50})(?=\n|$)',
                r'CLIENTE[\s:]*([^\n]{3,50})(?=\n|$)',
            ],
            'driver': [
                r'CONDUCTOR[\s:]*([A-Z\s]{5,30})(?=\n|$)',
                r'CHOFER[\s:]*([A-Z\s]{5,30})(?=\n|$)',
                r'NOMBRE[\s]+CONDUCTOR[\s:]*([A-Z\s]{5,30})(?=\n|$)',
                r'APELLIDOS[\s]+Y[\s]+NOMBRES[\s:]*([A-Z\s]{5,30})(?=\n|$)',
                r'CONDUCTOR[\s:]*([A-Z]+[\s]+[A-Z]+)(?=\s+DNI|\s+LIC|\n|$)',
            ],
            'license_plate': [
                r'PLACA[\s:]*([A-Z]{2,3}[\s-]?\d{3,4})',
                r'PATENTE[\s:]*([A-Z]{2,3}[\s-]?\d{3,4})',
                r'MATRICULA[\s:]*([A-Z]{2,3}[\s-]?\d{3,4})',
                r'([A-Z]{2,3}[\s-]?\d{3,4})(?=\s+-\s+VEHICULO|\s+PLACA)',
                r'CDL[\s-]?\d{3}',  # Patrón específico del ejemplo
            ],
            'weights': {
                'tara': r'TARA[\s:]*(\d{4,})',
                'bruto': r'BRUTO[\s:]*(\d{4,})',
                'neto': r'NETO[\s:]*(\d{4,})',
                'peso': r'PESO[\s:]*(\d{4,})',
            },
            'product': [
                r'PRODUCTO[\s:]*([^\n]{3,50})(?=\n|$)',
                r'MATERIAL[\s:]*([^\n]{3,50})(?=\n|$)',
                r'DESCRIPCION[\s:]*([^\n]{3,50})(?=\n|$)',
                r'MERCADERIA[\s:]*([^\n]{3,50})(?=\n|$)',
                r'(OXIDO[\s]+DE[\s]+CALCIO|CAL|ARENA|CEMENTO|ACERO)',
            ],
            'dates': [
                r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'FECHA[\s:]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'(\d{1,2}[\s]+(?:ENE|FEB|MAR|ABR|MAY|JUN|JUL|AGO|SEP|OCT|NOV|DIC)[\s]+\d{4})',
                r'FECHA[\s]+IMPRESION[\s:]*([^\n]+)(?=\n|$)',
            ],
            'document_id': [
                r'RUC[\s:]*(\d{11}[A-Z]?)',
                r'DNI[\s:]*(\d{8})',
                r'LICENCIA[\s:]*(\d{8})',
                r'DOCUMENTO[\s:]*(\d{8,})',
            ]
        }
        
        # Correcciones para errores comunes de OCR
        self.ocr_corrections = [
            (r'O(\d)', r'0\1'),  # O123 → 0123
            (r'(\d)O', r'\10'),   # 123O → 1230
            (r'l(\d)', r'1\1'),   # l23 → 123
            (r'(\d)l', r'\11'),   # 12l → 121
            (r'I(\d)', r'1\1'),   # I23 → 123
            (r'Z(\d)', r'2\1'),   # Z3 → 23
            (r'(\d)Z', r'\12'),   # 1Z → 12
            (r'S(\d)', r'5\1'),   # S6 → 56
            (r'B(\d)', r'8\1'),   # B9 → 89
            (r'\s+', ' '),        # Múltiples espacios a uno
        ]
    
    def parse_document(self, text: str) -> Dict[str, Any]:
        """Parsea texto extraído de PDF/imagen"""
        result = {
            'document_type': self._detect_document_type(text),
            'process_number': None,
            'supplier': None,
            'driver': None,
            'license_plate': None,
            'weights': {},
            'product': None,
            'dates': [],
            'additional_info': {},
            'pages': text.count('=== PÁGINA') or 1,
            'raw_preview': text[:300] + '...' if len(text) > 300 else text
        }
        
        try:
            # Limpiar y normalizar texto de OCR
            cleaned_text = self._clean_ocr_text(text)
            
            # Extraer información
            result.update(self._extract_all_info(cleaned_text))
            
            # Validar y completar información
            self._validate_and_complete(result)
            
            logger.info(f"Documento parseado: {result['document_type']}")
            
        except Exception as e:
            logger.error(f"Error parseando documento: {e}")
            result['parse_error'] = str(e)
            result['parse_success'] = False
        else:
            result['parse_success'] = True
        
        return result
    
    def _clean_ocr_text(self, text: str) -> str:
        """Limpia texto de OCR con correcciones comunes"""
        # Convertir a mayúsculas
        text = text.upper()
        
        # Aplicar correcciones
        for wrong, correct in self.ocr_corrections:
            text = re.sub(wrong, correct, text)
        
        # Reemplazar caracteres problemáticos
        replacements = {
            '|': 'I', ']': 'I', '[': 'I',
            ')': 'I', '(': 'I', '}': 'I',
            '{': 'I', '`': "'", '´': "'",
            'º': '°', 'ª': '°',
        }
        
        for wrong, correct in replacements.items():
            text = text.replace(wrong, correct)
        
        return text
    
    def _detect_document_type(self, text: str) -> str:
        """Detecta el tipo de documento"""
        text_upper = text.upper()
        
        if 'TICKET DE BASCULA' in text_upper or 'PESAJE' in text_upper:
            return 'ticket_pesaje'
        elif 'GUIA DE REMISION' in text_upper or 'TRASLADO' in text_upper:
            return 'guia_remision'
        elif 'FACTURA' in text_upper or 'INVOICE' in text_upper:
            return 'factura'
        elif 'RECEPCION' in text_upper or 'BAUCHER' in text_upper:
            return 'recepcion'
        else:
            return 'desconocido'
    
    def _extract_all_info(self, text: str) -> Dict[str, Any]:
        """Extrae toda la información del texto"""
        info = {}
        
        # Extraer número de proceso
        info['process_number'] = self._extract_field(text, 'process_number')
        
        # Extraer proveedor
        info['supplier'] = self._extract_field(text, 'supplier')
        
        # Extraer conductor
        info['driver'] = self._extract_field(text, 'driver')
        
        # Extraer placa
        info['license_plate'] = self._extract_field(text, 'license_plate')
        
        # Extraer pesos
        info['weights'] = self._extract_weights(text)
        
        # Extraer producto
        info['product'] = self._extract_field(text, 'product')
        
        # Extraer fechas
        info['dates'] = self._extract_dates(text)
        
        # Extraer información adicional
        info['additional_info'] = self._extract_additional_info(text)
        
        return info
    
    def _extract_field(self, text: str, field_name: str) -> Optional[str]:
        """Extrae un campo específico usando múltiples patrones"""
        if field_name not in self.patterns:
            return None
        
        for pattern in self.patterns[field_name]:
            try:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value = match.group(1).strip() if match.groups() else match.group(0).strip()
                    
                    # Limpiar valor
                    value = self._clean_value(value, field_name)
                    
                    if value:
                        return value
            except Exception as e:
                logger.debug(f"Patrón falló para {field_name}: {pattern}, error: {e}")
                continue
        
        return None
    
    def _extract_weights(self, text: str) -> Dict[str, float]:
        """Extrae todos los pesos del documento"""
        weights = {}
        
        for weight_type, pattern in self.patterns['weights'].items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    # Extraer número, limpiando caracteres no numéricos
                    weight_str = re.sub(r'[^\d]', '', match.group(1))
                    if weight_str:
                        weights[weight_type] = float(weight_str)
                except (ValueError, IndexError) as e:
                    logger.debug(f"Error extrayendo peso {weight_type}: {e}")
                    continue
        
        # Buscar pesos en formato tabla
        weight_matches = re.findall(r'(\d{4,})\s*KG', text)
        if weight_matches and len(weight_matches) >= 2:
            if 'tara' not in weights and len(weight_matches) > 0:
                weights['tara'] = float(weight_matches[0])
            if 'bruto' not in weights and len(weight_matches) > 1:
                weights['bruto'] = float(weight_matches[1])
            if 'neto' not in weights and len(weight_matches) > 2:
                weights['neto'] = float(weight_matches[2])
        
        return weights
    
    def _extract_dates(self, text: str) -> List[str]:
        """Extrae todas las fechas del documento"""
        dates = []
        
        for pattern in self.patterns['dates']:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    date_str = match[0]
                else:
                    date_str = match
                
                if self._is_valid_date(date_str):
                    dates.append(date_str)
        
        # Eliminar duplicados manteniendo orden
        seen = set()
        unique_dates = []
        for date in dates:
            if date not in seen:
                seen.add(date)
                unique_dates.append(date)
        
        return unique_dates
    
    def _extract_additional_info(self, text: str) -> Dict[str, Any]:
        """Extrae información adicional"""
        info = {}
        
        # RUC
        ruc_match = re.search(r'RUC[\s:]*(\d{11})', text)
        if ruc_match:
            info['ruc'] = ruc_match.group(1)
        
        # DNI
        dni_match = re.search(r'DNI[\s:]*(\d{8})', text)
        if dni_match:
            info['dni'] = dni_match.group(1)
        
        # Dirección
        dir_match = re.search(r'DIRECCION[\s:]*([^\n]{10,100})', text)
        if dir_match:
            info['direccion'] = dir_match.group(1).strip()
        
        # Observaciones
        obs_match = re.search(r'OBSERVACIONES[\s:]*([^\n]{10,200})', text)
        if obs_match:
            info['observaciones'] = obs_match.group(1).strip()
        
        # Monto/total
        total_match = re.search(r'TOTAL[\s:]*([$\s]*\d+[,\d]*)', text)
        if total_match:
            info['total'] = total_match.group(1).strip()
        
        return info
    
    def _clean_value(self, value: str, field_type: str) -> str:
        """Limpia el valor extraído según el tipo de campo"""
        if field_type in ['process_number', 'document_id']:
            # Solo números
            return re.sub(r'[^\d]', '', value)
        elif field_type == 'license_plate':
            # Formato uniforme: ABC-123
            value = re.sub(r'[^\w]', '', value)
            if len(value) >= 3 and value[:3].isalpha():
                return f"{value[:3]}-{value[3:]}"
            return value
        elif field_type in ['driver', 'supplier']:
            # Título apropiado
            return ' '.join([word.capitalize() for word in value.split()])
        else:
            return value.strip()
    
    def _is_valid_date(self, date_str: str) -> bool:
        """Valida si una cadena parece ser una fecha válida"""
        # Patrones comunes de fecha
        patterns = [
            r'\d{1,2}/\d{1,2}/\d{2,4}',
            r'\d{1,2}-\d{1,2}-\d{2,4}',
            r'\d{1,2}\s+(?:ENE|FEB|MAR|ABR|MAY|JUN|JUL|AGO|SEP|OCT|NOV|DIC)\s+\d{4}',
        ]
        
        for pattern in patterns:
            if re.fullmatch(pattern, date_str, re.IGNORECASE):
                return True
        
        return False
    
    def _validate_and_complete(self, result: Dict[str, Any]):
        """Valida y completa información faltante"""
        weights = result.get('weights', {})
        
        # Calcular peso neto si falta
        if 'neto' not in weights and 'tara' in weights and 'bruto' in weights:
            weights['neto'] = weights['bruto'] - weights['tara']
            result['weights'] = weights
        
        # Validar consistencia de pesos
        if 'tara' in weights and 'bruto' in weights:
            if weights['tara'] >= weights['bruto']:
                logger.warning(f"Tara ({weights['tara']}) >= Bruto ({weights['bruto']})")
        
        # Formatear placa si es necesario
        if result.get('license_plate'):
            plate = result['license_plate']
            if '-' not in plate and len(plate) >= 3:
                result['license_plate'] = f"{plate[:3]}-{plate[3:]}"


# Funciones de conveniencia
def parse_warehouse_document(text: str) -> Dict[str, Any]:
    parser = WarehouseDocumentParser()
    return parser.parse_document(text)

def parse_multiple_documents(texts: List[str]) -> List[Dict[str, Any]]:
    parser = WarehouseDocumentParser()
    results = []
    
    for i, text in enumerate(texts):
        result = parser.parse_document(text)
        result['document_index'] = i
        results.append(result)
    
    return results
