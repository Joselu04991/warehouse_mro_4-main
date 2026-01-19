from datetime import date
from models import db
from models.user import User

def aplicar_puntaje(task):
    user = User.query.get(task.assigned_to_id)
    if not user:
        return

    if task.fecha_completado <= task.fecha_limite:
        user.score += 1
    else:
        user.score -= 1

    if user.score < 0:
        user.score = 0

    db.session.commit()
