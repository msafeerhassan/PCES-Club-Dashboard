from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.extensions import oauth
from app.models.attendance import Attendance
from app.models.submission import Submission
from app.utils.hackatime_client import get_streak

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")


@profile_bp.route("/")
@login_required
def view_profile():
    attendance_records = Attendance.query.filter_by(member_id=current_user.id).all()
    total_marked = len(attendance_records)
    attended = sum(1 for a in attendance_records if a.present)
    attendance_pct = round((attended / total_marked) * 100, 1) if total_marked else None

    submission_count = Submission.query.filter_by(member_id=current_user.id).count()

    current_streak = None
    connection = current_user.hackatime_connection
    if connection:
        streak_data = get_streak(oauth, connection)
        current_streak = streak_data.get("streak_days") if streak_data else None

    return render_template(
        "profile/view.html",
        member=current_user,
        attendance_pct=attendance_pct,
        submission_count=submission_count,
        current_streak=current_streak,
    )