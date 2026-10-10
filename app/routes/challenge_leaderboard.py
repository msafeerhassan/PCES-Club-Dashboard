from flask import Blueprint, render_template, request, abort
from flask_login import login_required, current_user
from app.models.department import Department
from app.models.challenge_submission import ChallengeSubmission
from app.utils.permissions import VIEW_ALL_ROLES, visible_departments
from app.utils.challenge_helpers import compute_challenge_streak

challenge_leaderboard_bp = Blueprint("challenge_leaderboard", __name__, url_prefix="/challenges")


def _scope_departments(viewer):
    if viewer.role in VIEW_ALL_ROLES:
        return Department.query.order_by(Department.name).all()
    if viewer.role.value == "department_admin":
        return visible_departments(viewer)
    return list(viewer.departments)


@challenge_leaderboard_bp.route("/leaderboard")
@login_required
def index():
    departments = _scope_departments(current_user)
    if not departments:
        return render_template("challenges/leaderboard.html", departments=[], selected=None, rows=[])

    selected_id = request.args.get("department_id", type=int)
    selected = next((d for d in departments if d.id == selected_id), departments[0])

    submissions = ChallengeSubmission.query.filter_by(department_id=selected.id, is_judged=True).all()

    totals = {}
    for s in submissions:
        entry = totals.setdefault(s.member_id, {"member": s.member, "points": 0, "count": 0})
        entry["points"] += s.total_score
        entry["count"] += 1

    for r in totals.values():
        r["average"] = round(r["points"] / r["count"], 1)
        r["streak"] = compute_challenge_streak(r["member"])

    rows = sorted(totals.values(), key=lambda r: (r["points"], r["average"]), reverse=True)

    return render_template("challenges/leaderboard.html", departments=departments, selected=selected, rows=rows)