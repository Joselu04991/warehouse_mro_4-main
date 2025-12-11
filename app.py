from flask import Flask, redirect, url_for, jsonify
from flask_login import LoginManager
from config import Config
from models import db
from models.user import User
from routes import register_blueprints
import os

# =====================================================
# LOGIN MANAGER
# =====================================================
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# =====================================================
# CREATE_APP
# =====================================================
def create_app():
    app = Flask(__name__)
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
