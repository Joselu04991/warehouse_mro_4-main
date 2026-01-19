# utils/document_parser.py
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class WarehouseDocumentParser:
    def __init__(self):
        # Patrones específicos para los 9 campos requeridos
        self.patterns = {
            'numero_guia': [
                r'GUIA[:\s]*N°?[\s]*(\d+)',
                r'N°?[\s]*GUIA[:\s]*(\d+)',
                r'PROCESO[:\s]*(\d+)',
                r'PESAJE[:\s]*(\d+)',
                r'TICKET[:\s]*(\d+)',
                r'NUMERO[:\s]*(\d+)'
            ],
            'fecha': [
                r'FECHA[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'FECHA[:\s]*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[\s]+\d{1,2}[\s]+\d{4}'
            ],
            'cantidad': [
                r'CANTIDAD[:\s]*(\d+[.,]?\d*)',
                r'PESO[\s]*NETO[:\s]*(\d+)',
                r'NETO[:\s]*(\d+)',
                r'(\d+)[\s]*KG'
            ],
            'unidad': [
                r'UNIDAD[:\s]*(KG|KILOS|KILOGRAMOS)',
                r'(\d+)[\s]*(KG|KILOS)'
            ],
            'material': [
                r'MATERIAL[:\s]*([^\n]{3,50})',
                r'PRODUCTO[:\s]*([^\n]{3,50})',
                r'DESCRIPCION[:\s]*([^\n]{3,50})',
                r'(OXIDO[\s]+DE[\s]+CALCIO|CAL|CEMENTO|ARENA|ARCILLA|MINERAL)'
            ],
            'ruc_proveedor': [
                r'RUC[\s]*PROVEEDOR[:\s]*(\d{11})',
                r'PROVEEDOR.*RUC[:\s]*(\d{11})',
                r'RUC[:\s]*(\d{11})'
            ],
            'ruc_transportista': [
                r'RUC[\s]*TRANSPORTISTA[:\s]*(\d{11})',
                r'TRANSPORTISTA.*RUC[:\s]*(\d{11})',
                r'EMPRESA.*RUC[:\s]*(\d{11})'
            ],
            'placa_vehiculo': [
                r'PLACA[:\s]*([A-Z]{2,3}[\s-]?\d{3,4})',
                r'PATENTE[:\s]*([A-Z]{2,3}[\s-]?\d{3,4})',
                r'VEHICULO[:\s]*([A-Z]{2,3}[\s-]?\d{3,4})'
            ],
            'licencia_conductor': [
                r'LICENCIA[:\s]*(\d{8,10})',
                r'DNI[:\s]*(\d{8})',
                r'CONDUCTOR.*DNI[:\s]*(\d{8})',
                r'LIC[:\s]*(\d{8})'
            ]
        }
    
    def parse_document(self, text: str) -> Dict[str, Any]:
        """Extrae los 9 campos específicos del documento"""
        result = {
            'campos_extraidos': {},
            'campos_faltantes': [],
            'parse_success': False,
            'parse_error': None,
            'texto_preview': text[:300] + '...' if len(text) > 300 else text
        }
        
        try:
            # Limpiar texto
            cleaned_text = text.upper()
            
            # Definir los 9 campos requeridos
            campos_requeridos = {
                'A': 'N° de Guía',
                'B': 'Fecha', 
                'C': 'CANTIDAD DE PRESENTACION',
                'D': 'Unidad (kg)',
                'E': 'Material',
                'F': 'Número de RUC del PROVEEDOR',
                'G': 'Número de RUC del transportista',
                'H': 'Placa del vehículo',
                'I': 'Número de licencia de conducir del conductor'
            }
            
            # Mapeo de campos internos a los nombres de columna
            mapeo_campos = {
                'A': ('numero_guia', self._extract_field(cleaned_text, 'numero_guia')),
                'B': ('fecha', self._extract_field(cleaned_text, 'fecha')),
                'C': ('cantidad', self._extract_field(cleaned_text, 'cantidad')),
                'D': ('unidad', self._extract_field(cleaned_text, 'unidad', default='KG')),
                'E': ('material', self._extract_field(cleaned_text, 'material')),
                'F': ('ruc_proveedor', self._extract_field(cleaned_text, 'ruc_proveedor')),
                'G': ('ruc_transportista', self._extract_field(cleaned_text, 'ruc_transportista')),
                'H': ('placa_vehiculo', self._extract_field(cleaned_text, 'placa_vehiculo')),
                'I': ('licencia_conductor', self._extract_field(cleaned_text, 'licencia_conductor'))
            }
            
            # Procesar cada campo
            for col, (campo_interno, valor) in mapeo_campos.items():
                nombre_columna = campos_requeridos[col]
                
                if valor:
                    result['campos_extraidos'][nombre_columna] = valor
                else:
                    result['campos_faltantes'].append(nombre_columna)
            
            # Formatear placa si existe
            if 'Placa del vehículo' in result['campos_extraidos']:
                placa = result['campos_extraidos']['Placa del vehículo']
                if len(placa) >= 3 and placa[:3].isalpha():
                    result['campos_extraidos']['Placa del vehículo'] = f"{placa[:3]}-{placa[3:]}"
            
            # Si al menos se extrajo algo, considerar éxito
            if result['campos_extraidos']:
                result['parse_success'] = True
            else:
                result['parse_error'] = 'No se pudo extraer ningún campo del documento'
            
            # Calcular porcentaje de éxito
            total_campos = len(campos_requeridos)
            campos_encontrados = len(result['campos_extraidos'])
            result['porcentaje_exito'] = f"{(campos_encontrados / total_campos * 100):.1f}%"
            
        except Exception as e:
            result['parse_error'] = str(e)
            logger.error(f"Error parseando documento: {e}")
        
        return result
    
    def _extract_field(self, text: str, field_name: str, default: Optional[str] = None) -> Optional[str]:
        """Extrae un campo específico usando múltiples patrones"""
        if field_name not in self.patterns:
            return default
        
        for pattern in self.patterns[field_name]:
            try:
                match = re.search(pattern, text)
                if match:
                    value = match.group(1).strip() if match.groups() else match.group(0).strip()
                    
                    # Limpiar valor
                    value = self._clean_value(value, field_name)
                    
                    if value:
                        return value
            except Exception as e:
                logger.debug(f"Patrón falló para {field_name}: {pattern}")
                continue
        
        return default
    
    def _clean_value(self, value: str, field_type: str) -> str:
        """Limpia el valor extraído según el tipo de campo"""
        if field_type in ['numero_guia', 'ruc_proveedor', 'ruc_transportista', 'licencia_conductor']:
            # Solo números
            return re.sub(r'[^\d]', '', value)
        elif field_type == 'placa_vehiculo':
            # Formato uniforme
            return re.sub(r'[^\w]', '', value).upper()
        elif field_type == 'unidad':
            # Asegurar que sea KG
            if 'KG' in value.upper():
                return 'KG'
            return value.upper()
        elif field_type == 'cantidad':
            # Solo números, quitar decimales si no son necesarios
            value = re.sub(r'[^\d.,]', '', value)
            if '.' in value or ',' in value:
                try:
                    return str(float(value.replace(',', '.')))
                except:
                    return value
            return value
        else:
            return value.strip()

# Funciones de conveniencia
def parse_warehouse_document(text: str) -> Dict[str, Any]:
    parser = WarehouseDocumentParser()
    return parser.parse_document(text)

def parse_multiple_documents(texts: List[str]) -> List[Dict[str, Any]]:
    parser = WarehouseDocumentParser()
    return [parser.parse_document(text) for text in texts]
