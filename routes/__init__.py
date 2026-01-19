# routes/__init__.py
from routes.dashboard_routes import dashboard_bp
from routes.auth_routes import auth_bp
from routes.inventory_routes import inventory_bp
from routes.warehouse2d_routes import warehouse2d_bp
from routes.bultos_routes import bultos_bp
from routes.alerts_routes import alerts_bp
from routes.technician_errors_routes import technician_errors_bp
from routes.equipos_routes import equipos_bp

# COMENTA TEMPORALMENTE los que causan problemas
# from routes.productividad_routes import productividad_bp  # Causa error
from routes.qr_routes import qr_bp
from routes.auditoria_routes import auditoria_bp
from routes.alertas_ai_routes import alertas_ai_bp
from routes.admin_roles_routes import admin_roles_bp
from routes.tasks_routes import tasks_bp

# IMPORTANTE: Cambia warehouse_bp por warehouse_documents_bp si usaste ese nombre
try:
    from routes.warehouse_documents import warehouse_documents_bp
except ImportError:
    # Si no existe, intenta con warehouse_bp
    try:
        from routes.warehouse_documents import warehouse_bp as warehouse_documents_bp
    except ImportError:
        # Crea un blueprint dummy
        from flask import Blueprint, jsonify
        warehouse_documents_bp = Blueprint('warehouse_documents', __name__)
        @warehouse_documents_bp.route('/')
        def dummy():
            return jsonify({'error': 'warehouse_documents module not properly configured'})
        print("⚠️  Usando blueprint dummy para warehouse_documents")

def register_blueprints(app):
    print("\n========== CARGANDO BLUEPRINTS ==========\n")

    # 👉 Rutas que sabemos que funcionan
    app.register_blueprint(auth_bp)
    print("✅ Cargado: auth")

    app.register_blueprint(dashboard_bp)
    print("✅ Cargado: dashboard")

    app.register_blueprint(inventory_bp)
    print("✅ Cargado: inventario")

    app.register_blueprint(warehouse2d_bp)
    print("✅ Cargado: warehouse2d")

    app.register_blueprint(bultos_bp)
    print("✅ Cargado: bultos")

    app.register_blueprint(alerts_bp)
    print("✅ Cargado: alertas")

    app.register_blueprint(technician_errors_bp)
    print("✅ Cargado: errores_tecnicos")

    app.register_blueprint(equipos_bp)
    print("✅ Cargado: equipos")

    # productividad_bp - COMENTADO TEMPORALMENTE
    # app.register_blueprint(productividad_bp)
    # print("⚠️  Cargado: productividad (modo dummy)")

    app.register_blueprint(qr_bp)
    print("✅ Cargado: qr")

    app.register_blueprint(auditoria_bp)
    print("✅ Cargado: auditoria")

    app.register_blueprint(alertas_ai_bp)
    print("✅ Cargado: alertas_ai")

    app.register_blueprint(admin_roles_bp)
    print("✅ Cargado: roles")
    
    app.register_blueprint(tasks_bp)
    print("✅ Cargado: tasks")

    # warehouse_documents
    app.register_blueprint(warehouse_documents_bp)
    print("✅ Cargado: warehouse_documents")

    print("\n========== BLUEPRINTS CARGADOS OK ==========\n")
