from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, abort, current_app
from flask_login import login_required, current_user
from app.extensions import db, oauth
from app.models.challenge import Challenge
from app.models.challenge_submission import ChallengeSubmission
from app.models.challenge_submission_file import ChallengeSubmissionFile
from app.utils.permissions import can_view_challenge
from app.utils.challenge_helpers import get_eligible_departments, compute_challenge_streak
from app.utils.timeutil import club_now
from app.utils.storage import upload_submission_files

challenge_submissions_bp = Blueprint("challenge_submissions", __name__, url_prefix="/challenges")


@challenge_submissions_bp.route("/<int:challenge_id>/submit", methods=["GET", "POST"])
@login_required
def submit(challenge_id):
    challenge = Challenge.query.get_or_404(challenge_id)
    if not can_view_challenge(current_user, challenge):
        abort(403)

    existing = ChallengeSubmission.query.filter_by(challenge_id=challenge.id, member_id=current_user.id).first()
    if existing and existing.is_judged:
        return redirect(url_for("challenge_submissions.mine"))

    eligible_departments = get_eligible_departments(current_user, challenge)
    if not eligible_departments:
        abort(403)

    connection = current_user.hackatime_connection
    hackatime_projects = []
    if connection:
        resp = oauth.hackatime.get("api/v1/authenticated/projects", token={"access_token": connection.access_token})
        hackatime_projects = [p["name"] for p in resp.json().get("projects", [])] if resp.status_code == 200 else []

    now = club_now()
    will_be_late = now > challenge.deadline

    if request.method == "POST":
        github_url = request.form.get("github_url", "").strip() or None
        demo_url = request.form.get("demo_url", "").strip() or None
        hackatime_project_name = request.form.get("hackatime_project_name") or None
        late_reason = request.form.get("late_reason", "").strip() or None

        department_id = None
        if len(eligible_departments) > 1:
            department_id = request.form.get("department_id")
            if not department_id:
                return render_template(
                    "challenges/submit.html", challenge=challenge, hackatime_projects=hackatime_projects,
                    eligible_departments=eligible_departments, will_be_late=will_be_late, existing=existing,
                    error="Select which department this submission belongs to."
                )
            department_id = int(department_id)
            if department_id not in {d.id for d in eligible_departments}:
                abort(403)
        else:
            department_id = eligible_departments[0].id

        files_in_request = [f for f in request.files.getlist("files") if f and f.filename]
        has_existing_files = bool(existing and existing.files)
        if not (github_url or demo_url or files_in_request or has_existing_files):
            return render_template(
                "challenges/submit.html", challenge=challenge, hackatime_projects=hackatime_projects,
                eligible_departments=eligible_departments, will_be_late=will_be_late, existing=existing,
                error="Add at least a GitHub link, a demo link, or a file before submitting."
            )

        if existing:
            submission = existing
        else:
            submission = ChallengeSubmission(challenge_id=challenge.id, member_id=current_user.id)
            db.session.add(submission)

        submission.department_id = department_id
        submission.github_url = github_url
        submission.demo_url = demo_url
        submission.hackatime_project_name = hackatime_project_name
        submission.submitted_at = now
        submission.is_late = will_be_late
        submission.late_reason = late_reason if will_be_late else None
        db.session.flush()

        uploaded = upload_submission_files(current_app, request.files.getlist("files"))
        for url, name in uploaded:
            db.session.add(ChallengeSubmissionFile(submission_id=submission.id, file_url=url, file_name=name))

        db.session.commit()
        return redirect(url_for("challenges.list_challenges"))

    return render_template(
        "challenges/submit.html", challenge=challenge, hackatime_projects=hackatime_projects,
        eligible_departments=eligible_departments, will_be_late=will_be_late, existing=existing, error=None,
    )


@challenge_submissions_bp.route("/mine")
@login_required
def mine():
    submissions = ChallengeSubmission.query.filter_by(member_id=current_user.id).order_by(
        ChallengeSubmission.submitted_at.desc()
    ).all()
    judged = [s for s in submissions if s.is_judged]
    total_points = sum(s.total_score for s in judged)
    average = round(total_points / len(judged), 1) if judged else None

    return render_template(
        "challenges/mine.html", submissions=submissions, total_points=total_points,
        average=average, judged_count=len(judged), streak=compute_challenge_streak(current_user),
    )