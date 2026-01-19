from models.task import Task
from datetime import date

def pending_task_alerts(user):
    alerts = []

    tareas = Task.query.filter_by(
        assigned_to_id=user.id,
        estado="pendiente"
    ).all()

    for t in tareas:
        if 0 <= t.days_left <= 3:
            alerts.append(f"⏰ La tarea '{t.titulo}' vence en {t.days_left} días")

        if t.is_overdue:
            alerts.append(f"⚠️ La tarea '{t.titulo}' está vencida")

    return alerts
