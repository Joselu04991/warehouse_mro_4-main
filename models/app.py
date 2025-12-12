from flask import Flask, redirect, url_for
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
    # FIX PARA CARPETAS NECESARIAS
    # =====================================================
    REQUIRED_DIRS = [
        "uploads",
        "uploads/inventory",
        "uploads/history",
        "uploads/bultos",
        "reports",
    ]

    for d in REQUIRED_DIRS:
        path = os.path.join(app.root_path, d)
        try:
            os.makedirs(path, exist_ok=True)
            print(f"✔ Carpeta disponible: {path}")
        except Exception as e:
            print(f"✖ ERROR creando carpeta {path}: {e}")

    # =====================================================
    # Inicializar extensiones
    # =====================================================
    db.init_app(app)
    login_manager.init_app(app)

    # Registrar rutas (blueprints)
    register_blueprints(app)

    # =====================================================
    # FILTRO DE FECHA
    # =====================================================
    @app.template_filter("format_fecha")
    def format_fecha(value):
        try:
            return value.strftime("%d/%m/%Y %H:%M")
        except Exception:
            return value

    # =====================================================
    # FIX GLOBAL PARA ARCHIVOS EXCEL EN RAILWAY
    # =====================================================
    @app.after_request
    def fix_excel_download(response):
        # Evita compresión GZIP que daña archivos Excel
        response.headers["Content-Encoding"] = "identity"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    # =====================================================
    # RUTA DE INICIO
    # =====================================================
    @app.route("/")
    def index():
        return redirect(url_for("auth.login"))

    # =====================================================
    # CREAR TABLAS Y USUARIO OWNER
    # =====================================================
    with app.app_context():
        print("\n>>> Creando tablas si no existen...")
        db.create_all()
        db.session.commit()
        print(">>> Tablas listas.\n")

        owner_email = "jose.castillo@sider.com.pe"
        owner_username = "JCASTI15"
        owner_password = "Admin123#"

        owner = User.query.filter_by(email=owner_email).first()

        if not owner:
            print(">>> Creando usuario OWNER...")
            new_owner = User(
                username=owner_username,
                email=owner_email,
                role="owner",
                status="active",
                email_confirmed=True,
            )
            new_owner.set_password(owner_password)
            db.session.add(new_owner)
            db.session.commit()
            print(">>> OWNER creado correctamente.")
        else:
            owner.role = "owner"
            owner.email_confirmed = True
            db.session.commit()
            print(">>> OWNER verificado.")

    return app


# =====================================================
# EJECUTAR LOCAL
# =====================================================
if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
