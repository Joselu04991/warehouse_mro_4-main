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
    """
    reset_score_if_needed(current_user.id)

    tareas = Task.query.filter_by(assigned_to_id=current_user.id).order_by(
        Task.fecha_limite.asc(), Task.estado.asc()
    ).all()
    
    return render_template("tasks/my_tasks.html", 
                         tareas=tareas,
                         today=date.today())  # ✅ AQUÍ PASAS LA FECHA ACTUAL


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

    usuarios = User.query.filter(User.status == "active").all()
    
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
        titulo = request.form.get("titulo", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        assigned_to = request.form.get("assigned_to", "")
        fecha_limite = request.form.get("fecha_limite", "")
        
        if not titulo or len(titulo) < 3:
            flash("❌ El título debe tener al menos 3 caracteres", "danger")
            return redirect(url_for("tasks.create_task_form"))
        
        if not assigned_to:
            flash("❌ Debe seleccionar un usuario", "danger")
            return redirect(url_for("tasks.create_task_form"))
        
        if not fecha_limite:
            flash("❌ La fecha límite es requerida", "danger")
            return redirect(url_for("tasks.create_task_form"))
        
        fecha_obj = date.fromisoformat(fecha_limite)
        if fecha_obj < date.today():
            flash("❌ La fecha límite no puede ser en el pasado", "danger")
            return redirect(url_for("tasks.create_task_form"))
        
        usuario_asignado = User.query.filter_by(
            id=int(assigned_to), 
            status="active"
        ).first()
        
        if not usuario_asignado:
            flash("❌ El usuario seleccionado no existe o no está activo", "danger")
            return redirect(url_for("tasks.create_task_form"))
        
        task = Task(
            titulo=titulo,
            descripcion=descripcion,
            assigned_to_id=int(assigned_to),
            assigned_by_id=current_user.id,
            fecha_limite=fecha_obj,
            estado="pendiente"
        )

        db.session.add(task)
        db.session.commit()

        flash(f"✅ Tarea '{titulo}' creada para {usuario_asignado.username}", "success")
        return redirect(url_for("tasks.my_tasks"))
        
    except ValueError:
        db.session.rollback()
        flash("❌ Formato de fecha inválido", "danger")
        return redirect(url_for("tasks.create_task_form"))
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error al crear tarea: {str(e)}", "danger")
        return redirect(url_for("tasks.create_task_form"))


# =========================
# COMPLETAR TAREA
# =========================
@tasks_bp.route("/complete/<int:task_id>")
@login_required
def complete_task(task_id):
    """
    Marca una tarea como completada.
    """
    try:
        task = Task.query.get_or_404(task_id)

        if task.assigned_to_id != current_user.id:
            flash("❌ No puedes completar tareas de otros", "danger")
            return redirect(url_for("tasks.my_tasks"))
        
        if task.estado == "completada":
            flash("ℹ️ Esta tarea ya estaba completada", "info")
            return redirect(url_for("tasks.my_tasks"))
        
        task.estado = "completada"
        task.fecha_completado = date.today()
        aplicar_puntaje(task)
        
        db.session.commit()
        
        if task.fecha_limite and task.fecha_completado > task.fecha_limite:
            flash("⚠️ Tarea completada (fuera de plazo)", "warning")
        else:
            flash("✅ Tarea completada", "success")
            
        return redirect(url_for("tasks.my_tasks"))
        
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error: {str(e)}", "danger")
        return redirect(url_for("tasks.my_tasks"))


# =========================
# RANKING TÉCNICOS
# =========================
@tasks_bp.route("/ranking")
@login_required
def ranking():
    """
    Muestra el ranking de técnicos.
    """
    usuarios = (
        User.query
        .filter(User.score.isnot(None))
        .order_by(User.score.desc())
        .all()
    )
    
    return render_template("tasks/ranking.html", usuarios=usuarios)
