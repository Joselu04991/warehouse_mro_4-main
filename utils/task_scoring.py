from datetime import date
from models import db
from models.user import User

def aplicar_puntaje(task):
    usuario = User.query.get(task.assigned_to_id)

    if not usuario:
        return

    dias_diferencia = (task.fecha_completado - task.fecha_limite).days

    if dias_diferencia <= 0:
        usuario.score += 1
    else:
        usuario.score -= 1

    if usuario.score < 0:
        usuario.score = 0
    if usuario.score > 20:
        usuario.score = 20

    db.session.add(usuario)
