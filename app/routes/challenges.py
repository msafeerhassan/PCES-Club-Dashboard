from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models.challenge import Challenge
from app.models.department import Department
from app.utils.permissions import (
    admin_required,
    can_view_challenge,
    can_manage_challenge,
    assignable_departments,
)

challenges_bp = Blueprint("challenges", __name__, url_prefix="/challenges")


@challenges_bp.route("/")
@login_required
def list_challenges():
    from app.models.challenge_submission import ChallengeSubmission
    from app.utils.permissions import can_manage_challenge_submission
    from app.utils.challenge_helpers import get_member_challenge_state
    from app.utils.timeutil import club_now

    all_challenges = Challenge.query.order_by(Challenge.release_date.desc(), Challenge.id.desc()).all()
    visible = [c for c in all_challenges if can_view_challenge(current_user, c)]

    now = club_now()
    active = sorted([c for c in visible if c.deadline >= now], key=lambda c: c.deadline)
    past = [c for c in visible if c.deadline < now]

    states = {c.id: get_member_challenge_state(current_user, c) for c in visible}

    is_admin = current_user.role.value in ("president", "department_admin")
    admin_counts = {}
    if is_admin:
        for c in visible:
            subs = [
                s for s in ChallengeSubmission.query.filter_by(challenge_id=c.id).all()
                if can_manage_challenge_submission(current_user, s)
            ]
            admin_counts[c.id] = {"total": len(subs), "pending": sum(1 for s in subs if not s.is_judged)}

    return render_template(
        "challenges/list.html", active=active, past=past, states=states,
        admin_counts=admin_counts, is_admin=is_admin,
    )


@challenges_bp.route("/new", methods=["GET", "POST"])
@login_required
@admin_required
def new_challenge():
    departments = assignable_departments(current_user)
    if not departments:
        abort(403)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        theme = request.form.get("theme", "").strip()
        technology = request.form.get("technology", "").strip()
        objective = request.form.get("objective", "").strip()
        submission_requirements = request.form.get("submission_requirements", "").strip()
        is_club_wide = request.form.get("is_club_wide") == "on"
        dept_ids = [int(d) for d in request.form.getlist("departments")]
        release_date = request.form.get("release_date")
        deadline_raw = request.form.get("deadline")

        if current_user.role.value != "president":
            is_club_wide = False

        allowed_ids = {d.id for d in departments}
        if any(d not in allowed_ids for d in dept_ids):
            abort(403)
        if not is_club_wide and not dept_ids:
            return render_template(
                "challenges/form.html", departments=departments, challenge=None,
                error="Select at least one department, or mark the challenge as club-wide."
            )

        challenge = Challenge(
            title=title, theme=theme, technology=technology,
            objective=objective, submission_requirements=submission_requirements,
            is_club_wide=is_club_wide,
            release_date=datetime.strptime(release_date, "%Y-%m-%d").date(),
            deadline=datetime.fromisoformat(deadline_raw),
            created_by_id=current_user.id,
        )
        if not is_club_wide:
            challenge.departments = Department.query.filter(Department.id.in_(dept_ids)).all()

        db.session.add(challenge)
        db.session.commit()

        from app.utils.discord_notify import notify_scoped
        notify_scoped(
            is_club_wide, challenge.departments,
            "🧩 New Weekly Challenge", f"**{title}** — {theme} ({technology})\nDeadline: {challenge.deadline.strftime('%B %d, %Y at %H:%M')}",
            color=0xFF8C37, ping=True,
        )

        return redirect(url_for("challenges.list_challenges"))

    return render_template("challenges/form.html", departments=departments, challenge=None, error=None)


@challenges_bp.route("/<int:challenge_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_challenge(challenge_id):
    challenge = Challenge.query.get_or_404(challenge_id)

    if not can_manage_challenge(current_user, challenge):
        abort(403)

    departments = assignable_departments(current_user)

    if request.method == "POST":
        challenge.title = request.form.get("title", "").strip()
        challenge.theme = request.form.get("theme", "").strip()
        challenge.technology = request.form.get("technology", "").strip()
        challenge.objective = request.form.get("objective", "").strip()
        challenge.submission_requirements = request.form.get("submission_requirements", "").strip()
        challenge.release_date = datetime.strptime(request.form.get("release_date"), "%Y-%m-%d").date()
        challenge.deadline = datetime.fromisoformat(request.form.get("deadline"))

        if not challenge.is_club_wide:
            dept_ids = [int(d) for d in request.form.getlist("departments")]
            allowed_ids = {d.id for d in departments}
            if any(d not in allowed_ids for d in dept_ids):
                abort(403)
            challenge.departments = Department.query.filter(Department.id.in_(dept_ids)).all()

        db.session.commit()
        return redirect(url_for("challenges.list_challenges"))

    return render_template("challenges/form.html", departments=departments, challenge=challenge, error=None)


@challenges_bp.route("/<int:challenge_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_challenge(challenge_id):
    from app.models.challenge_submission import ChallengeSubmission
    from app.models.challenge_submission_file import ChallengeSubmissionFile

    challenge = Challenge.query.get_or_404(challenge_id)
    if not can_manage_challenge(current_user, challenge):
        abort(403)

    submission_ids = [s.id for s in ChallengeSubmission.query.filter_by(challenge_id=challenge.id).all()]
    if submission_ids:
        ChallengeSubmissionFile.query.filter(ChallengeSubmissionFile.submission_id.in_(submission_ids)).delete(synchronize_session=False)
        ChallengeSubmission.query.filter(ChallengeSubmission.id.in_(submission_ids)).delete(synchronize_session=False)

    db.session.delete(challenge)
    db.session.commit()
    return redirect(url_for("challenges.list_challenges"))