# utils/excel_generator.py
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
import os
import logging

logger = logging.getLogger(__name__)

def generate_warehouse_excel(parsed_documents: List[Dict[str, Any]], 
                           output_path: Optional[str] = None) -> str:
    """
    Genera un archivo Excel organizado con los datos parseados
    
    Args:
        parsed_documents: Lista de diccionarios con datos parseados
        output_path: Ruta donde guardar el Excel (opcional)
        
    Returns:
        Ruta del archivo generado
    """
    
    if not parsed_documents:
        raise ValueError("No hay documentos para generar Excel")
    
    # Si no se proporciona output_path, crear uno temporal
    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"warehouse_data_{timestamp}.xlsx"
    
    try:
        # Preparar datos para DataFrame
        rows = []
        
        for doc in parsed_documents:
            # Documento con error
            if doc.get('parse_error') or not doc.get('parse_success', True):
                row = {
                    'Estado': 'ERROR',
                    'Error': doc.get('parse_error', 'Desconocido'),
                    'Procesado': 'NO',
                    'Nombre_Archivo': doc.get('filename', 'Desconocido'),
                    'Tipo_Documento': doc.get('document_type', 'Desconocido'),
                    'Paginas': doc.get('pages', 0),
                    'Texto_Muestra': doc.get('raw_preview', '')[:200],
                }
            else:
                # Documento parseado correctamente
                row = {
                    'Estado': 'OK',
                    'Procesado': 'SI',
                    'Nombre_Archivo': doc.get('filename', ''),
                    'Tipo_Documento': doc.get('document_type', ''),
                    'Numero_Proceso': doc.get('process_number'),
                    'Proveedor': doc.get('supplier'),
                    'Conductor': doc.get('driver'),
                    'Placa_Vehiculo': doc.get('license_plate'),
                    'Producto_Material': doc.get('product'),
                    'Peso_Tara_Kg': doc.get('weights', {}).get('tara'),
                    'Peso_Bruto_Kg': doc.get('weights', {}).get('bruto'),
                    'Peso_Neto_Kg': doc.get('weights', {}).get('neto'),
                    'Fechas_Encontradas': ', '.join(doc.get('dates', [])),
                    'RUC': doc.get('additional_info', {}).get('ruc'),
                    'DNI_Conductor': doc.get('additional_info', {}).get('dni'),
                    'Direccion': doc.get('additional_info', {}).get('direccion', ''),
                    'Observaciones': doc.get('additional_info', {}).get('observaciones', ''),
                    'Paginas': doc.get('pages', 1),
                    'OCR_Exitoso': doc.get('ocr_success', True),
                }
            
            rows.append(row)
        
        # Crear DataFrame
        df = pd.DataFrame(rows)
        
        # Ordenar columnas lógicamente
        column_order = [
            'Estado', 'Procesado', 'Nombre_Archivo', 'Tipo_Documento',
            'Numero_Proceso', 'Proveedor', 'Conductor', 'Placa_Vehiculo',
            'Producto_Material', 'Peso_Tara_Kg', 'Peso_Bruto_Kg', 'Peso_Neto_Kg',
            'Fechas_Encontradas', 'RUC', 'DNI_Conductor', 'Direccion',
            'Observaciones', 'Paginas', 'OCR_Exitoso', 'Error', 'Texto_Muestra'
        ]
        
        # Filtrar solo columnas que existen
        existing_columns = [col for col in column_order if col in df.columns]
        df = df[existing_columns]
        
        # Crear writer de Excel
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Hoja 1: Datos completos
            df.to_excel(writer, sheet_name='Datos_Completos', index=False)
            
            # Hoja 2: Resumen
            self._create_summary_sheet(writer, parsed_documents, df)
            
            # Hoja 3: Solo documentos exitosos
            successful_docs = [doc for doc in parsed_documents 
                             if doc.get('parse_success', True) and not doc.get('parse_error')]
            if successful_docs:
                self._create_successful_sheet(writer, successful_docs)
            
            # Hoja 4: Errores (si los hay)
            error_docs = [doc for doc in parsed_documents 
                         if doc.get('parse_error') or not doc.get('parse_success', True)]
            if error_docs:
                self._create_errors_sheet(writer, error_docs)
            
            # Ajustar anchos de columna
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            cell_value = str(cell.value) if cell.value is not None else ""
                            if len(cell_value) > max_length:
                                max_length = len(cell_value)
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
        
        logger.info(f"Excel generado exitosamente: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Error generando Excel: {e}")
        raise

def _create_summary_sheet(self, writer, parsed_documents: List[Dict[str, Any]], df: pd.DataFrame):
    """Crea hoja de resumen"""
    try:
        successful_docs = [doc for doc in parsed_documents 
                          if doc.get('parse_success', True) and not doc.get('parse_error')]
        error_docs = [doc for doc in parsed_documents 
                     if doc.get('parse_error') or not doc.get('parse_success', True)]
        
        # Calcular pesos totales
        total_tara = 0
        total_bruto = 0
        total_neto = 0
        
        for doc in successful_docs:
            weights = doc.get('weights', {})
            total_tara += weights.get('tara', 0)
            total_bruto += weights.get('bruto', 0)
            total_neto += weights.get('neto', 0)
        
        summary_data = {
            'Metrica': [
                'Fecha Generación',
                'Total Documentos',
                'Documentos Exitosos',
                'Documentos con Error',
                'Tasa de Éxito (%)',
                'Peso Tara Total (Kg)',
                'Peso Bruto Total (Kg)',
                'Peso Neto Total (Kg)',
                'Proveedores Diferentes',
                'Conductores Diferentes',
                'Productos Diferentes',
                'Tipo Documento Más Común'
            ],
            'Valor': [
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                len(parsed_documents),
                len(successful_docs),
                len(error_docs),
                f"{(len(successful_docs) / len(parsed_documents) * 100):.1f}" if parsed_documents else "0",
                f"{total_tara:,.0f}",
                f"{total_bruto:,.0f}",
                f"{total_neto:,.0f}",
                len(set(doc.get('supplier') for doc in successful_docs if doc.get('supplier'))),
                len(set(doc.get('driver') for doc in successful_docs if doc.get('driver'))),
                len(set(doc.get('product') for doc in successful_docs if doc.get('product'))),
                df['Tipo_Documento'].mode().iloc[0] if not df.empty and 'Tipo_Documento' in df.columns else 'N/A'
            ]
        }
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Resumen', index=False)
        
    except Exception as e:
        logger.warning(f"Error creando hoja de resumen: {e}")

def _create_successful_sheet(self, writer, successful_docs: List[Dict[str, Any]]):
    """Crea hoja solo con documentos exitosos"""
    try:
        # Extraer solo los datos importantes
        simple_data = []
        for doc in successful_docs:
            simple_data.append({
                'Archivo': doc.get('filename'),
                'Proceso': doc.get('process_number'),
                'Proveedor': doc.get('supplier'),
                'Producto': doc.get('product'),
                'Peso Neto (Kg)': doc.get('weights', {}).get('neto'),
                'Fecha': doc.get('dates', [''])[0] if doc.get('dates') else '',
                'Placa': doc.get('license_plate')
            })
        
        simple_df = pd.DataFrame(simple_data)
        simple_df.to_excel(writer, sheet_name='Exitosos_Simplificado', index=False)
        
    except Exception as e:
        logger.warning(f"Error creando hoja de exitosos: {e}")

def _create_errors_sheet(self, writer, error_docs: List[Dict[str, Any]]):
    """Crea hoja con errores"""
    try:
        error_data = []
        for doc in error_docs:
            error_data.append({
                'Archivo': doc.get('filename', 'Desconocido'),
                'Error': doc.get('parse_error', 'Error desconocido'),
                'Tipo': doc.get('file_type', 'Desconocido'),
                'Paginas': doc.get('pages', 0),
                'Texto_Muestra': doc.get('raw_preview', '')[:500]
            })
        
        error_df = pd.DataFrame(error_data)
        error_df.to_excel(writer, sheet_name='Errores', index=False)
        
    except Exception as e:
        logger.warning(f"Error creando hoja de errores: {e}")

# Versión simplificada para uso inmediato
def generate_simple_excel(parsed_documents: List[Dict[str, Any]], output_path: str) -> str:
    """
    Versión simplificada del generador de Excel
    """
    if not parsed_documents:
        raise ValueError("No hay documentos para generar Excel")
    
    rows = []
    for doc in parsed_documents:
        if doc.get('parse_success', True):
            rows.append({
                'Archivo': doc.get('filename', ''),
                'Proceso': doc.get('process_number'),
                'Proveedor': doc.get('supplier'),
                'Conductor': doc.get('driver'),
                'Placa': doc.get('license_plate'),
                'Producto': doc.get('product'),
                'Tara (Kg)': doc.get('weights', {}).get('tara'),
                'Bruto (Kg)': doc.get('weights', {}).get('bruto'),
                'Neto (Kg)': doc.get('weights', {}).get('neto'),
                'Fecha': doc.get('dates', [''])[0] if doc.get('dates') else ''
            })
    
    df = pd.DataFrame(rows)
    df.to_excel(output_path, index=False)
    return output_path
