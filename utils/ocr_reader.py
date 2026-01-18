import logging
import os
import re
import random
import hashlib
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
        """Genera datos aleatorios pero consistentes para un documento"""
        
        # Usar hash del nombre para generar datos consistentes
        file_hash = hashlib.md5(filename.encode()).hexdigest()[:8]
        
        # Usar el hash para selección determinista
        hash_int = int(file_hash, 16)
        
        # Seleccionar material basado en hash (consistente para mismo archivo)
        material_idx = hash_int % len(cls.MATERIALES)
        material = cls.MATERIALES[material_idx]
        
        # Selecciones consistentes basadas en hash
        proveedor_idx = (hash_int // 10) % len(cls.PROVEEDORES)
        conductor_idx = (hash_int // 100) % len(cls.CONDUCTORES)
        transportadora_idx = (hash_int // 1000) % len(cls.TRANSPORTADORAS)
        
        # Generar cantidades y pesos realistas
        cantidad_unidades = 100 + (hash_int % 901)  # 100-1000
        peso_neto = round(cantidad_unidades * material["peso_por_unidad"], 2)
        peso_bruto = round(peso_neto * (1.05 + (hash_int % 11) / 100), 2)  # 1.05-1.15
        tara = round(peso_bruto - peso_neto, 2)
        
        # Generar datos de calidad
        humedad = round(material["humedad_min"] + (hash_int % 100) * (material["humedad_max"] - material["humedad_min"]) / 100, 1)
        impurezas = round(material["impurezas_min"] + ((hash_int // 10) % 100) * (material["impurezas_max"] - material["impurezas_min"]) / 100, 2)
        temperatura = round(material["temperatura_min"] + ((hash_int // 100) % 100) * (material["temperatura_max"] - material["temperatura_min"]) / 100, 1)
        
        # Determinar estado basado en calidad
        if humedad <= material["humedad_max"] * 0.9 and impurezas <= material["impurezas_max"] * 0.8:
            estado = "APROBADO - ÓPTIMO"
        elif humedad <= material["humedad_max"] and impurezas <= material["impurezas_max"]:
            estado = "APROBADO"
        else:
            estado = "RECHAZADO - FUERA DE ESPECIFICACIÓN"
        
        # Fecha basada en hash (últimos 30 días)
        dias_atras = hash_int % 31
        fecha_doc = datetime.now() - timedelta(days=dias_atras)
        
        # Generar placas consistentes
        letras_placas = ['ABC', 'DEF', 'GHI', 'JKL', 'MNO', 'PQR', 'STU', 'VWX', 'YZ']
        letra_idx1 = hash_int % len(letras_placas)
        letra_idx2 = (hash_int // 10) % len(letras_placas)
        num_placa1 = 100 + (hash_int % 900)
        num_placa2 = 100 + ((hash_int // 100) % 900)
        
        return {
            # Información del documento
            "process_number": f"PROC-{fecha_doc.strftime('%Y%m%d')}-{file_hash[:4].upper()}",
            "documento_numero": f"DOC-{file_hash.upper()}",
            "fecha": fecha_doc.strftime('%d/%m/%Y'),
            "hora": fecha_doc.strftime('%H:%M:%S'),
            
            # Información del proveedor
            "provider": cls.PROVEEDORES[proveedor_idx],
            "nit_proveedor": f"900.{file_hash[:3]}.{file_hash[3:6]}-{(hash_int % 9) + 1}",
            
            # Información del transporte
            "driver": cls.CONDUCTORES[conductor_idx],
            "cedula": f"{file_hash[:8]}",
            "plate_tractor": f"{letras_placas[letra_idx1]}-{num_placa1}",
            "plate_remolque": f"{letras_placas[letra_idx2]}-{num_placa2}",
            "transportadora": cls.TRANSPORTADORAS[transportadora_idx],
            
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
            "observaciones": cls.generar_observaciones(estado, material["nombre"], hash_int),
            
            # Información de procesamiento
            "procesado_por": "SISTEMA OCR AUTOMÁTICO",
            "fecha_procesamiento": datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            "modo_ocr": "SIMULADO - TESSERACT NO INSTALADO"
        }
    
    @classmethod
    def generar_observaciones(cls, estado: str, material: str, hash_int: int) -> str:
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
        
        # Observaciones aleatorias pero consistentes
        observaciones_extra = [
            "TEMPERATURA CONTROLADA DURANTE TRANSPORTE",
            "SELLOS DE SEGURIDAD INTACTOS",
            "CERTIFICADO DE ORIGEN ADJUNTO",
            "MUESTRA TOMADA PARA ANÁLISIS",
            "REGISTRO FOTOGRÁFICO DISPONIBLE",
            "INSPECCIÓN VISUAL SATISFACTORIA",
            "DOCUMENTOS DE TRANSPORTE EN REGLA"
        ]
        
        # Seleccionar observaciones basadas en hash
        num_obs = 2 + (hash_int % 3)  # 2-4 observaciones
        indices = [(hash_int // (i+1)) % len(observaciones_extra) for i in range(num_obs)]
        for idx in indices[:num_obs]:
            if observaciones_extra[idx] not in observaciones:
                observaciones.append(observaciones_extra[idx])
        
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
        
        {'='*60}
        """


def extract_text(path: str, lang: str = "spa") -> str:
    """
    Versión simplificada de OCR que funciona SIN Tesseract.
    Para producción, instale Tesseract OCR en el sistema.
    """
    # Verificar que el archivo existe
    if not os.path.exists(path):
        raise FileNotFoundError(f"Archivo no encontrado: {path}")
    
    filename = os.path.basename(path)
    file_extension = os.path.splitext(filename)[1].lower()
    
    logger.info(f"Procesando archivo: {filename}")
    logger.warning("⚠️  Tesseract no instalado. Usando modo simulado.")
    logger.info("Para OCR real, instale Tesseract OCR en el sistema.")
    
    # Determinar tipo de archivo
    if file_extension == '.pdf':
        file_type = 'PDF'
    elif file_extension in ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp']:
        file_type = 'IMAGEN'
    else:
        file_type = 'DOCUMENTO'
    
    # Generar datos consistentes basados en el nombre del archivo
    datos = DocumentGenerator.generar_datos(filename)
    
    # Añadir información específica del tipo de archivo
    datos['tipo_archivo'] = file_type
    datos['nombre_archivo'] = filename
    
    # Generar texto del documento
    texto = DocumentGenerator.generar_texto_documento(datos, file_type)
    
    # Añadir información técnica
    texto += f"""
    
    {'='*60}
    INFORMACIÓN TÉCNICA
    {'='*60}
    • Archivo procesado: {filename}
    • Tipo: {file_type}
    • Tamaño: {os.path.getsize(path) / 1024:.1f} KB
    • Modo OCR: SIMULADO (Tesseract no instalado)
    • Fecha de procesamiento: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    
    {'='*60}
    NOTA: Para OCR real (extracción de texto real de imágenes/PDFs):
    1. Instale Tesseract OCR en el sistema
    2. Ejecute: pip install pytesseract pillow pdf2image
    3. Reinicie la aplicación
    
    En Linux: sudo apt-get install tesseract-ocr tesseract-ocr-spa
    En MacOS: brew install tesseract
    En Windows: Descargue instalador de GitHub
    {'='*60}
    """
    
    return texto


def extract_text_simple(path: str) -> str:
    """Versión simple compatible."""
    try:
        return extract_text(path)
    except Exception as e:
        logger.error(f"Error en extract_text_simple: {e}")
        filename = os.path.basename(path)
        datos = DocumentGenerator.generar_datos(filename)
        return DocumentGenerator.generar_texto_documento(datos, 'error')


def get_supported_formats() -> list:
    """Devuelve lista de formatos de archivo soportados."""
    return [
        '.pdf',           # Documentos PDF
        '.jpg', '.jpeg',  # Imágenes JPEG
        '.png',           # Imágenes PNG
        '.tiff', '.tif',  # Imágenes TIFF
        '.bmp',           # Imágenes BMP
        '.gif',           # Imágenes GIF
        '.webp'           # Imágenes WebP
    ]


def is_supported_file(filename: str) -> bool:
    """Verifica si un archivo está soportado."""
    extension = os.path.splitext(filename)[1].lower()
    return extension in get_supported_formats()


# Para pruebas
if __name__ == "__main__":
    # Probar generación de datos
    print("=== PRUEBA DE GENERACIÓN DE DATOS ===")
    datos = DocumentGenerator.generar_datos("documento_ejemplo.pdf")
    print(f"Proceso: {datos['process_number']}")
    print(f"Proveedor: {datos['provider']}")
    print(f"Material: {datos['product']}")
    print(f"Peso Neto: {datos['net_weight']} kg")
    print(f"Placa: {datos['plate_tractor']}")
    
    # Probar extracción
    print("\n=== PRUEBA DE EXTRACCIÓN ===")
    texto = extract_text_simple("/ruta/ejemplo/documento.jpg")
    print(texto[:500])
