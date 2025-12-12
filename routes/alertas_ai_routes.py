# routes/alertas_ai_routes.py

from flask import Blueprint, render_template
from flask_login import login_required

# Import correcto para Railway
from models.alertas_ai import AlertaIA

alertas_ai_bp = Blueprint("alertas_ai", __name__, url_prefix="/alertas-ai")


# ===========================================
# LISTADO DE ALERTAS GENERADAS POR IA
# ===========================================
@alertas_ai_bp.route("/listado")
@login_required
def listado_ai():

    # Obtener alertas reales desde la base de datos
    alertas_bd = AlertaIA.query.order_by(AlertaIA.fecha.desc()).all()

    alertas = []

    # Si existen alertas reales, formatearlas
    if alertas_bd:
        for a in alertas_bd:
            alertas.append({
                "categoria": a.categoria,
                "descripcion": a.descripcion,
                "nivel": a.nivel.capitalize(),
                "fecha": a.fecha.strftime("%Y-%m-%d %H:%M")
            })
    else:
        # Datos de ejemplo temporales si la BD está vacía
        alertas = [
            {
                "categoria": "Predicción de Stock Crítico",
                "descripcion": "Material M00123 está próximo a agotarse.",
                "nivel": "Alto",
                "fecha": "2025-12-01 08:45",
            },
            {
                "categoria": "Anomalía en Inventario",
                "descripcion": "Variación inesperada detectada en material M00421.",
                "nivel": "Medio",
                "fecha": "2025-12-01 09:10",
            },
            {
                "categoria": "Uso Irregular de Bultos",
                "descripcion": "Patrón anómalo detectado en bulto B099.",
                "nivel": "Alto",
                "fecha": "2025-11-30 17:22",
            },
        ]

    # Renderizar vista
    return render_template("alertas_ai/listado_ai.html", alertas=alertas)

