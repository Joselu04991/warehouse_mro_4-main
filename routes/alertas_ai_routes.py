# routes/alertas_ai_routes.py
# VERSIÓN CORREGIDA - SIN IMPORTS CIRCULARES

from flask import Blueprint, render_template, request, jsonify, Response, current_app
from flask_login import login_required
from datetime import datetime, timedelta
import csv
from io import StringIO

# Crear blueprint
alertas_ai_bp = Blueprint("alertas_ai", __name__, url_prefix="/alertas-ai")

# ===========================================
# FUNCIONES AUXILIARES (Para evitar imports circulares)
# ===========================================
def _get_alerta_model():
    """Obtiene el modelo AlertaIA de forma segura"""
    from models.alertas_ai import AlertaIA
    return AlertaIA

def _get_db():
    """Obtiene la instancia de db de forma segura"""
    from app import db
    return db

def _format_alerta(alerta):
    """Formatea una alerta para la vista"""
    return {
        "id": alerta.id,
        "categoria": alerta.categoria or "Sin categoría",
        "descripcion": alerta.descripcion or "Sin descripción",
        "nivel": alerta.nivel.capitalize() if alerta.nivel else "No especificado",
        "fecha": alerta.fecha.strftime("%Y-%m-%d %H:%M") if alerta.fecha else "Sin fecha",
        "origen": getattr(alerta, 'origen', 'Sistema IA'),
        "usuario": getattr(alerta, 'usuario_nombre', None),
        "estado": getattr(alerta, 'estado', 'activo')
    }

# ===========================================
# LISTADO DE ALERTAS GENERADAS POR IA
# ===========================================
@alertas_ai_bp.route("/listado")
@login_required
def listado_ai():
    try:
        # Obtener modelo de forma segura
        AlertaIA = _get_alerta_model()
        
        # Obtener parámetros de filtro
        nivel = request.args.get('nivel', '').lower()
        categoria = request.args.get('categoria', '')
        desde = request.args.get('desde', '')
        hasta = request.args.get('hasta', '')
        q = request.args.get('q', '').lower()
        
        # Construir consulta base
        query = AlertaIA.query
        
        # Aplicar filtros
        if nivel and nivel != 'todos' and nivel != '':
            query = query.filter(AlertaIA.nivel.ilike(f"%{nivel}%"))
        
        if categoria and categoria != '':
            query = query.filter(AlertaIA.categoria.ilike(f"%{categoria}%"))
        
        if desde:
            try:
                desde_date = datetime.strptime(desde, "%Y-%m-%d")
                query = query.filter(AlertaIA.fecha >= desde_date)
            except ValueError:
                current_app.logger.warning(f"Fecha 'desde' inválida: {desde}")
        
        if hasta:
            try:
                hasta_date = datetime.strptime(hasta, "%Y-%m-%d")
                hasta_date = hasta_date + timedelta(days=1)
                query = query.filter(AlertaIA.fecha <= hasta_date)
            except ValueError:
                current_app.logger.warning(f"Fecha 'hasta' inválida: {hasta}")
        
        if q and q != '':
            query = query.filter(
                AlertaIA.descripcion.ilike(f"%{q}%") | 
                AlertaIA.categoria.ilike(f"%{q}%")
            )
        
        # Ordenar por fecha descendente
        alertas_bd = query.order_by(AlertaIA.fecha.desc()).all()
        
        # Formatear alertas
        alertas = [_format_alerta(a) for a in alertas_bd]
        
        # Calcular estadísticas
        total_alertas = len(alertas)
        alertas_criticas = len([a for a in alertas if a['nivel'].lower() in ['alto', 'critical', 'crítico']])
        ultima_alerta = alertas[0]['fecha'] if alertas else "N/A"
        
        # Renderizar vista
        return render_template(
            "alertas_ai/listado_ai.html",
            alertas=alertas,
            total_alertas=total_alertas,
            alertas_criticas=alertas_criticas,
            ultima_alerta=ultima_alerta,
            filtros={
                'nivel': request.args.get('nivel', ''),
                'categoria': request.args.get('categoria', ''),
                'desde': desde,
                'hasta': hasta,
                'q': request.args.get('q', '')
            }
        )
        
    except Exception as e:
        current_app.logger.error(f"Error en listado_ai: {str(e)}", exc_info=True)
        
        # En caso de error, mostrar vista vacía
        return render_template(
            "alertas_ai/listado_ai.html",
            alertas=[],
            total_alertas=0,
            alertas_criticas=0,
            ultima_alerta="N/A",
            error_message="Error al cargar las alertas. Intente nuevamente."
        )

# ===========================================
# API PARA OBTENER ALERTAS (AJAX)
# ===========================================
@alertas_ai_bp.route("/api/alertas")
@login_required
def api_alertas():
    try:
        AlertaIA = _get_alerta_model()
        
        # Parámetros
        nivel = request.args.get('nivel', '')
        categoria = request.args.get('categoria', '')
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        query = AlertaIA.query
        
        if nivel:
            query = query.filter_by(nivel=nivel)
        
        if categoria:
            query = query.filter_by(categoria=categoria)
        
        # Paginación
        total = query.count()
        alertas_bd = query.order_by(AlertaIA.fecha.desc()).offset(offset).limit(limit).all()
        
        alertas_json = [_format_alerta(a) for a in alertas_bd]
        
        return jsonify({
            "success": True,
            "alertas": alertas_json,
            "total": total,
            "offset": offset,
            "limit": limit
        })
        
    except Exception as e:
        current_app.logger.error(f"Error en api_alertas: {str(e)}")
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
        AlertaIA = _get_alerta_model()
        db = _get_db()
        
        alerta = AlertaIA.query.get_or_404(alerta_id)
        
        # Si el modelo tiene campo estado
        if hasattr(alerta, 'estado'):
            nuevo_estado = 'cerrado' if getattr(alerta, 'estado') == 'activo' else 'activo'
            setattr(alerta, 'estado', nuevo_estado)
            alerta.fecha_actualizacion = datetime.now()
            db.session.commit()
            
            return jsonify({
                "success": True,
                "estado": nuevo_estado,
                "mensaje": f"Alerta {alerta_id} marcada como {nuevo_estado}"
            })
        else:
            # Si no tiene campo estado, marcar como leída
            if hasattr(alerta, 'leida'):
                alerta.leida = True
                alerta.fecha_lectura = datetime.now()
                db.session.commit()
                
                return jsonify({
                    "success": True,
                    "mensaje": f"Alerta {alerta_id} marcada como leída"
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "El modelo no tiene campo estado ni leída"
                }), 400
                
    except Exception as e:
        current_app.logger.error(f"Error en toggle_alerta: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ===========================================
# OBTENER DETALLE DE ALERTA
# ===========================================
@alertas_ai_bp.route("/alerta/<int:alerta_id>")
@login_required
def detalle_alerta(alerta_id):
    try:
        AlertaIA = _get_alerta_model()
        
        alerta = AlertaIA.query.get_or_404(alerta_id)
        
        return render_template(
            "alertas_ai/detalle_alerta.html",
            alerta=_format_alerta(alerta)
        )
        
    except Exception as e:
        current_app.logger.error(f"Error en detalle_alerta: {str(e)}")
        return render_template(
            "alertas_ai/detalle_alerta.html",
            alerta=None,
            error_message="Alerta no encontrada"
        )

# ===========================================
# ESTADÍSTICAS DE ALERTAS
# ===========================================
@alertas_ai_bp.route("/api/estadisticas")
@login_required
def estadisticas_alertas():
    try:
        AlertaIA = _get_alerta_model()
        db = _get_db()
        
        # Conteos por nivel
        niveles_query = db.session.query(
            AlertaIA.nivel,
            db.func.count(AlertaIA.id).label('total')
        ).group_by(AlertaIA.nivel).all()
        
        niveles = {nivel: total for nivel, total in niveles_query}
        
        # Alertas últimas 24 horas
        ultimas_24h = AlertaIA.query.filter(
            AlertaIA.fecha >= datetime.now() - timedelta(days=1)
        ).count()
        
        # Alertas por categoría
        categorias_query = db.session.query(
            AlertaIA.categoria,
            db.func.count(AlertaIA.id).label('total')
        ).group_by(AlertaIA.categoria).all()
        
        categorias = {cat: total for cat, total in categorias_query}
        
        # Total
        total = AlertaIA.query.count()
        
        return jsonify({
            "success": True,
            "estadisticas": {
                "por_nivel": niveles,
                "ultimas_24h": ultimas_24h,
                "por_categoria": categorias,
                "total": total
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error en estadisticas_alertas: {str(e)}")
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
        AlertaIA = _get_alerta_model()
        
        # Aplicar mismos filtros que listado
        nivel = request.args.get('nivel', '').lower()
        categoria = request.args.get('categoria', '')
        desde = request.args.get('desde', '')
        hasta = request.args.get('hasta', '')
        q = request.args.get('q', '').lower()
        
        query = AlertaIA.query
        
        if nivel and nivel != 'todos' and nivel != '':
            query = query.filter(AlertaIA.nivel.ilike(f"%{nivel}%"))
        
        if categoria and categoria != '':
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
        
        if q and q != '':
            query = query.filter(
                AlertaIA.descripcion.ilike(f"%{q}%") | 
                AlertaIA.categoria.ilike(f"%{q}%")
            )
        
        alertas_bd = query.order_by(AlertaIA.fecha.desc()).all()
        
        # Crear CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # Encabezados
        writer.writerow([
            'ID', 'Categoría', 'Descripción', 'Nivel', 
            'Fecha', 'Origen', 'Usuario', 'Estado'
        ])
        
        # Datos
        for a in alertas_bd:
            writer.writerow([
                a.id,
                a.categoria or '',
                a.descripcion or '',
                a.nivel or '',
                a.fecha.strftime("%Y-%m-%d %H:%M") if a.fecha else '',
                getattr(a, 'origen', ''),
                getattr(a, 'usuario_nombre', ''),
                getattr(a, 'estado', '')
            ])
        
        output.seek(0)
        
        nombre_archivo = f"alertas_ia_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={nombre_archivo}",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )
        
    except Exception as e:
        current_app.logger.error(f"Error en exportar_csv: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Error al generar el reporte CSV"
        }), 500

# ===========================================
# ELIMINAR ALERTA
# ===========================================
@alertas_ai_bp.route("/api/alerta/<int:alerta_id>/eliminar", methods=["DELETE"])
@login_required
def eliminar_alerta(alerta_id):
    try:
        AlertaIA = _get_alerta_model()
        db = _get_db()
        
        alerta = AlertaIA.query.get_or_404(alerta_id)
        
        # Guardar información antes de eliminar (opcional)
        current_app.logger.info(f"Eliminando alerta {alerta_id}: {alerta.categoria}")
        
        db.session.delete(alerta)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "mensaje": f"Alerta {alerta_id} eliminada correctamente"
        })
        
    except Exception as e:
        current_app.logger.error(f"Error en eliminar_alerta: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ===========================================
# CREAR ALERTA MANUALMENTE (para testing)
# ===========================================
@alertas_ai_bp.route("/api/alerta/crear", methods=["POST"])
@login_required
def crear_alerta():
    try:
        AlertaIA = _get_alerta_model()
        db = _get_db()
        
        datos = request.get_json()
        
        if not datos:
            return jsonify({
                "success": False,
                "error": "No se recibieron datos"
            }), 400
        
        # Validar campos requeridos
        campos_requeridos = ['categoria', 'descripcion', 'nivel']
        for campo in campos_requeridos:
            if campo not in datos or not datos[campo]:
                return jsonify({
                    "success": False,
                    "error": f"Campo requerido faltante: {campo}"
                }), 400
        
        # Crear alerta
        nueva_alerta = AlertaIA(
            categoria=datos['categoria'],
            descripcion=datos['descripcion'],
            nivel=datos['nivel'],
            fecha=datetime.now(),
            origen=datos.get('origen', 'Manual'),
            usuario_nombre=datos.get('usuario', None),
            estado='activo'
        )
        
        db.session.add(nueva_alerta)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "mensaje": "Alerta creada correctamente",
            "alerta": _format_alerta(nueva_alerta)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error en crear_alerta: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
