import cv2
import pytesseract
import numpy as np
from PIL import Image
import os
import re
from datetime import datetime

class TicketImageProcessor:
    """Procesador de imágenes de tickets de báscula"""
    
    def __init__(self, image_path):
        self.image_path = image_path
        self.text = ""
        self.extracted_data = {}
    
    def preprocess_image(self):
        """Preprocesa la imagen para mejorar OCR"""
        try:
            # Leer imagen
            img = cv2.imread(self.image_path)
            if img is None:
                raise ValueError(f"No se pudo leer la imagen: {self.image_path}")
            
            # Convertir a escala de grises
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Aumentar contraste
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(gray)
            
            # Reducir ruido
            denoised = cv2.medianBlur(enhanced, 3)
            
            # Aplicar threshold
            _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            return thresh
        except Exception as e:
            print(f"Error en preprocesamiento: {e}")
            return None
    
    def extract_text(self):
        """Extrae texto de la imagen usando OCR"""
        try:
            processed_img = self.preprocess_image()
            if processed_img is None:
                return ""
            
            # Configurar Tesseract para español
            custom_config = r'--oem 3 --psm 6 -l spa'
            
            # Extraer texto
            self.text = pytesseract.image_to_string(processed_img, config=custom_config)
            return self.text
        except Exception as e:
            print(f"Error en OCR: {e}")
            return ""
    
    def extract_ticket_data(self):
        """Extrae datos específicos del ticket"""
        if not self.text:
            self.extract_text()
        
        data = {}
        
        # Patrones de búsqueda para el ticket
        patterns = {
            'proceso': r'PROCESO\s*:\s*(\d+)',
            'nro_pesaje': r'NRO\.?\s*PESAJE\s*:\s*(\d+)',
            'fecha': r'FECHA IMPRESION:\s*(.+?\d{4}\s+\d{1,2}:\d{2}[AP]M)',
            'placa': r'PLACA\s*:\s*([A-Z0-9-]+)',
            'conductor': r'CONDUCTOR:\s*([A-Z\s]+(?:[A-Z][a-z]+)?)',
            'proveedor': r'PROVEEDOR:\s*([^:\n]+)',
            'peso_tara': r'TARA\s+(\d{4,})',
            'peso_bruto': r'BRUTO\s+(\d{4,})',
            'peso_neto': r'NETO\s+(\d{4,})',
            'material': r'(OXIDO DE CALCIO)',
            'origen': r'DIRECCION DEL PUNTO DE PARTIDA:(.+?)(?=DIRECCION|MOTIVO|\*\*)',
            'destino': r'DIRECCION DEL PUNTO DE LLEGADA:(.+?)(?=Ruta|DATOS|\*\*)',
            'ruc_destinatario': r'RUC\s+(\d{11}[A-Z]?)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, self.text, re.IGNORECASE | re.DOTALL)
            if match:
                data[key] = match.group(1).strip()
            else:
                data[key] = ""
        
        self.extracted_data = data
        return data
    
    def save_to_excel(self, output_path=None):
        """Guarda los datos extraídos a Excel"""
        from .excel import generate_excel  # Importar desde el módulo existente
        
        if not self.extracted_data:
            self.extract_ticket_data()
        
        # Crear lista de diccionarios para Excel
        data_list = [self.extracted_data]
        
        # Generar nombre de archivo
        if not output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f'ticket_data_{timestamp}.xlsx'
        
        # Usar la función existente de excel.py
        return generate_excel(data_list, output_path)

def process_ticket_images(image_paths, output_excel=None):
    """Procesa múltiples imágenes y genera Excel consolidado"""
    all_data = []
    
    for image_path in image_paths:
        print(f"Procesando: {image_path}")
        
        processor = TicketImageProcessor(image_path)
        data = processor.extract_ticket_data()
        
        if data:
            all_data.append(data)
            print(f"✓ Datos extraídos: {len(data)} campos")
        else:
            print(f"✗ No se pudieron extraer datos")
    
    if all_data and output_excel:
        from .excel import generate_excel
        return generate_excel(all_data, output_excel)
    
    return all_data
