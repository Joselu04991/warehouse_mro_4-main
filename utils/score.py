from datetime import datetime
from models import db
from models.user import User

def reset_score_if_needed(user_id):
    user = User.query.get(user_id)
    if not user:
        return

    now = datetime.utcnow()

    if not hasattr(user, "score_year"):
        user.score_year = now.year
        db.session.commit()
        return

    if user.score_year != now.year:
        user.score = 20
        user.score_year = now.year
        db.session.commit()
