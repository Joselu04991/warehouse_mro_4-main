from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from models import db
from models.task import Task
from models.user import User
from utils.task_scoring import aplicar_puntaje
from utils.score import reset_score_if_needed

tasks_bp = Blueprint("tasks", __name__, url_prefix="/tasks")


# =========================
# MIS TAREAS
# =========================
@tasks_bp.route("/")
@login_required
def my_tasks():
    """
    Muestra todas las tareas asignadas al usuario actual.
    Calcula días restantes y estado de vencimiento.
    """
    reset_score_if_needed(current_user.id)

    tareas = Task.query.filter_by(assigned_to_id=current_user.id).order_by(
        Task.fecha_limite.asc(), Task.estado.asc()
    ).all()
    
    return render_template("tasks/my_tasks.html", tareas=tareas)


# =========================
# FORM CREAR TAREA (GET)
# =========================
@tasks_bp.route("/create", methods=["GET"])
@login_required
def create_task_form():
    """
    Muestra el formulario para crear una nueva tarea.
    Solo accesible para administradores y dueños.
    """
    if current_user.role not in ["admin", "owner"]:
        flash("❌ No tienes permisos para crear tareas", "danger")
        return redirect(url_for("tasks.my_tasks"))

    usuarios = User.query.filter(
        User.status == "active",
        User.id != current_user.id  # Excluir al propio usuario
    ).all()
    
    return render_template("tasks/create_task.html", 
                         usuarios=usuarios,
                         fecha_minima=date.today().isoformat())


# =========================
# CREAR TAREA (POST)
# =========================
@tasks_bp.route("/create", methods=["POST"])
@login_required
def create_task():
    """
    Procesa el formulario para crear una nueva tarea.
    Solo accesible para administradores y dueños.
    """
    if current_user.role not in ["admin", "owner"]:
        flash("❌ No tienes permisos para crear tareas", "danger")
        return redirect(url_for("tasks.my_tasks"))

    try:
        # Obtener y validar datos del formulario
        titulo = request.form.get("titulo", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        assigned_to = request.form.get("assigned_to", "")
        fecha_limite = request.form.get("fecha_limite", "")
        
        # Validaciones
        errores = []
        if not titulo or len(titulo) < 3:
            errores.append("El título debe tener al menos 3 caracteres")
        
        if not assigned_to:
            errores.append("Debe seleccionar un usuario")
        
        if not fecha_limite:
            errores.append("La fecha límite es requerida")
        else:
            try:
                fecha_obj = date.fromisoformat(fecha_limite)
                if fecha_obj < date.today():
                    errores.append("La fecha límite no puede ser en el pasado")
            except ValueError:
                errores.append("Formato de fecha inválido")
        
        # Si hay errores, mostrarlos y redirigir
        if errores:
            for error in errores:
                flash(f"❌ {error}", "danger")
            return redirect(url_for("tasks.create_task_form"))
        
        # Verificar que el usuario asignado existe y está activo
        usuario_asignado = User.query.filter_by(
            id=int(assigned_to), 
            status="active"
        ).first()
        
        if not usuario_asignado:
            flash("❌ El usuario seleccionado no existe o no está activo", "danger")
            return redirect(url_for("tasks.create_task_form"))
        
        # Crear la tarea
        task = Task(
            titulo=titulo,
            descripcion=descripcion,
            assigned_to_id=int(assigned_to),
            assigned_by_id=current_user.id,
            fecha_limite=date.fromisoformat(fecha_limite),
            estado="pendiente"
        )

        db.session.add(task)
        db.session.commit()

        flash(f"✅ Tarea '{titulo}' creada exitosamente para {usuario_asignado.username}", "success")
        return redirect(url_for("tasks.my_tasks"))
        
    except ValueError as e:
        db.session.rollback()
        flash(f"❌ Error en los datos ingresados: {str(e)}", "danger")
        return redirect(url_for("tasks.create_task_form"))
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error inesperado al crear tarea: {str(e)}", "danger")
        return redirect(url_for("tasks.create_task_form"))


# =========================
# COMPLETAR TAREA
# =========================
@tasks_bp.route("/complete/<int:task_id>")
@login_required
def complete_task(task_id):
    """
    Marca una tarea como completada.
    Solo el usuario asignado puede completar su tarea.
    """
    try:
        task = Task.query.get_or_404(task_id)

        # Verificar permisos
        if task.assigned_to_id != current_user.id:
            flash("❌ No puedes completar una tarea asignada a otro usuario", "danger")
            return redirect(url_for("tasks.my_tasks"))
        
        # Verificar que no esté ya completada
        if task.estado == "completada":
            flash("ℹ️ Esta tarea ya estaba marcada como completada", "info")
            return redirect(url_for("tasks.my_tasks"))
        
        # Completar la tarea
        task.estado = "completada"
        task.fecha_completado = date.today()
        
        # Aplicar puntaje basado en la puntualidad
        aplicar_puntaje(task)
        
        db.session.commit()
        
        # Determinar mensaje basado en puntualidad
        if task.fecha_limite and task.fecha_completado > task.fecha_limite:
            flash("⚠️ Tarea completada (fuera de plazo)", "warning")
        else:
            flash("✅ Tarea completada exitosamente", "success")
            
        return redirect(url_for("tasks.my_tasks"))
        
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error al completar tarea: {str(e)}", "danger")
        return redirect(url_for("tasks.my_tasks"))


# =========================
# CANCELAR TAREA (NUEVA FUNCIONALIDAD)
# =========================
@tasks_bp.route("/cancel/<int:task_id>")
@login_required
def cancel_task(task_id):
    """
    Cancela una tarea pendiente.
    Solo el asignado o un admin pueden cancelar.
    """
    try:
        task = Task.query.get_or_404(task_id)

        # Verificar permisos
        if task.assigned_to_id != current_user.id and current_user.role not in ["admin", "owner"]:
            flash("❌ No tienes permisos para cancelar esta tarea", "danger")
            return redirect(url_for("tasks.my_tasks"))
        
        # Verificar estado
        if task.estado == "completada":
            flash("❌ No puedes cancelar una tarea ya completada", "danger")
            return redirect(url_for("tasks.my_tasks"))
        
        # Cancelar la tarea
        task.estado = "cancelada"
        task.fecha_completado = date.today()
        
        db.session.commit()
        
        flash("🔄 Tarea cancelada exitosamente", "info")
        return redirect(url_for("tasks.my_tasks"))
        
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error al cancelar tarea: {str(e)}", "danger")
        return redirect(url_for("tasks.my_tasks"))


# =========================
# VER DETALLE DE TAREA
# =========================
@tasks_bp.route("/detail/<int:task_id>")
@login_required
def task_detail(task_id):
    """
    Muestra el detalle completo de una tarea específica.
    """
    task = Task.query.get_or_404(task_id)
    
    # Verificar que el usuario puede ver esta tarea
    if task.assigned_to_id != current_user.id and current_user.role not in ["admin", "owner"]:
        flash("❌ No tienes permisos para ver esta tarea", "danger")
        return redirect(url_for("tasks.my_tasks"))
    
    # Obtener información del asignado y asignador
    asignado = User.query.get(task.assigned_to_id)
    asignador = User.query.get(task.assigned_by_id)
    
    return render_template("tasks/task_detail.html",
                         task=task,
                         asignado=asignado,
                         asignador=asignador)


# =========================
# EDITAR TAREA (SOLO ADMIN/OWNER)
# =========================
@tasks_bp.route("/edit/<int:task_id>", methods=["GET", "POST"])
@login_required
def edit_task(task_id):
    """
    Permite editar una tarea existente.
    Solo accesible para administradores y dueños.
    """
    if current_user.role not in ["admin", "owner"]:
        flash("❌ No tienes permisos para editar tareas", "danger")
        return redirect(url_for("tasks.my_tasks"))
    
    task = Task.query.get_or_404(task_id)
    
    if request.method == "GET":
        usuarios = User.query.filter(User.status == "active").all()
        return render_template("tasks/edit_task.html",
                             task=task,
                             usuarios=usuarios,
                             fecha_minima=date.today().isoformat())
    
    # POST: Procesar edición
    try:
        titulo = request.form.get("titulo", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        assigned_to = request.form.get("assigned_to", "")
        fecha_limite = request.form.get("fecha_limite", "")
        estado = request.form.get("estado", "pendiente")
        
        # Validaciones
        if not titulo or len(titulo) < 3:
            flash("❌ El título debe tener al menos 3 caracteres", "danger")
            return redirect(url_for("tasks.edit_task", task_id=task_id))
        
        # Actualizar tarea
        task.titulo = titulo
        task.descripcion = descripcion
        task.assigned_to_id = int(assigned_to)
        task.fecha_limite = date.fromisoformat(fecha_limite)
        task.estado = estado
        
        if estado == "completada" and not task.fecha_completado:
            task.fecha_completado = date.today()
            aplicar_puntaje(task)
        
        db.session.commit()
        
        flash("✅ Tarea actualizada exitosamente", "success")
        return redirect(url_for("tasks.task_detail", task_id=task_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error al actualizar tarea: {str(e)}", "danger")
        return redirect(url_for("tasks.edit_task", task_id=task_id))


# =========================
# ELIMINAR TAREA (SOLO ADMIN/OWNER)
# =========================
@tasks_bp.route("/delete/<int:task_id>", methods=["POST"])
@login_required
def delete_task(task_id):
    """
    Elimina una tarea permanentemente.
    Solo accesible para administradores y dueños.
    """
    if current_user.role not in ["admin", "owner"]:
        return jsonify({"success": False, "error": "No autorizado"}), 403
    
    try:
        task = Task.query.get_or_404(task_id)
        
        titulo = task.titulo
        db.session.delete(task)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Tarea '{titulo}' eliminada exitosamente"
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": f"Error al eliminar tarea: {str(e)}"
        }), 500


# =========================
# ESTADÍSTICAS DE TAREAS
# =========================
@tasks_bp.route("/stats")
@login_required
def task_stats():
    """
    Muestra estadísticas de tareas para el usuario actual.
    """
    # Obtener todas las tareas del usuario
    tareas = Task.query.filter_by(assigned_to_id=current_user.id).all()
    
    # Calcular estadísticas
    total_tareas = len(tareas)
    tareas_completadas = len([t for t in tareas if t.estado == "completada"])
    tareas_pendientes = len([t for t in tareas if t.estado == "pendiente"])
    tareas_canceladas = len([t for t in tareas if t.estado == "cancelada"])
    
    # Tareas vencidas (pendientes con fecha pasada)
    hoy = date.today()
    tareas_vencidas = len([
        t for t in tareas 
        if t.estado == "pendiente" 
        and t.fecha_limite 
        and t.fecha_limite < hoy
    ])
    
    # Tareas por vencer (pendientes con fecha próxima - 3 días)
    tareas_por_vencer = len([
        t for t in tareas 
        if t.estado == "pendiente" 
        and t.fecha_limite 
        and t.fecha_limite >= hoy 
        and (t.fecha_limite - hoy).days <= 3
    ])
    
    # Porcentaje de completitud
    porcentaje_completado = (tareas_completadas / total_tareas * 100) if total_tareas > 0 else 0
    
    return render_template("tasks/stats.html",
                         total_tareas=total_tareas,
                         tareas_completadas=tareas_completadas,
                         tareas_pendientes=tareas_pendientes,
                         tareas_canceladas=tareas_canceladas,
                         tareas_vencidas=tareas_vencidas,
                         tareas_por_vencer=tareas_por_vencer,
                         porcentaje_completado=round(porcentaje_completado, 1))


# =========================
# RANKING TÉCNICOS
# =========================
@tasks_bp.route("/ranking")
@login_required
def ranking():
    """
    Muestra el ranking de técnicos basado en su puntaje.
    """
    usuarios = (
        User.query
        .filter(
            User.score.isnot(None),
            User.status == "active",
            User.role.in_(["tecnico", "admin"])  # Solo técnicos y admins
        )
        .order_by(User.score.desc())
        .all()
    )
    
    # Calcular posiciones
    for i, usuario in enumerate(usuarios, 1):
        usuario.ranking_posicion = i
    
    return render_template("tasks/ranking.html", usuarios=usuarios)


# =========================
# CALENDARIO DE TAREAS
# =========================
@tasks_bp.route("/calendar")
@login_required
def task_calendar():
    """
    Muestra un calendario con las tareas del usuario.
    """
    tareas = Task.query.filter_by(assigned_to_id=current_user.id).all()
    
    # Organizar tareas por fecha
    tareas_por_fecha = {}
    for tarea in tareas:
        if tarea.fecha_limite:
            fecha_str = tarea.fecha_limite.isoformat()
            if fecha_str not in tareas_por_fecha:
                tareas_por_fecha[fecha_str] = []
            tareas_por_fecha[fecha_str].append(tarea)
    
    return render_template("tasks/calendar.html",
                         tareas_por_fecha=tareas_por_fecha,
                         hoy=date.today())


# =========================
# TAREAS POR VENCER (API)
# =========================
@tasks_bp.route("/api/upcoming")
@login_required
def api_upcoming_tasks():
    """
    API que retorna las tareas por vencer (próximos 7 días).
    """
    hoy = date.today()
    limite = hoy.replace(day=hoy.day + 7)  # Próximos 7 días
    
    tareas = Task.query.filter(
        Task.assigned_to_id == current_user.id,
        Task.estado == "pendiente",
        Task.fecha_limite.between(hoy, limite)
    ).order_by(Task.fecha_limite.asc()).all()
    
    # Formatear respuesta
    tareas_formateadas = []
    for tarea in tareas:
        dias_restantes = (tarea.fecha_limite - hoy).days
        tareas_formateadas.append({
            'id': tarea.id,
            'titulo': tarea.titulo,
            'descripcion': tarea.descripcion,
            'fecha_limite': tarea.fecha_limite.isoformat(),
            'dias_restantes': dias_restantes,
            'is_urgent': dias_restantes <= 3
        })
    
    return {
        'success': True,
        'count': len(tareas_formateadas),
        'tareas': tareas_formateadas,
        'hoy': hoy.isoformat()
    }
