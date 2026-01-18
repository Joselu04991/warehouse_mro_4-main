import re
import logging
from datetime import datetime, date
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def parse_document(text: str) -> Dict[str, Any]:
    """
    Parsear texto extraído del PDF de 3 páginas.
    Extrae datos específicos de cada página.
    """
    logger.info("Parseando documento de 3 páginas...")
    
    # Separar páginas
    pages = text.split('===== Page')
    if len(pages) < 4:
        logger.warning(f"Documento tiene {len(pages)} páginas, esperaba 3")
        # Si no está separado por '===== Page', intentar otra forma
        pages = [""] + text.split('\n\n\n')  # Alternativa
    
    resultado = {
        # Página 1 - Ticket de Pesaje
        'process_number': None,
        'weigh_number': None,
        'card': None,
        'operation': None,
        'tare_weight': None,
        'bruto_weight': None,
        'net_weight': None,
        'tare_date': None,
        'bruto_date': None,
        'net_date': None,
        'weigh_date': None,
        'driver': None,
        'plate_tractor': None,
        'provider': None,
        
        # Página 2 - Traslado
        'issue_date': None,
        'origin_address': None,
        'transfer_reason': None,
        'transport_mode': None,
        'transfer_start': None,
        'vehicle_brand': None,
        'driver_document_type': None,
        'driver_id': None,
        'destination_address': None,
        'fiscal_route': None,
        'recipient': None,
        'provider_nit': None,
        
        # Página 3 - Mercancía
        'product': None,
        'product_code': None,
        'un_code': None,
        'concentration': None,
        'unit': None,
        'guide_net_weight': None,
        'guide_gross_weight': None,
        'verification_code': None,
        'plate_trailer': None,
        'observations': None,
        
        # Derivados para compatibilidad
        'provider': None,  # Alias de recipient
        'plate_tractor_clean': None,
    }
    
    # ====== PÁGINA 1: TICKET DE PESAJE ======
    if len(pages) > 1:
        page1 = pages[1]
        parse_page1(page1, resultado)
    
    # ====== PÁGINA 2: TRASLADO ======
    if len(pages) > 2:
        page2 = pages[2]
        parse_page2(page2, resultado)
    
    # ====== PÁGINA 3: MERCANCÍA ======
    if len(pages) > 3:
        page3 = pages[3]
        parse_page3(page3, resultado)
    
    # Limpiar y normalizar datos
    clean_and_normalize(resultado)
    
    # Log resultados
    logger.info(f"Proceso extraído: {resultado.get('process_number')}")
    logger.info(f"Peso neto: {resultado.get('net_weight')} kg")
    logger.info(f"Producto: {resultado.get('product')}")
    
    return resultado


def parse_page1(text: str, resultado: Dict[str, Any]):
    """Parsear Página 1 - Ticket de Pesaje"""
    # Número de proceso
    proceso_match = re.search(r'PROCESO\s*:\s*(\d+)', text)
    if proceso_match:
        resultado['process_number'] = proceso_match.group(1)
    
    # Número de pesaje
    pesaje_match = re.search(r'NRO\.?\s*PESAJE\s*:\s*(\d+)', text)
    if pesaje_match:
        resultado['weigh_number'] = pesaje_match.group(1)
    
    # Fecha de impresión
    fecha_match = re.search(r'FECHA IMPRESION:\s*(\w+\s+\d+\s+\d+\s+\d+:\d+\w+)', text)
    if fecha_match:
        try:
            fecha_str = fecha_match.group(1)
            resultado['weigh_date'] = parse_date_english(fecha_str)
        except:
            pass
    
    # Tarjeta
    tarjeta_match = re.search(r'TARJETA\s*:\s*(\d+)', text)
    if tarjeta_match:
        resultado['card'] = tarjeta_match.group(1)
    
    # Operación
    operacion_match = re.search(r'OPERACION:\s*(.+?)PLACA', text, re.DOTALL)
    if operacion_match:
        resultado['operation'] = operacion_match.group(1).strip()
    
    # Placa
    placa_match = re.search(r'PLACA\s*:\s*(\w+)', text)
    if placa_match:
        resultado['plate_tractor'] = placa_match.group(1)
    
    # Conductor
    conductor_match = re.search(r'CONDUCTOR:\s*([^ ]+ [^ ]+(?: [^ ]+)?)', text)
    if conductor_match:
        resultado['driver'] = conductor_match.group(1).strip()
    
    # Proveedor (página 1)
    proveedor_match = re.search(r'PROVEEDOR:\s*(.+?)(?:\n|$)', text)
    if proveedor_match:
        resultado['provider'] = proveedor_match.group(1).strip()
    
    # Pesos (TARA, BRUTO, NETO)
    # TARA
    tara_match = re.search(r'TARA\s+(\d+)\s+(\w+\s+\d+\s+\d+\s+\d+:\d+\w+)', text)
    if tara_match:
        resultado['tare_weight'] = float(tara_match.group(1))
        try:
            resultado['tare_date'] = parse_date_english(tara_match.group(2))
        except:
            pass
    
    # BRUTO
    bruto_match = re.search(r'BRUTO\s+(\d+)\s+(\w+\s+\d+\s+\d+\s+\d+:\d+\w+)', text)
    if bruto_match:
        resultado['bruto_weight'] = float(bruto_match.group(1))
        try:
            resultado['bruto_date'] = parse_date_english(bruto_match.group(2))
        except:
            pass
    
    # NETO
    neto_match = re.search(r'NETO\s+(\d+)\s+(\w+\s+\d+\s+\d+\s+\d+:\d+\w+)', text)
    if neto_match:
        resultado['net_weight'] = float(neto_match.group(1))
        try:
            resultado['net_date'] = parse_date_english(neto_match.group(2))
        except:
            pass


def parse_page2(text: str, resultado: Dict[str, Any]):
    """Parsear Página 2 - Traslado"""
    # Fecha de emisión
    emision_match = re.search(r'FECHA DE EMISION:\s*(\d{2}/\d{2}/\d{4})', text)
    if emision_match:
        try:
            resultado['issue_date'] = datetime.strptime(emision_match.group(1), '%d/%m/%Y').date()
        except:
            pass
    
    # Dirección origen
    origen_match = re.search(r'DIRECCION DEL PUNTO DE PARTIDA:\s*(.+?)(?:\n\n|\*\*)', text, re.DOTALL)
    if origen_match:
        resultado['origin_address'] = origen_match.group(1).strip()
    
    # Motivo de traslado
    motivo_match = re.search(r'MOTIVO DE TRASLADO:\s*(.+?)(?:\n|$)', text)
    if motivo_match:
        resultado['transfer_reason'] = motivo_match.group(1).strip()
    
    # Modalidad de transporte
    modalidad_match = re.search(r'MODALIDAD DE TRANSPORTE:\s*(.+?)(?:\n|$)', text)
    if modalidad_match:
        resultado['transport_mode'] = modalidad_match.group(1).strip()
    
    # Fecha y hora inicio traslado
    inicio_match = re.search(r'FECHA Y HORA DEL INICIO TRASLADO:\s*(\d{2}/\d{2}/\d{2}\s+\d{2}:\d{2})', text)
    if inicio_match:
        try:
            resultado['transfer_start'] = datetime.strptime(inicio_match.group(1), '%d/%m/%y %H:%M')
        except:
            pass
    
    # Datos del transporte (placa, conductor, DNI)
    transporte_match = re.search(r'MARCA PLACA TIPO Y DOCUMENTO APELLIDOS Y NOMBRES\s+([^ ]+)\s+([^ ]+)\s+(\w+)\s+(\d+)\s+(.+)', text)
    if transporte_match:
        resultado['vehicle_brand'] = transporte_match.group(1)
        if not resultado['plate_tractor']:  # Si no se extrajo de la página 1
            resultado['plate_tractor'] = transporte_match.group(2)
        resultado['driver_document_type'] = transporte_match.group(3)
        resultado['driver_id'] = transporte_match.group(4)
        if not resultado['driver']:  # Si no se extrajo de la página 1
            resultado['driver'] = transporte_match.group(5)
    
    # Dirección destino
    destino_match = re.search(r'DIRECCION DEL PUNTO DE LLEGADA:\s*(.+?)(?:\n\n|\*\*)', text, re.DOTALL)
    if destino_match:
        resultado['destination_address'] = destino_match.group(1).strip()
    
    # Ruta fiscal
    ruta_match = re.search(r'Ruta Fiscal:\s*(.+?)(?:\n|$)', text)
    if ruta_match:
        resultado['fiscal_route'] = ruta_match.group(1).strip()
    
    # Destinatario (proveedor)
    destinatario_match = re.search(r'APELLIDOS, NOMBRES, DENOMINACION O RAZON SOCIAL:\s*(.+?)(?:\n|$)', text)
    if destinatario_match:
        resultado['recipient'] = destinatario_match.group(1).strip()
    
    # NIT/RUC del proveedor
    nit_match = re.search(r'RUC\s+(\d+[A-Z]?)', text)
    if nit_match:
        resultado['provider_nit'] = nit_match.group(1)


def parse_page3(text: str, resultado: Dict[str, Any]):
    """Parsear Página 3 - Mercancía"""
    # Producto
    producto_match = re.search(r'OXIDO DE CALCIO', text)
    if producto_match:
        resultado['product'] = "ÓXIDO DE CALCIO"
    else:
        # Buscar cualquier producto
        prod_match = re.search(r'(\d+-)?([A-Z\s]+-[A-Z\s]+)', text)
        if prod_match:
            resultado['product'] = prod_match.group(2).replace('-', ' ').strip()
    
    # Código de producto
    codigo_match = re.search(r'(\d+-\d+-\d+)', text)
    if codigo_match:
        resultado['product_code'] = codigo_match.group(1)
    
    # Código UN
    un_match = re.search(r'UN(\d+)', text)
    if un_match:
        resultado['un_code'] = f"UN{un_match.group(1)}"
    
    # Concentración
    concentracion_match = re.search(r'(\d+\.\d+ %.*?AL \d+\.\d+ %)', text)
    if concentracion_match:
        resultado['concentration'] = concentracion_match.group(1)
    
    # Unidad
    if 'KILOGRAMO' in text:
        resultado['unit'] = 'KILOGRAMO'
    
    # Peso neto de la guía
    peso_neto_match = re.search(r'Peso Neto de la guia\s+(\d+\.?\d*)', text)
    if peso_neto_match:
        resultado['guide_net_weight'] = float(peso_neto_match.group(1))
    
    # Peso bruto de la guía
    peso_bruto_match = re.search(r'Peso Bruto Total de la guia\s+(\d+\.?\d*)', text)
    if peso_bruto_match:
        resultado['guide_gross_weight'] = float(peso_bruto_match.group(1))
    
    # Código de verificación
    verificacion_match = re.search(r'CODI GO DE VERIFICACION:\s*(\d+)', text)
    if verificacion_match:
        resultado['verification_code'] = verificacion_match.group(1)
    
    # Observaciones (contiene placa remolque)
    obs_match = re.search(r'OBSERVACIONES:(.+?)$', text, re.DOTALL)
    if obs_match:
        obs_text = obs_match.group(1).strip()
        resultado['observations'] = obs_text
        
        # Extraer placa remolque de observaciones
        remolque_match = re.search(r'PLACA CARRETA:\s*([A-Z]+-\d+)', obs_text)
        if remolque_match:
            resultado['plate_trailer'] = remolque_match.group(1)
        
        # Extraer placa tracto si no se encontró antes
        if not resultado.get('plate_tractor'):
            tracto_match = re.search(r'PLACA TRACTO:\s*([A-Z]+-\d+)', obs_text)
            if tracto_match:
                resultado['plate_tractor'] = tracto_match.group(1)


def parse_date_english(date_str: str) -> Optional[datetime]:
    """Parsear fechas en formato inglés: Jan 14 2026 5:37PM"""
    try:
        # Limpiar y convertir
        date_str = date_str.strip()
        # Convertir a formato parseable
        date_str = date_str.replace('Jan', '01').replace('Feb', '02').replace('Mar', '03')
        date_str = date_str.replace('Apr', '04').replace('May', '05').replace('Jun', '06')
        date_str = date_str.replace('Jul', '07').replace('Aug', '08').replace('Sep', '09')
        date_str = date_str.replace('Oct', '10').replace('Nov', '11').replace('Dec', '12')
        
        # Formato: MM DD YYYY HH:MMPM
        parts = date_str.split()
        if len(parts) >= 4:
            month = parts[0]
            day = parts[1]
            year = parts[2]
            time_str = parts[3]
            
            # Convertir 12h a 24h
            if 'PM' in time_str:
                time_str = time_str.replace('PM', '').strip()
                hour, minute = map(int, time_str.split(':'))
                if hour < 12:
                    hour += 12
            elif 'AM' in time_str:
                time_str = time_str.replace('AM', '').strip()
                hour, minute = map(int, time_str.split(':'))
                if hour == 12:
                    hour = 0
            else:
                hour, minute = map(int, time_str.split(':'))
            
            return datetime(int(year), int(month), int(day), hour, minute)
    except Exception as e:
        logger.warning(f"Error parseando fecha {date_str}: {e}")
    
    return None


def clean_and_normalize(resultado: Dict[str, Any]):
    """Limpiar y normalizar datos"""
    
    # Asegurar que provider y recipient sean consistentes
    if resultado.get('recipient') and not resultado.get('provider'):
        resultado['provider'] = resultado['recipient']
    elif resultado.get('provider') and not resultado.get('recipient'):
        resultado['recipient'] = resultado['provider']
    
    # Limpiar placas (quitar espacios, unificar formato)
    if resultado.get('plate_tractor'):
        resultado['plate_tractor'] = resultado['plate_tractor'].replace(' ', '').strip()
        resultado['plate_tractor_clean'] = resultado['plate_tractor']
    
    if resultado.get('plate_trailer'):
        resultado['plate_trailer'] = resultado['plate_trailer'].replace(' ', '').strip()
    
    # Asegurar peso neto principal
    if not resultado.get('net_weight') and resultado.get('guide_net_weight'):
        resultado['net_weight'] = resultado['guide_net_weight']
    
    # Si no hay unidad, asumir kilogramos
    if not resultado.get('unit') and resultado.get('net_weight'):
        resultado['unit'] = 'KILOGRAMO'
    
    # Log de datos extraídos
    logger.info(f"Datos extraídos - Proceso: {resultado.get('process_number')}, "
                f"Peso: {resultado.get('net_weight')}, "
                f"Producto: {resultado.get('product')}")
