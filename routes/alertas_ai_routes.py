# routes/alertas_ai_routes.py - VERSIÓN CORREGIDA

from flask import Blueprint, render_template, request, jsonify, Response, current_app
from flask_login import login_required
from datetime import datetime, timedelta
import csv
from io import StringIO

# IMPORTANTE: NO importes 'app' o 'db' directamente aquí
# Usa 'current_app' y 'db' de forma diferida

alertas_ai_bp = Blueprint("alertas_ai", __name__, url_prefix="/alertas-ai")

# ===========================================
# FUNCIÓN PARA OBTENER DB SIN IMPORT CIRCULAR
# ===========================================
def get_db():
    """Obtiene la instancia de db de forma segura"""
    from app import db
    return db

# ===========================================
# LISTADO DE ALERTAS GENERADAS POR IA
# ===========================================
@alertas_ai_bp.route("/listado")
@login_required
def listado_ai():
    try:
        # Importar dentro de la función para evitar circular
        from models.alertas_ai import AlertaIA
        
        # Obtener parámetros de filtro
        nivel = request.args.get('nivel', '').lower()
        categoria = request.args.get('categoria', '')
        desde = request.args.get('desde', '')
        hasta = request.args.get('hasta', '')
        q = request.args.get('q', '').lower()

        # Construir consulta base
        query = AlertaIA.query

        # Aplicar filtros
        if nivel and nivel != 'todos':
            query = query.filter(AlertaIA.nivel.ilike(f"%{nivel}%"))
        
        if categoria:
            query = query.filter(AlertaIA.categoria.ilike(f"%{categoria}%"))
        
        if desde:
            try:
                desde_date = datetime.strptime(desde, "%Y-%m-%d")
                query = query.filter(AlertaIA.fecha >= desde_date)
            except ValueError:
                pass
        
        if hasta:
            try:
                hasta_date = datetime.strptime(hasta, "%Y-%m-%d")
                hasta_date = hasta_date + timedelta(days=1)
                query = query.filter(AlertaIA.fecha <= hasta_date)
            except ValueError:
                pass
        
        if q:
            query = query.filter(
                AlertaIA.descripcion.ilike(f"%{q}%") | 
                AlertaIA.categoria.ilike(f"%{q}%")
            )

        # Ordenar por fecha descendente
        alertas_bd = query.order_by(AlertaIA.fecha.desc()).all()

        # Preparar datos para la vista
        alertas = []
        for a in alertas_bd:
            alertas.append({
                "id": a.id,
                "categoria": a.categoria,
                "descripcion": a.descripcion,
                "nivel": a.nivel.capitalize() if a.nivel else "No especificado",
                "fecha": a.fecha.strftime("%Y-%m-%d %H:%M") if a.fecha else "Sin fecha",
                "origen": getattr(a, 'origen', 'Sistema IA'),
                "usuario": getattr(a, 'usuario_nombre', None)
            })

        # Estadísticas
        total_alertas = len(alertas)
        alertas_criticas = len([a for a in alertas if a['nivel'].lower() in ['alto', 'critical', 'crítico']])
        ultima_alerta = alertas[0]['fecha'] if alertas else "N/A"

        # Renderizar vista
        return render_template(
            "alertas_ai/listado_ai.html", 
            alertas=alertas,
            total_alertas=total_alertas,
            alertas_criticas=alertas_criticas,
            ultima_alerta=ultima_alerta
        )

    except Exception as e:
        # Usar current_app para logging
        current_app.logger.error(f"Error en listado_ai: {str(e)}")
        
        # En caso de error, mostrar vista vacía
        return render_template(
            "alertas_ai/listado_ai.html", 
            alertas=[],
            total_alertas=0,
            alertas_criticas=0,
            ultima_alerta="N/A"
        )
