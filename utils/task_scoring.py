from datetime import date
from models import db
from models.user import User

def aplicar_puntaje(task):
    user = User.query.get(task.assigned_to_id)
    if not user:
        return

    dias_diferencia = (task.fecha_completado - task.fecha_limite).days

    if dias_diferencia <= 0:
        user.score = min(user.score + 1, 20)
    else:
        user.score = max(user.score - 1, 0)

    db.session.add(user)
