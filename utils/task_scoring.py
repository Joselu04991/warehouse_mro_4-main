from datetime import date
from models import db
from models.alerts import Alert

def apply_task_score(task):
    user_score = task.assigned_to.score

    if task.completed:
        days_diff = (task.due_date - task.completed_at.date()).days

        if days_diff > 0:
            user_score.score += 2
            msg = "Tarea completada antes de la fecha (+2)"
        elif days_diff == 0:
            user_score.score += 1
            msg = "Tarea completada a tiempo (+1)"
        else:
            user_score.score -= 1
            msg = "Tarea completada fuera de fecha (-1)"
    else:
        if date.today() > task.due_date:
            user_score.score -= 2
            msg = "Tarea vencida (-2)"
        else:
            return

    alert = Alert(
        alert_type="task_score",
        message=msg,
        severity="Media",
        estado="activo",
    )

    db.session.add(alert)
    db.session.commit()
