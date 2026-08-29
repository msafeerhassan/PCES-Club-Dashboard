from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from app.extensions import oauth, db
from app.models.member import Member
from app.models.department import Department
from app.models.submission import Submission
from app.models.attendance import Attendance
from app.models.enums import RoleEnum, SubmissionStatus
from app.utils.permissions import VIEW_ALL_ROLES, visible_departments
from app.utils.hackatime_client import get_hours, get_streak
from app.utils.dashboard_helpers import get_peer_members

leaderboard_bp = Blueprint("leaderboard", __name__, url_prefix="/leaderboard")


def _get_scoped_members(member):
    if member.role in VIEW_ALL_ROLES:
        return Member.query.filter_by(role=RoleEnum.MEMBER).all()
    if member.role == RoleEnum.DEPARTMENT_ADMIN:
        departments = visible_departments(member)
        dept_ids = [d.id for d in departments]
        if not dept_ids:
            return []
        return Member.query.filter(
            Member.departments.any(Department.id.in_(dept_ids)), Member.role == RoleEnum.MEMBER
        ).all()
    return get_peer_members(member)


@leaderboard_bp.route("/")
@login_required
def index():
    tab = request.args.get("tab", "hours")
    members = _get_scoped_members(current_user)

    rows = []
    for m in members:
        connection = m.hackatime_connection
        hours = 0
        streak = 0
        if connection:
            hours_data = get_hours(oauth, connection)
            hours = round(hours_data.get("total_seconds", 0) / 3600, 1) if hours_data else 0
            streak_data = get_streak(oauth, connection)
            streak = streak_data.get("streak_days") if streak_data else 0

        submission_count = Submission.query.filter_by(member_id=m.id, status=SubmissionStatus.APPROVED).count()

        attendance_records = Attendance.query.filter_by(member_id=m.id).all()
        total_marked = len(attendance_records)
        attended = sum(1 for a in attendance_records if a.present)
        attendance_pct = round((attended / total_marked) * 100, 1) if total_marked else 0

        rows.append({
            "member": m, "hours": hours, "streak": streak or 0,
            "submissions": submission_count, "attendance": attendance_pct,
        })

    key_map = {"hours": "hours", "streak": "streak", "submissions": "submissions", "attendance": "attendance"}
    sort_key = key_map.get(tab, "hours")
    rows.sort(key=lambda r: r[sort_key], reverse=True)

    return render_template("leaderboard/index.html", rows=rows, tab=tab)