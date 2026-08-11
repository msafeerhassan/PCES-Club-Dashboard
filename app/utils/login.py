from app.extensions import login_manager
from app.models.member import Member


@login_manager.user_loader
def load_user(user_id):
    return Member.query.get(int(user_id))