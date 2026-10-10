from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.extensions import oauth
from app.models.department import Department
from app.models.member import Member
from app.models.submission import Submission
from app.models.challenge_submission import ChallengeSubmission
from app.models.enums import SubmissionStatus, RoleEnum
from app.utils.hackatime_client import get_hours

department_rankings_bp = Blueprint("department_rankings", __name__, url_prefix="/rankings")


@department_rankings_bp.route("/")
@login_required
def index():
    departments = Department.query.order_by(Department.name).all()
    rows = []

    for d in departments:
        members = Member.query.filter(Member.departments.any(Department.id == d.id), Member.role == RoleEnum.MEMBER).all()
        member_ids = [m.id for m in members]

        total_hours = 0
        for m in members:
            conn = m.hackatime_connection
            if conn:
                data = get_hours(oauth, conn)
                if data:
                    total_hours += data.get("total_seconds", 0) / 3600

        shipped = Submission.query.filter(
            Submission.member_id.in_(member_ids), Submission.status == SubmissionStatus.APPROVED
        ).count() if member_ids else 0

        challenge_points = 0
        if member_ids:
            judged = ChallengeSubmission.query.filter(
                ChallengeSubmission.member_id.in_(member_ids), ChallengeSubmission.is_judged == True
            ).all()
            challenge_points = sum(s.total_score for s in judged)

        rows.append({
            "id": d.id, "name": d.name, "hours": round(total_hours, 1),
            "shipped": shipped, "challenge_points": challenge_points,
        })

    rows_by_hours = sorted(rows, key=lambda r: r["hours"], reverse=True)
    rows_by_shipped = sorted(rows, key=lambda r: r["shipped"], reverse=True)
    rows_by_points = sorted(rows, key=lambda r: r["challenge_points"], reverse=True)

    return render_template(
        "rankings/index.html",
        rows_by_hours=rows_by_hours, rows_by_shipped=rows_by_shipped, rows_by_points=rows_by_points,
        my_ids={d.id for d in current_user.departments},
    )