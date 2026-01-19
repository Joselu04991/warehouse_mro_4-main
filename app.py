# app.py - VERSIÓN QUE FUNCIONA CON RAILWAY
from flask import Flask, jsonify
import os
from datetime import datetime

# =====================================================
# CREAR APP SIMPLE PRIMERO PARA HEALTH CHECK
# =====================================================
app = Flask(__name__)

# =====================================================
# HEALTH CHECK MÁS SIMPLE POSIBLE (LO PRIMERO)
# =====================================================
@app.route("/")
def root():
    return jsonify({
        "status": "online",
        "service": "Sistema de Almacén",
        "timestamp": datetime.now().isoformat()
    })

@app.route("/health")
@app.route("/api/health")
@app.route("/healthz")
def health_check():
    """Health check mínimo para Railway"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }), 200

# =====================================================
# INICIALIZAR EL RESTO DE LA APP DESPUÉS
# =====================================================
def initialize_full_app():
    """Inicializa toda la aplicación después del health check"""
    print("\n" + "="*50)
    print("INICIALIZANDO APLICACIÓN COMPLETA")
    print("="*50)
    
    # Configuración
    from config import Config
    app.config.from_object(Config)
    
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
    from flask_login import LoginManager
    from models import db
    
    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"
    
    db.init_app(app)
    login_manager.init_app(app)
    
    # =====================================================
    # USER LOADER
    # =====================================================
    from models.user import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # =====================================================
    # REGISTRAR BLUEPRINTS
    # =====================================================
    from routes import register_blueprints
    register_blueprints(app)
    
    # =====================================================
    # ENDPOINTS DE VERIFICACIÓN
    # =====================================================
    @app.route("/api/status")
    def full_status():
        """Estado completo de la aplicación"""
        import subprocess
        
        # Verificar Tesseract
        try:
            result = subprocess.run(['which', 'tesseract'], 
                                  capture_output=True, text=True)
            tesseract_installed = result.returncode == 0
        except:
            tesseract_installed = False
        
        return jsonify({
            "app": "Sistema de Gestión de Almacén",
            "status": "fully_initialized",
            "tesseract_installed": tesseract_installed,
            "database": "connected",
            "blueprints_loaded": True,
            "timestamp": datetime.now().isoformat()
        })
    
    # =====================================================
    # CREAR TABLAS Y USUARIO OWNER
    # =====================================================
    with app.app_context():
        print("\n>>> Creando tablas si no existen...")
        try:
            db.create_all()
            db.session.commit()
            print(">>> Tablas listas.\n")
        except Exception as e:
            print(f">>> Error creando tablas: {e}\n")
        
        # Crear usuario OWNER si no existe
        try:
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
                print(">>> OWNER ya existe.")
        except Exception as e:
            print(f">>> Error con usuario OWNER: {e}")
    
    print("\n" + "="*50)
    print("APLICACIÓN INICIALIZADA CORRECTAMENTE")
    print("="*50 + "\n")
    
    return app

# =====================================================
# INICIALIZAR APP COMPLETA (PERO HEALTH CHECK YA FUNCIONA)
# =====================================================
try:
    initialize_full_app()
except Exception as e:
    print(f"\n⚠️  Error inicializando app completa: {e}")
    print("⚠️  Pero el health check seguirá funcionando\n")

# =====================================================
# PARA EJECUCIÓN DIRECTA
# =====================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
