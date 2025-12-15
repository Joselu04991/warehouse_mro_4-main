from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from models import db
from models.task import Task
from models.user import User
from utils.task_scoring import aplicar_puntaje
from utils.score import reset_score_if_needed

tasks_bp = Blueprint("tasks", __name__, url_prefix="/tasks")


@tasks_bp.route("/")
@login_required
def my_tasks():
    reset_score_if_needed(current_user.id)

    tareas = Task.query.filter_by(assigned_to_id=current_user.id).all()
    usuarios = User.query.all()

    return render_template(
        "tasks/my_tasks.html",
        tareas=tareas,
        usuarios=usuarios
    )


@tasks_bp.route("/create", methods=["POST"])
@login_required
def create_task():
    if current_user.role not in ["admin", "owner"]:
        flash("No autorizado", "danger")
        return redirect(url_for("tasks.my_tasks"))

    task = Task(
        titulo=request.form["titulo"],
        descripcion=request.form["descripcion"],
        assigned_to_id=request.form["assigned_to"],
        assigned_by_id=current_user.id,
        fecha_limite=date.fromisoformat(request.form["fecha_limite"]),
        estado="pendiente"
    )

    db.session.add(task)
    db.session.commit()

    flash("Tarea creada correctamente", "success")
    return redirect(url_for("tasks.my_tasks"))


@tasks_bp.route("/complete/<int:task_id>")
@login_required
def complete_task(task_id):
    task = Task.query.get_or_404(task_id)

    if task.assigned_to_id != current_user.id:
        flash("No autorizado", "danger")
        return redirect(url_for("tasks.my_tasks"))

    task.estado = "completada"
    task.fecha_completado = date.today()

    aplicar_puntaje(task)

    db.session.commit()
    flash("Tarea completada", "success")
    return redirect(url_for("tasks.my_tasks"))


@tasks_bp.route("/ranking")
@login_required
def ranking():
    if current_user.role not in ["admin", "owner"]:
        flash("No autorizado", "danger")
        return redirect(url_for("tasks.my_tasks"))

    usuarios = User.query.order_by(User.score.desc()).all()
    return render_template("tasks/ranking.html", usuarios=usuarios)
