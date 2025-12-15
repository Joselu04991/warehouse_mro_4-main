from datetime import datetime
from models import db
from models.user_score import UserScore

def reset_score_if_needed(user):
    current_year = datetime.utcnow().year

    score = user.score
    if score.last_reset_year != current_year:
        score.score = 20
        score.last_reset_year = current_year
        db.session.commit()
