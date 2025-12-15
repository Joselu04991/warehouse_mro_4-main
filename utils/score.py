from datetime import date
from models import db
from models.user import User

def reset_score_if_needed(user_id):
    user = User.query.get(user_id)
    if not user:
        return

    hoy = date.today()

    if not user.score_last_reset:
        user.score_last_reset = hoy
        db.session.commit()
        return

    if (hoy - user.score_last_reset).days >= 365:
        user.score = 20
        user.score_last_reset = hoy
        db.session.commit()
