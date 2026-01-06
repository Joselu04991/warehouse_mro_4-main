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
    reset_score_if_needed(current_user.id)

    tareas = Task.query.filter_by(assigned_to_id=current_user.id).all()
    
    # Calcular días restantes para cada tarea
    hoy = date.today()
    for tarea in tareas:
        if tarea.fecha_limite:
            delta = tarea.fecha_limite - hoy
            tarea.days_left = delta.days
            tarea.is_overdue = delta.days < 0
        else:
            tarea.days_left = 999
            tarea.is_overdue = False
    
    return render_template("tasks/my_tasks.html", tareas=tareas)


# =========================
# FORM CREAR TAREA (GET)
# =========================
@tasks_bp.route("/create", methods=["GET"])
@login_required
def create_task_form():
    if current_user.role not in ["admin", "owner"]:
        flash("No autorizado", "danger")
        return redirect(url_for("tasks.my_tasks"))

    usuarios = User.query.filter(User.status == "active").all()
    return render_template("tasks/create_task.html", usuarios=usuarios)


# =========================
# CREAR TAREA (POST)
# =========================
@tasks_bp.route("/create", methods=["POST"])
@login_required
def create_task():
    if current_user.role not in ["admin", "owner"]:
        flash("No autorizado", "danger")
        return redirect(url_for("tasks.my_tasks"))

    try:
        # Validar datos
        titulo = request.form.get("titulo", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        assigned_to = request.form.get("assigned_to", "")
        fecha_limite = request.form.get("fecha_limite", "")
        
        if not titulo:
            flash("El título es requerido", "danger")
            return redirect(url_for("tasks.create_task_form"))
        
        if not assigned_to:
            flash("Debe seleccionar un usuario", "danger")
            return redirect(url_for("tasks.create_task_form"))
        
        if not fecha_limite:
            flash("La fecha límite es requerida", "danger")
            return redirect(url_for("tasks.create_task_form"))
        
        # Crear la tarea
        task = Task(
            titulo=titulo,
            descripcion=descripcion,
            assigned_to_id=int(assigned_to),
            assigned_by_id=current_user.id,
            fecha_limite=date.fromisoformat(fecha_limite)
        )

        db.session.add(task)
        db.session.commit()

        flash("✅ Tarea creada correctamente", "success")
        return redirect(url_for("tasks.my_tasks"))
        
    except ValueError as e:
        db.session.rollback()
        flash(f"❌ Error en el formato de fecha: {str(e)}", "danger")
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
    try:
        task = Task.query.get_or_404(task_id)

        if task.assigned_to_id != current_user.id:
            flash("❌ No autorizado", "danger")
            return redirect(url_for("tasks.my_tasks"))

        task.estado = "completada"
        task.fecha_completado = date.today()
        aplicar_puntaje(task)
        
        db.session.commit()
        flash("✅ Tarea completada", "success")
        return redirect(url_for("tasks.my_tasks"))
        
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error al completar tarea: {str(e)}", "danger")
        return redirect(url_for("tasks.my_tasks"))


# =========================
# RANKING TÉCNICOS
# =========================
@tasks_bp.route("/ranking")
@login_required
def ranking():
    usuarios = (
        User.query
        .filter(User.score.isnot(None))
        .order_by(User.score.desc())
        .all()
    )
    return render_template("tasks/ranking.html", usuarios=usuarios)
