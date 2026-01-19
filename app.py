# app.py - VERSIÓN COMPLETA CON INSTALACIÓN DE TESSERACT
from flask import Flask, redirect, url_for, jsonify
from flask_login import LoginManager
from config import Config
from models import db
from models.user import User
from routes import register_blueprints
import os
import subprocess
import sys

# =====================================================
# LOGIN MANAGER
# =====================================================
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def install_tesseract_if_needed():
    """Instala Tesseract si no está disponible"""
    print("\n=== VERIFICANDO/INSTALANDO TESSERACT OCR ===")
    
    try:
        # Verificar si tesseract ya está instalado
        result = subprocess.run(['which', 'tesseract'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Tesseract ya instalado en: {result.stdout.strip()}")
            
            # Verificar versión
            version = subprocess.run(['tesseract', '--version'], 
                                   capture_output=True, text=True)
            if version.stdout:
                print(f"📊 Versión: {version.stdout.split()[1]}")
            return True
    except:
        pass
    
    print("❌ Tesseract no encontrado. Intentando instalar...")
    
    try:
        # Instalar Tesseract usando apt (Railway usa Ubuntu)
        print("📦 Instalando tesseract-ocr y tesseract-ocr-spa...")
        
        # Actualizar repositorios primero
        subprocess.run(['apt-get', 'update', '-y'], 
                      capture_output=True, text=True)
        
        # Instalar Tesseract
        install_cmd = ['apt-get', 'install', '-y', 
                      'tesseract-ocr', 'tesseract-ocr-spa', 'poppler-utils']
        result = subprocess.run(install_cmd, 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Tesseract instalado exitosamente")
            
            # Verificar instalación
            verify = subprocess.run(['tesseract', '--version'], 
                                  capture_output=True, text=True)
            if verify.stdout:
                print(f"📊 Tesseract listo: {verify.stdout.split()[1]}")
            return True
        else:
            print(f"❌ Error instalando Tesseract: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Excepción instalando Tesseract: {e}")
        return False


def check_ocr_dependencies():
    """Verifica todas las dependencias de OCR"""
    print("\n=== VERIFICANDO DEPENDENCIAS OCR ===")
    
    dependencies = {
        'tesseract': False,
        'python_packages': {}
    }
    
    # 1. Verificar Tesseract
    try:
        result = subprocess.run(['which', 'tesseract'], 
                              capture_output=True, text=True)
        dependencies['tesseract'] = result.returncode == 0
        if dependencies['tesseract']:
            print(f"✅ Tesseract: {result.stdout.strip()}")
        else:
            print("❌ Tesseract: NO INSTALADO")
    except:
        print("❌ Tesseract: ERROR VERIFICANDO")
    
    # 2. Verificar paquetes Python
    packages = ['pytesseract', 'PIL', 'fitz', 'pandas', 'openpyxl']
    for pkg in packages:
        try:
            if pkg == 'PIL':
                from PIL import Image
                dependencies['python_packages'][pkg] = 'OK'
            elif pkg == 'fitz':
                import fitz
                dependencies['python_packages'][pkg] = 'OK'
            else:
                __import__(pkg)
                dependencies['python_packages'][pkg] = 'OK'
            print(f"✅ {pkg}: OK")
        except ImportError as e:
            dependencies['python_packages'][pkg] = f'ERROR: {e}'
            print(f"❌ {pkg}: NO INSTALADO - {e}")
    
    return dependencies


# =====================================================
# CREATE_APP
# =====================================================
def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # =====================================================
    # INSTALAR TESSERACT AL INICIAR (SI ES NECESARIO)
    # =====================================================
    # Solo intentar instalar en Railway (no en desarrollo local)
    if os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('RAILWAY_GITHUB_DEPLOYMENT'):
        print("\n🚀 EJECUTANDO EN RAILWAY - VERIFICANDO TESSERACT")
        tesseract_installed = install_tesseract_if_needed()
        
        if not tesseract_installed:
            print("⚠️  ADVERTENCIA: Tesseract no pudo instalarse automáticamente")
            print("⚠️  El OCR no funcionará para PDFs/imágenes")
    else:
        print("\n💻 EJECUTANDO EN LOCAL - VERIFICANDO TESSERACT")
        check_ocr_dependencies()

    # =====================================================
    # CREAR CARPETAS NECESARIAS
    # =====================================================
    REQUIRED_DIRS = [
        "uploads",
        "uploads/inventory",
        "uploads/history",
        "uploads/bultos",
        "reports",
    ]

    for folder in REQUIRED_DIRS:
        path = os.path.join(app.root_path, folder)
        try:
            os.makedirs(path, exist_ok=True)
            print(f"✔ Carpeta verificada: {path}")
        except Exception as e:
            print(f"✖ ERROR creando carpeta {path}: {e}")

    # =====================================================
    # INICIALIZAR EXTENSIONES
    # =====================================================
    db.init_app(app)
    login_manager.init_app(app)

    # Registrar Blueprints
    register_blueprints(app)

    # =====================================================
    # FIX GLOBAL — DESACTIVA COMPRESIÓN (EVITA EXCEL CORRUPTOS)
    # =====================================================
    @app.after_request
    def disable_compression(response):
        response.headers["Content-Encoding"] = "identity"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
        return response

    # =====================================================
    # FORMATEO DE FECHA
    # =====================================================
    @app.template_filter("format_fecha")
    def format_fecha(value):
        try:
            return value.strftime("%d/%m/%Y %H:%M")
        except:
            return value

    # =====================================================
    # RUTA RAIZ → LOGIN
    # =====================================================
    @app.route("/")
    def index():
        return redirect(url_for("auth.login"))

    # =====================================================
    # ENDPOINT PARA VERIFICAR OCR
    # =====================================================
    @app.route("/api/check-ocr")
    def check_ocr_status():
        """Endpoint para verificar estado de OCR"""
        dependencies = check_ocr_dependencies()
        
        # Probar OCR simple si está disponible
        ocr_test = "No probado"
        if dependencies['tesseract'] and 'pytesseract' in dependencies['python_packages']:
            try:
                import pytesseract
                from PIL import Image, ImageDraw
                import io
                
                img = Image.new('RGB', (200, 50), color='white')
                d = ImageDraw.Draw(img)
                d.text((10, 10), "OCR TEST 123", fill='black')
                
                text = pytesseract.image_to_string(img, lang='spa')
                ocr_test = f"OK - Reconoció: {text.strip()}" if text.strip() else "OK - Sin texto"
            except Exception as e:
                ocr_test = f"ERROR: {e}"
        
        return jsonify({
            'environment': 'Railway' if os.environ.get('RAILWAY_ENVIRONMENT') else 'Local',
            'dependencies': dependencies,
            'ocr_test': ocr_test,
            'instructions': 'Si Tesseract no está instalado, Railway necesita configurarse manualmente'
        })

    # =====================================================
    # GLOBAL ERROR HANDLER (PRODUCCIÓN)
    # =====================================================
    @app.errorhandler(500)
    def server_error(e):
        print("❌ ERROR 500:", e)
        return jsonify({"error": "Error interno del servidor"}), 500

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Ruta no encontrada"}), 404

    # =====================================================
    # CREAR TABLAS Y OWNER
    # =====================================================
    with app.app_context():
        print("\n>>> Creando tablas si no existen...")
        db.create_all()
        db.session.commit()
        print(">>> Tablas listas.\n")

        # OWNER predeterminado
        OWNER_EMAIL = "jose.castillo@sider.com.pe"
        OWNER_USERNAME = "JCASTI15"
        OWNER_PASSWORD = "Admin123#"

        owner = User.query.filter_by(email=OWNER_EMAIL).first()

        if not owner:
            print(">>> Creando usuario OWNER...")
            new_owner = User(
                username=OWNER_USERNAME,
                email=OWNER_EMAIL,
                role="owner",
                status="active",
                email_confirmed=True,
            )
            new_owner.set_password(OWNER_PASSWORD)

            db.session.add(new_owner)
            db.session.commit()

            print(">>> OWNER creado correctamente.")
        else:
            owner.role = "owner"
            owner.email_confirmed = True
            db.session.commit()
            print(">>> OWNER verificado y activo.")

    return app


# =====================================================
# EJECUTAR EN LOCAL
# =====================================================
if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
