# routes/alertas_ai_routes.py

from flask import Blueprint, render_template, request, jsonify, Response
from flask_login import login_required
from datetime import datetime, timedelta
import csv
from io import StringIO

# Importar desde tu aplicación
from app import db, app  # Ajusta estos imports según tu estructura
from models.alertas_ai import AlertaIA

alertas_ai_bp = Blueprint("alertas_ai", __name__, url_prefix="/alertas-ai")


# ===========================================
# LISTADO DE ALERTAS GENERADAS POR IA
# ===========================================
@alertas_ai_bp.route("/listado")
@login_required
def listado_ai():
    try:
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
                # Añadir un día para incluir todo el día
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

        # Obtener estadísticas para el dashboard
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
        # Log del error usando current_app si app no está disponible
        from flask import current_app
        current_app.logger.error(f"Error en listado_ai: {str(e)}")
        
        # En caso de error, mostrar vista vacía
        return render_template(
            "alertas_ai/listado_ai.html", 
            alertas=[],
            total_alertas=0,
            alertas_criticas=0,
            ultima_alerta="N/A",
            error_message=f"Error al cargar alertas: {str(e)}"
        )


# ===========================================
# API PARA OBTENER ALERTAS (AJAX)
# ===========================================
@alertas_ai_bp.route("/api/alertas")
@login_required
def api_alertas():
    try:
        # Obtener parámetros de filtro
        nivel = request.args.get('nivel', '')
        categoria = request.args.get('categoria', '')
        limit = request.args.get('limit', 50, type=int)

        # Construir consulta
        query = AlertaIA.query

        if nivel:
            query = query.filter_by(nivel=nivel)
        
        if categoria:
            query = query.filter_by(categoria=categoria)

        # Obtener últimas alertas
        alertas_bd = query.order_by(AlertaIA.fecha.desc()).limit(limit).all()

        # Formatear respuesta JSON
        alertas_json = []
        for a in alertas_bd:
            alertas_json.append({
                "id": a.id,
                "categoria": a.categoria,
                "descripcion": a.descripcion,
                "nivel": a.nivel,
                "fecha": a.fecha.isoformat() if a.fecha else None,
                "origen": getattr(a, 'origen', 'Sistema IA')
            })

        return jsonify({
            "success": True,
            "alertas": alertas_json,
            "total": len(alertas_json)
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ===========================================
# MARCAR ALERTA COMO LEÍDA/CERRADA
# ===========================================
@alertas_ai_bp.route("/api/alerta/<int:alerta_id>/toggle", methods=["POST"])
@login_required
def toggle_alerta(alerta_id):
    try:
        alerta = AlertaIA.query.get_or_404(alerta_id)
        
        # Cambiar estado (si tu modelo tiene campo estado)
        if hasattr(alerta, 'estado'):
            alerta.estado = 'cerrado' if alerta.estado == 'activo' else 'activo'
            db.session.commit()
            
            return jsonify({
                "success": True,
                "estado": alerta.estado,
                "mensaje": f"Alerta {alerta_id} marcada como {alerta.estado}"
            })
        else:
            return jsonify({
                "success": False,
                "error": "El modelo no tiene campo estado"
            }), 400

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ===========================================
# ESTADÍSTICAS DE ALERTAS
# ===========================================
@alertas_ai_bp.route("/api/estadisticas")
@login_required
def estadisticas_alertas():
    try:
        # Obtener conteos por nivel
        niveles = db.session.query(
            AlertaIA.nivel, 
            db.func.count(AlertaIA.id).label('total')
        ).group_by(AlertaIA.nivel).all()

        # Obtener últimas 24 horas
        ultimas_24h = AlertaIA.query.filter(
            AlertaIA.fecha >= datetime.now() - timedelta(days=1)
        ).count()

        # Obtener por categoría
        categorias = db.session.query(
            AlertaIA.categoria, 
            db.func.count(AlertaIA.id).label('total')
        ).group_by(AlertaIA.categoria).all()

        return jsonify({
            "success": True,
            "estadisticas": {
                "por_nivel": dict(niveles),
                "ultimas_24h": ultimas_24h,
                "por_categoria": dict(categorias),
                "total": db.session.query(db.func.count(AlertaIA.id)).scalar()
            }
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ===========================================
# GENERAR REPORTE CSV
# ===========================================
@alertas_ai_bp.route("/exportar-csv")
@login_required
def exportar_csv():
    try:
        # Obtener todas las alertas
        alertas_bd = AlertaIA.query.order_by(AlertaIA.fecha.desc()).all()
        
        # Crear contenido CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # Encabezados
        writer.writerow(['ID', 'Categoría', 'Descripción', 'Nivel', 'Fecha', 'Origen'])
        
        # Datos
        for a in alertas_bd:
            writer.writerow([
                a.id,
                a.categoria,
                a.descripcion,
                a.nivel,
                a.fecha.strftime("%Y-%m-%d %H:%M") if a.fecha else "",
                getattr(a, 'origen', '')
            ])
        
        # Preparar respuesta
        output.seek(0)
        
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-disposition": f"attachment; filename=alertas_ia_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
        )

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
