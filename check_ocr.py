# check_ocr.py
import subprocess
import sys

print("=== VERIFICANDO INSTALACIÓN DE TESSERACT ===")

# 1. Verificar sistema
print("\n1. Sistema operativo:")
try:
    result = subprocess.run(['lsb_release', '-a'], capture_output=True, text=True)
    print(result.stdout)
except:
    print("No se pudo obtener info del sistema")

# 2. Verificar si tesseract está instalado
print("\n2. Buscando Tesseract...")
try:
    # Buscar en PATH
    result = subprocess.run(['which', 'tesseract'], capture_output=True, text=True)
    print(f"Tesseract encontrado en: {result.stdout.strip()}")
    
    # Ver versión
    version = subprocess.run(['tesseract', '--version'], capture_output=True, text=True)
    print(f"Versión Tesseract:\n{version.stdout}")
    
except FileNotFoundError:
    print("❌ Tesseract NO encontrado en PATH")
    print("\n3. Buscando en ubicaciones comunes...")
    
    # Buscar en ubicaciones comunes
    common_paths = [
        '/usr/bin/tesseract',
        '/usr/local/bin/tesseract',
        '/bin/tesseract',
        '/app/.apt/usr/bin/tesseract'
    ]
    
    for path in common_paths:
        import os
        if os.path.exists(path):
            print(f"✅ Encontrado en: {path}")
            break
    else:
        print("❌ No encontrado en ninguna ubicación común")

# 3. Verificar paquetes instalados
print("\n4. Paquetes instalados relacionados con OCR:")
try:
    result = subprocess.run(['dpkg', '-l', '|', 'grep', 'tesseract'], 
                          shell=True, capture_output=True, text=True)
    print(result.stdout if result.stdout else "No hay paquetes tesseract")
except:
    print("No se pudo listar paquetes")

print("\n=== FIN DE VERIFICACIÓN ===")
