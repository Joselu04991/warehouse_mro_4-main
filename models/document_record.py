import PyPDF2
import re
from datetime import datetime
from models.document_record import DocumentRecord

def extract_3page_pdf(pdf_path):
    """Extrae datos de las 3 páginas del ticket de pesaje"""
    
    data = {}
    
    with open(pdf_path, 'rb') as file:
        pdf = PyPDF2.PdfReader(file)
        
        # ===== PÁGINA 1: TICKET DE PESAJE =====
        if len(pdf.pages) > 0:
            page1 = pdf.pages[0].extract_text()
            
            # PROCESO y NÚMERO DE PESAJE
            proceso_match = re.search(r'PROCESO\s*:\s*(\S+)', page1)
            pesaje_match = re.search(r'NRO\.\s*PESAJE\s*:\s*(\S+)', page1)
            data['process_number'] = proceso_match.group(1) if proceso_match else None
            data['weigh_number'] = pesaje_match.group(1) if pesaje_match else None
            
            # FECHA IMPRESIÓN
            fecha_match = re.search(r'FECHA IMPRESION:\s*(\w+ \d+ \d+ \d+:\d+[APM]+)', page1)
            if fecha_match:
                try:
                    data['weigh_date'] = datetime.strptime(fecha_match.group(1), '%b %d %Y %I:%M%p')
                except:
                    pass
            
            # TARJETA y OPERACIÓN
            tarjeta_match = re.search(r'TARJETA\s*:\s*(\S+)', page1)
            operacion_match = re.search(r'OPERACION:\s*([\w\s\-]+)', page1)
            data['card'] = tarjeta_match.group(1) if tarjeta_match else None
            data['operation'] = operacion_match.group(1).strip() if operacion_match else None
            
            # PESOS (TARA, BRUTO, NETO) con fechas
            pesos = {}
            # Patrón: "TARA 16910 Jan 14 2026 5:37PM"
            peso_pattern = r'(TARA|BRUTO|NETO)\s+(\d+)\s+(\w+ \d+ \d+ \d+:\d+[APM]+)'
            for match in re.finditer(peso_pattern, page1):
                tipo, valor, fecha_str = match.groups()
                try:
                    fecha = datetime.strptime(fecha_str, '%b %d %Y %I:%M%p')
                    if tipo == 'TARA':
                        data['tare_weight'] = float(valor)
                        data['tare_date'] = fecha
                    elif tipo == 'BRUTO':
                        data['bruto_weight'] = float(valor)
                        data['bruto_date'] = fecha
                    elif tipo == 'NETO':
                        data['net_weight'] = float(valor)
                        data['net_date'] = fecha
                except:
                    pass
            
            # PLACA y CONDUCTOR (Página 1)
            placa_match = re.search(r'PLACA\s*:\s*(\S+)', page1)
            conductor_match = re.search(r'CONDUCTOR:\s*([\w\s]+)', page1)
            data['plate_tractor'] = placa_match.group(1) if placa_match else None
            data['driver'] = conductor_match.group(1).strip() if conductor_match else None
            
            # PROVEEDOR
            proveedor_match = re.search(r'PROVEEDOR:\s*([\w\s\.]+)', page1)
            if proveedor_match:
                data['provider'] = proveedor_match.group(1).strip()
        
        # ===== PÁGINA 2: TRASLADO =====
        if len(pdf.pages) > 1:
            page2 = pdf.pages[1].extract_text()
            
            # FECHA EMISIÓN (13/01/2026)
            emision_match = re.search(r'FECHA DE EMISION:\s*(\d+/\d+/\d+)', page2)
            if emision_match:
                try:
                    data['issue_date'] = datetime.strptime(emision_match.group(1), '%d/%m/%Y').date()
                except:
                    pass
            
            # DIRECCIÓN DE PARTIDA (puede ser multilínea)
            partida_match = re.search(r'DIRECCION DEL PUNTO DE PARTIDA:\s*(.+?)(?=\n\*\*|\nFECHA|$)', page2, re.DOTALL)
            if partida_match:
                data['origin_address'] = ' '.join(partida_match.group(1).split())
            
            # MOTIVO y MODALIDAD
            motivo_match = re.search(r'MOTIVO DE TRASLADO:\s*([^\n]+)', page2)
            modalidad_match = re.search(r'MODALIDAD DE TRANSPORTE:\s*([^\n]+)', page2)
            data['transfer_reason'] = motivo_match.group(1).strip() if motivo_match else None
            data['transport_mode'] = modalidad_match.group(1).strip() if modalidad_match else None
            
            # INICIO TRASLADO (13/01/26 06:00 PM)
            inicio_match = re.search(r'INICIO TRASLADO:\s*(\d+/\d+/\d+\s+\d+:\d+\s*[APM]+)', page2, re.IGNORECASE)
            if inicio_match:
                try:
                    data['transfer_start'] = datetime.strptime(inicio_match.group(1), '%d/%m/%y %I:%M %p')
                except:
                    pass
            
            # MARCA, PLACA, DOCUMENTO DEL CONDUCTOR
            marca_match = re.search(r'MARCA\s+PLACA\s+TIPO.*?\n([^\n]+)', page2)
            if marca_match:
                partes = marca_match.group(1).split()
                if len(partes) >= 4:
                    data['vehicle_brand'] = partes[0]
                    # La placa ya la tenemos de página 1, pero por si acaso
                    if not data.get('plate_tractor'):
                        data['plate_tractor'] = partes[1]
                    data['driver_document_type'] = partes[2]
                    data['driver_id'] = partes[3]
            
            # DESTINO
            destino_match = re.search(r'DIRECCION DEL PUNTO DE LLEGADA:\s*(.+?)(?=\nRuta|\n\*\*|$)', page2, re.DOTALL)
            if destino_match:
                data['destination_address'] = ' '.join(destino_match.group(1).split())
            
            # RUTA FISCAL
            ruta_match = re.search(r'Ruta Fiscal:\s*([^\n]+)', page2)
            data['fiscal_route'] = ruta_match.group(1).strip() if ruta_match else None
            
            # DESTINATARIO y RUC
            destinatario_match = re.search(r'DENOMINACION O RAZON SOCIAL:\s*([^\n]+)', page2)
            ruc_match = re.search(r'RUC\s+(\S+)', page2)
            data['recipient'] = destinatario_match.group(1).strip() if destinatario_match else None
            data['provider_nit'] = ruc_match.group(1) if ruc_match else None
        
        # ===== PÁGINA 3: MERCANCÍA =====
        if len(pdf.pages) > 2:
            page3 = pdf.pages[2].extract_text()
            
            # PRODUCTO (ej: "1-102200001-000001- OXIDO DE CALCIO")
            producto_match = re.search(r'\d+-\d+-\d+-\s*([\w\s]+)-', page3)
            if producto_match:
                data['product'] = producto_match.group(1).strip()
            
            # CÓDIGO ONU
            un_match = re.search(r'UN(\d+)', page3)
            data['un_code'] = f"UN{un_match.group(1)}" if un_match else None
            
            # CONCENTRACIÓN (71.52% MIN AL 90.80%)
            conc_match = re.search(r'([\d\.]+%[\w\s]+%[\d\.]+%)', page3)
            data['concentration'] = conc_match.group(1) if conc_match else None
            
            # PESOS DE GUÍA
            neto_guia_match = re.search(r'Peso Neto de la guia\s+([\d\.]+)', page3)
            bruto_guia_match = re.search(r'Peso Bruto Total de la guia\s+([\d\.]+)', page3)
            if neto_guia_match:
                data['guide_net_weight'] = float(neto_guia_match.group(1))
            if bruto_guia_match:
                data['guide_gross_weight'] = float(bruto_guia_match.group(1))
            
            # CÓDIGO VERIFICACIÓN
            codigo_match = re.search(r'CODIGO DE VERIFICACION:\s*(\S+)', page3, re.IGNORECASE)
            data['verification_code'] = codigo_match.group(1) if codigo_match else None
            
            # OBSERVACIONES (contiene placas del remolque)
            obs_match = re.search(r'OBSERVACIONES:\s*(.+?)(?=\n\n|$)', page3, re.DOTALL)
            if obs_match:
                obs_text = obs_match.group(1).strip()
                data['observations'] = obs_text
                
                # Extraer placa del remolque de observaciones
                trailer_match = re.search(r'CARRETA:\s*(\S+)', obs_text)
                if trailer_match:
                    data['plate_trailer'] = trailer_match.group(1)
    
    return data

def process_complete_ticket(pdf_path, user_id=1):
    """Procesa las 3 páginas y guarda en base de datos"""
    
    try:
        # Extraer datos
        pdf_data = extract_3page_pdf(pdf_path)
        
        # Crear registro
        record = DocumentRecord()
        
        # Asignar todos los campos encontrados
        for key, value in pdf_data.items():
            if value is not None:
                # Verificar que el campo exista en el modelo
                if hasattr(record, key):
                    setattr(record, key, value)
                else:
                    print(f"⚠️ Campo '{key}' no existe en el modelo")
        
        # Campos del sistema
        record.original_file = pdf_path
        record.uploaded_by = user_id
        record.status = 'PROCESADO'
        record.created_at = datetime.now()
        
        # Si no hay fecha de pesaje, usar la actual
        if not record.weigh_date:
            record.weigh_date = datetime.now()
        
        # Guardar
        db.session.add(record)
        db.session.commit()
        
        print(f"✅ Registro creado: {record.process_number}")
        print(f"📊 Datos: {record.to_excel_dict()}")
        
        return record
        
    except Exception as e:
        print(f"❌ Error procesando PDF: {e}")
        db.session.rollback()
        return None
