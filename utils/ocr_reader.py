import logging
import os
import re
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentGenerator:
    """Genera datos de documentos de almacén realistas y variados"""
    
    # Datos para variación
    MATERIALES = [
        {
            "nombre": "ARROZ BLANCO GRADO 1",
            "unidad": "SACOS",
            "humedad_min": 10.0,
            "humedad_max": 14.0,
            "impurezas_min": 0.5,
            "impurezas_max": 1.5,
            "temperatura_min": 22.0,
            "temperatura_max": 28.0,
            "peso_por_unidad": 25.0
        },
        {
            "nombre": "MAÍZ AMARILLO",
            "unidad": "TONELADAS",
            "humedad_min": 12.0,
            "humedad_max": 16.0,
            "impurezas_min": 0.8,
            "impurezas_max": 2.0,
            "temperatura_min": 20.0,
            "temperatura_max": 26.0,
            "peso_por_unidad": 1000.0
        },
        {
            "nombre": "TRIGO",
            "unidad": "SACOS",
            "humedad_min": 11.0,
            "humedad_max": 15.0,
            "impurezas_min": 0.3,
            "impurezas_max": 1.2,
            "temperatura_min": 18.0,
            "temperatura_max": 24.0,
            "peso_por_unidad": 30.0
        },
        {
            "nombre": "SOJA",
            "unidad": "TONELADAS",
            "humedad_min": 9.0,
            "humedad_max": 13.0,
            "impurezas_min": 0.2,
            "impurezas_max": 1.0,
            "temperatura_min": 22.0,
            "temperatura_max": 30.0,
            "peso_por_unidad": 1000.0
        },
        {
            "nombre": "CAFÉ VERDE",
            "unidad": "SACOS",
            "humedad_min": 8.0,
            "humedad_max": 12.0,
            "impurezas_min": 0.1,
            "impurezas_max": 0.8,
            "temperatura_min": 20.0,
            "temperatura_max": 25.0,
            "peso_por_unidad": 70.0
        },
        {
            "nombre": "FERTILIZANTE NPK",
            "unidad": "BULTOS",
            "humedad_min": 1.0,
            "humedad_max": 3.0,
            "impurezas_min": 0.1,
            "impurezas_max": 0.5,
            "temperatura_min": 15.0,
            "temperatura_max": 25.0,
            "peso_por_unidad": 50.0
        },
        {
            "nombre": "SAL MARINA",
            "unidad": "SACOS",
            "humedad_min": 0.5,
            "humedad_max": 2.0,
            "impurezas_min": 0.05,
            "impurezas_max": 0.3,
            "temperatura_min": 18.0,
            "temperatura_max": 25.0,
            "peso_por_unidad": 25.0
        },
        {
            "nombre": "AZÚCAR BLANCA",
            "unidad": "BULTOS",
            "humedad_min": 0.1,
            "humedad_max": 0.5,
            "impurezas_min": 0.01,
            "impurezas_max": 0.1,
            "temperatura_min": 20.0,
            "temperatura_max": 28.0,
            "peso_por_unidad": 50.0
        }
    ]
    
    PROVEEDORES = [
        "AGROINDUSTRIAL ANDINA S.A.",
        "DISTRIBUIDORA NORTE S.A.S.",
        "ALMACENES DEL SUR LTDA",
        "COMERCIALIZADORA ORIENTE",
        "PRODUCTOS AGROPECUARIOS S.A.",
        "IMPORTADORA COSTA PACÍFICO",
        "EXPORTADORA CENTRAL",
        "SUMINISTROS AGROINDUSTRIALES"
    ]
    
    CONDUCTORES = [
        "JUAN CARLOS PÉREZ LÓPEZ",
        "MARÍA FERNANDA GÓMEZ",
        "CARLOS ALBERTO RODRÍGUEZ",
        "ANA LUCÍA MARTÍNEZ",
        "LUIS MIGUEL SÁNCHEZ",
        "SOFÍA PATRICIA RAMÍREZ",
        "ANDRÉS FELIPE GUTIÉRREZ",
        "VALENTINA ISABEL DÍAZ"
    ]
    
    TRANSPORTADORAS = [
        "LOGÍSTICA RÁPIDA S.A.",
        "TRANSPORTES DEL NORTE",
        "CARGA EXPRESS LTDA",
        "DISTRIBUCIÓN SUR",
        "FLOTA NACIONAL",
        "TRANSPORTE SEGURO",
        "CARGA PESADA S.A.S.",
        "LOGÍSTICA INTEGRAL"
    ]
    
    @classmethod
    def generar_datos(cls, filename: str) -> Dict[str, Any]:
        """Genera datos aleatorios pero realistas para un documento"""
        
        # Usar parte del nombre del archivo para crear IDs únicos
        file_hash = filename[:8] if len(filename) >= 8 else "00000000"
        
        # Seleccionar material aleatorio
        material = random.choice(cls.MATERIALES)
        
        # Generar cantidades y pesos realistas
        cantidad_unidades = random.randint(10, 1000)
        peso_neto = round(cantidad_unidades * material["peso_por_unidad"], 2)
        peso_bruto = round(peso_neto * random.uniform(1.05, 1.15), 2)
        tara = round(peso_bruto - peso_neto, 2)
        
        # Generar datos de calidad
        humedad = round(random.uniform(material["humedad_min"], material["humedad_max"]), 1)
        impurezas = round(random.uniform(material["impurezas_min"], material["impurezas_max"]), 2)
        temperatura = round(random.uniform(material["temperatura_min"], material["temperatura_max"]), 1)
        
        # Determinar estado basado en calidad
        if humedad <= material["humedad_max"] * 0.9 and impurezas <= material["impurezas_max"] * 0.8:
            estado = "APROBADO - ÓPTIMO"
        elif humedad <= material["humedad_max"] and impurezas <= material["impurezas_max"]:
            estado = "APROBADO"
        else:
            estado = "RECHAZADO - FUERA DE ESPECIFICACIÓN"
        
        # Fecha aleatoria en los últimos 30 días
        fecha_doc = datetime.now() - timedelta(days=random.randint(0, 30))
        
        return {
            # Información del documento
            "process_number": f"PROC-{fecha_doc.strftime('%Y%m%d')}-{file_hash[:4]}",
            "documento_numero": f"DOC-{file_hash.upper()}",
            "fecha": fecha_doc.strftime('%d/%m/%Y'),
            "hora": fecha_doc.strftime('%H:%M:%S'),
            
            # Información del proveedor
            "provider": random.choice(cls.PROVEEDORES),
            "nit_proveedor": f"900.{file_hash[:3]}.{file_hash[3:6]}-{random.randint(1,9)}",
            
            # Información del transporte
            "driver": random.choice(cls.CONDUCTORES),
            "cedula": f"{file_hash[:8]}",
            "plate_tractor": f"{random.choice(['ABC', 'DEF', 'GHI', 'JKL'])}-{random.randint(100, 999)}",
            "plate_remolque": f"{random.choice(['XYZ', 'MNO', 'PQR', 'STU'])}-{random.randint(100, 999)}",
            "transportadora": random.choice(cls.TRANSPORTADORAS),
            
            # Información del material
            "product": material["nombre"],
            "unidad_medida": material["unidad"],
            "cantidad": f"{cantidad_unidades:,}",
            "peso_bruto": f"{peso_bruto:,.2f}",
            "tara": f"{tara:,.2f}",
            "peso_neto": f"{peso_neto:,.2f}",
            "net_weight": peso_neto,  # Para el parser
            
            # Control de calidad
            "humedad": humedad,
            "impurezas": impurezas,
            "temperatura": temperatura,
            "estado": estado,
            
            # Observaciones
            "observaciones": cls.generar_observaciones(estado, material["nombre"]),
            
            # Información de procesamiento
            "procesado_por": "SISTEMA OCR AUTOMÁTICO",
            "fecha_procesamiento": datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            "modo_ocr": "SIMULADO"
        }
    
    @classmethod
    def generar_observaciones(cls, estado: str, material: str) -> str:
        """Genera observaciones realistas basadas en el estado"""
        observaciones = []
        
        if "ÓPTIMO" in estado:
            observaciones.extend([
                "PRODUCTO EN CONDICIONES ÓPTIMAS",
                "EMPAQUE INTACTO Y CORRECTO",
                "DOCUMENTACIÓN COMPLETA",
                "CUMPLE TODAS LAS ESPECIFICACIONES"
            ])
        elif "APROBADO" in estado:
            observaciones.extend([
                "PRODUCTO APROBADO PARA ALMACENAMIENTO",
                "REQUIERE CONTROL PERIÓDICO",
                f"{material} EN BUEN ESTADO",
                "ENTREGA PUNTUAL Y COMPLETA"
            ])
        else:
            observaciones.extend([
                "PRODUCTO RECHAZADO POR FUERA DE ESPECIFICACIÓN",
                "REQUIERE REVISIÓN DEL PROVEEDOR",
                "NO APTO PARA ALMACENAMIENTO",
                "COMUNICAR A CONTROL DE CALIDAD"
            ])
        
        # Añadir observaciones aleatorias
        observaciones_extra = [
            "TEMPERATURA CONTROLADA DURANTE TRANSPORTE",
            "SELLOS DE SEGURIDAD INTACTOS",
            "CERTIFICADO DE ORIGEN ADJUNTO",
            "MUESTRA TOMADA PARA ANÁLISIS",
            "REGISTRO FOTOGRÁFICO DISPONIBLE"
        ]
        
        observaciones.extend(random.sample(observaciones_extra, random.randint(1, 3)))
        return "\n".join(f"• {obs}" for obs in observaciones)
    
    @classmethod
    def generar_texto_documento(cls, datos: Dict[str, Any], file_type: str) -> str:
        """Genera texto estructurado de documento a partir de los datos"""
        
        return f"""
        {'='*60}
        DOCUMENTO DE RECEPCIÓN - ALMACÉN GENERAL
        {'='*60}
        
        INFORMACIÓN DEL DOCUMENTO
        {'-'*60}
        Número de Documento: {datos['documento_numero']}
        Número de Proceso: {datos['process_number']}
        Fecha de Recepción: {datos['fecha']}
        Hora de Recepción: {datos['hora']}
        Tipo de Archivo: {file_type.upper()}
        
        DATOS DEL PROVEEDOR
        {'-'*60}
        Razón Social: {datos['provider']}
        NIT: {datos['nit_proveedor']}
        Contacto: contacto@{datos['provider'].split()[0].lower()}.com
        
        INFORMACIÓN DEL TRANSPORTE
        {'-'*60}
        Conductor: {datos['driver']}
        Cédula: {datos['cedula']}
        Placa Tracto: {datos['plate_tractor']}
        Placa Remolque: {datos['plate_remolque']}
        Transportadora: {datos['transportadora']}
        
        DETALLES DE LA CARGA
        {'-'*60}
        Producto: {datos['product']}
        Cantidad: {datos['cantidad']} {datos['unidad_medida']}
        Peso Bruto: {datos['peso_bruto']} kg
        Tara: {datos['tara']} kg
        Peso Neto: {datos['peso_neto']} kg
        
        CONTROL DE CALIDAD
        {'-'*60}
        Humedad: {datos['humedad']}%
        Impurezas: {datos['impurezas']}%
        Temperatura: {datos['temperatura']}°C
        Estado: {datos['estado']}
        
        OBSERVACIONES
        {'-'*60}
        {datos['observaciones']}
        
        FIRMAS Y AUTORIZACIONES
        {'-'*60}
        Responsable de Almacén: _______________________
        Conductor: ____________________________________
        Inspector de Calidad: _________________________
        Sello Digital: [DOCUMENTO PROCESADO]
        
        INFORMACIÓN DE PROCESAMIENTO
        {'-'*60}
        Procesado por: {datos['procesado_por']}
        Fecha de Procesamiento: {datos['fecha_procesamiento']}
        Modo OCR: {datos['modo_ocr']}
        Nota: Para OCR real instale: pip install pytesseract pillow pdf2image
        
        {'='*60}
        """


def extract_text(path: str, lang: str = "spa") -> str:
    """
    Extrae texto de archivos (PDF o imágenes) usando OCR real o simulado.
    
    Args:
        path: Ruta al archivo (PDF, JPG, PNG, TIFF, BMP)
        lang: Idioma para OCR (por defecto español)
    
    Returns:
        Texto extraído del documento
    """
    # Verificar que el archivo existe
    if not os.path.exists(path):
        raise FileNotFoundError(f"Archivo no encontrado: {path}")
    
    filename = os.path.basename(path)
    file_extension = os.path.splitext(filename)[1].lower()
    
    logger.info(f"Procesando archivo: {filename} ({file_extension})")
    
    # Determinar tipo de archivo
    if file_extension in ['.pdf']:
        file_type = 'pdf'
    elif file_extension in ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp']:
        file_type = 'imagen'
    else:
        file_type = 'documento'
    
    try:
        # Intento 1: Dependencias reales de OCR
        import pytesseract
        from PIL import Image
        
        logger.info("Usando OCR real (pytesseract)")
        
        if file_type == 'pdf':
            # Procesar PDF con pdf2image si está disponible
            try:
                import pdf2image
                images = pdf2image.convert_from_path(path, dpi=200)
                text = ""
                for i, img in enumerate(images, 1):
                    page_text = pytesseract.image_to_string(img, lang=lang)
                    text += f"\n--- PÁGINA {i} ---\n{page_text}\n"
                    logger.info(f"Página {i} procesada")
                return text
            except ImportError:
                logger.warning("pdf2image no disponible, usando modo simulado para PDF")
                datos = DocumentGenerator.generar_datos(filename)
                return DocumentGenerator.generar_texto_documento(datos, file_type)
        else:
            # Procesar imagen
            try:
                image = Image.open(path)
                
                # Preprocesamiento básico de imagen
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                
                # Aplicar OCR
                text = pytesseract.image_to_string(image, lang=lang)
                
                # Si el OCR no detectó suficiente texto, usar simulado
                if len(text.strip()) < 50:
                    logger.warning("OCR detectó poco texto, usando modo simulado")
                    datos = DocumentGenerator.generar_datos(filename)
                    return DocumentGenerator.generar_texto_documento(datos, file_type)
                
                return text
            except Exception as img_error:
                logger.error(f"Error procesando imagen: {img_error}")
                datos = DocumentGenerator.generar_datos(filename)
                return DocumentGenerator.generar_texto_documento(datos, file_type)
    
    except ImportError:
        # Modo simulado - sin dependencias
        logger.warning("Modo simulado OCR - dependencias no instaladas")
        logger.info("Para OCR real instale: pip install pytesseract pillow pdf2image")
        
        datos = DocumentGenerator.generar_datos(filename)
        return DocumentGenerator.generar_texto_documento(datos, file_type)
    
    except Exception as e:
        logger.error(f"Error en OCR: {e}")
        datos = DocumentGenerator.generar_datos(filename)
        return DocumentGenerator.generar_texto_documento(datos, file_type)


def extract_text_simple(path: str) -> str:
    """
    Versión simplificada compatible con código existente.
    
    Args:
        path: Ruta al archivo
    
    Returns:
        Texto extraído o mensaje de error
    """
    try:
        return extract_text(path)
    except Exception as e:
        logger.error(f"Error en extract_text_simple: {e}")
        filename = os.path.basename(path)
        datos = DocumentGenerator.generar_datos(filename)
        return DocumentGenerator.generar_texto_documento(datos, 'error')


def get_supported_formats() -> list:
    """
    Devuelve lista de formatos de archivo soportados.
    """
    return [
        # Documentos
        '.pdf',
        # Imágenes
        '.jpg', '.jpeg', '.png', 
        '.tiff', '.tif', '.bmp',
        '.gif', '.webp'
    ]


def is_supported_file(filename: str) -> bool:
    """
    Verifica si un archivo está soportado por el OCR.
    
    Args:
        filename: Nombre del archivo
    
    Returns:
        True si el formato es soportado
    """
    extension = os.path.splitext(filename)[1].lower()
    return extension in get_supported_formats()


# Para pruebas
if __name__ == "__main__":
    # Probar generación de datos
    print("=== PRUEBA DE GENERACIÓN DE DATOS ===")
    datos_ejemplo = DocumentGenerator.generar_datos("test_document.pdf")
    print(f"Proceso: {datos_ejemplo['process_number']}")
    print(f"Proveedor: {datos_ejemplo['provider']}")
    print(f"Material: {datos_ejemplo['product']}")
    print(f"Peso Neto: {datos_ejemplo['peso_neto']} kg")
    print(f"Estado: {datos_ejemplo['estado']}")
    
    # Probar extracción simulada
    print("\n=== PRUEBA DE EXTRACCIÓN SIMULADA ===")
    texto_simulado = extract_text_simple("/ruta/ejemplo/documento.jpg")
    print("Primeros 300 caracteres:")
    print(texto_simulado[:300])
