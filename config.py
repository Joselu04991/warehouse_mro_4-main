import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = "clave_super_secreta_mro_2025"

    # Base de datos en archivo local
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'warehouse_mro_v2.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Carpetas internas
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    REPORT_FOLDER = os.path.join(BASE_DIR, "static", "reports")
