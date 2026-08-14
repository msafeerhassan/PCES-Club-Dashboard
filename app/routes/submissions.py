from flask import Blueprint, render_template, request, redirect, url_for, abort, current_app
from flask_login import login_required, current_user
from app.extensions import db, oauth
from app.models.submission import Submission
from app.models.event import Event
from app.models.member import Member
from app.models.enums import EventScopeEnum, SectionEnum
from app.utils.permissions import visible_sections, VIEW_ALL_ROLES, can_manage_section
from app.utils.storage import upload_submission_files
from app.models.submission_file import SubmissionFile
from app.models.submission_screenshot import SubmissionScreenshot
from app.models.enums import SubmissionStatus
from app.utils.permissions import can_review_submission
from datetime import datetime, date

submissions_bp = Blueprint("submissions", __name__, url_prefix="/submissions")


@submissions_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_submission():
    connection = current_user.hackatime_connection
    if connection is None:
        return redirect(url_for("hackatime.connect"))

    resp = oauth.hackatime.get("api/v1/authenticated/projects", token={"access_token": connection.access_token})
    hackatime_projects = [p["name"] for p in resp.json().get("projects", [])] if resp.status_code == 200 else []
    from datetime import datetime

    eligible_events = [
        e for e in Event.query.all()
        if e.scope == EventScopeEnum.CLUB_WIDE or (current_user.section and e.scope.value == current_user.section.value)
    ]
    eligible_events_annotated = [
        (e, e.submission_deadline is not None and datetime.utcnow() > e.submission_deadline)
        for e in eligible_events
    ]

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        hackatime_project_name = request.form.get("hackatime_project_name") or None
        event_id = request.form.get("event_id") or None
        demo_url = request.form.get("demo_url", "").strip() or None
        github_url = request.form.get("github_url", "").strip() or None

        event = None
        if event_id:
            event = Event.query.get_or_404(int(event_id))
            if event not in eligible_events:
                abort(403)

        submission = Submission(
            member_id=current_user.id,
            event_id=event.id if event else None,
            title=title,
            description=description,
            hackatime_project_name=hackatime_project_name,
            demo_url=demo_url,
            github_url=github_url,
        )
        db.session.add(submission)
        db.session.flush()

        uploaded_files = upload_submission_files(current_app, request.files.getlist("project_files"))
        for url, name in uploaded_files:
            db.session.add(SubmissionFile(submission_id=submission.id, file_url=url, file_name=name))

        db.session.commit()
        return redirect(url_for("submissions.my_submissions"))

    return render_template(
        "submissions/new.html",
        hackatime_projects=hackatime_projects,
        eligible_events_annotated=eligible_events_annotated,
    )


@submissions_bp.route("/mine")
@login_required
def my_submissions():
    subs = Submission.query.filter_by(member_id=current_user.id).order_by(Submission.submitted_at.desc()).all()
    return render_template("submissions/my_list.html", submissions=subs)


@submissions_bp.route("/all")
@login_required
def all_submissions():
    sections = visible_sections(current_user)
    if not sections:
        abort(403)

    query = Submission.query.join(Member, Submission.member_id == Member.id)
    if current_user.role not in VIEW_ALL_ROLES:
        query = query.filter(Member.section.in_(sections))

    search = request.args.get("q", "").strip()
    if search:
        query = query.filter(Member.name.ilike(f"%{search}%"))

    section_filter = request.args.get("section", "").strip()
    if section_filter:
        try:
            section_enum = SectionEnum(section_filter)
        except ValueError:
            section_enum = None
        if section_enum is not None:
            query = query.filter(Member.section == section_enum)
    status_filter = request.args.get("status", "").strip()
    if status_filter:
        query = query.filter(Submission.status == SubmissionStatus(status_filter))

    subs = query.order_by(Submission.submitted_at.desc()).all()
    return render_template("submissions/admin_list.html", submissions=subs, search=search, section_filter=section_filter, status_filter=status_filter)

@submissions_bp.route("/<int:submission_id>/hackatime")
@login_required
def hackatime_detail(submission_id):
    submission = Submission.query.get_or_404(submission_id)

    if current_user.role not in VIEW_ALL_ROLES:
        member_section = submission.member.section
        if member_section is None or not can_manage_section(current_user, member_section):
            abort(403)

    connection = submission.member.hackatime_connection
    if connection is None or not submission.hackatime_project_name:
        return render_template("submissions/hackatime_detail.html", submission=submission, project=None)

    resp = oauth.hackatime.get("api/v1/authenticated/projects", token={"access_token": connection.access_token})
    project = None
    if resp.status_code == 200:
        for p in resp.json().get("projects", []):
            if p["name"] == submission.hackatime_project_name:
                project = p
                break

    return render_template("submissions/hackatime_detail.html", submission=submission, project=project)

@submissions_bp.route("/<int:submission_id>/feature", methods=["GET", "POST"])
@login_required
def feature_submission(submission_id):
    if current_user.role.value not in ("president", "vp_boys", "vp_girls"):
        abort(403)

    submission = Submission.query.get_or_404(submission_id)

    if current_user.role.value != "president":
        member_section = submission.member.section
        if member_section is None or not can_manage_section(current_user, member_section):
            abort(403)

    if submission.status != SubmissionStatus.APPROVED:
        return render_template(
            "submissions/feature_form.html", submission=submission,
            error="Only approved submissions can be featured. Review and approve it first."
        )

    if request.method == "POST":
        uploaded = upload_submission_files(current_app, request.files.getlist("screenshots"))
        for url, _ in uploaded:
            db.session.add(SubmissionScreenshot(submission_id=submission.id, image_url=url))
        db.session.flush()

        has_screenshot = SubmissionScreenshot.query.filter_by(submission_id=submission.id).count() > 0
        if not has_screenshot:
            db.session.rollback()
            return render_template(
                "submissions/feature_form.html", submission=submission,
                error="At least one screenshot is required to feature a project."
            )

        submission.is_featured = True
        db.session.commit()
        return redirect(url_for("submissions.all_submissions"))

    return render_template("submissions/feature_form.html", submission=submission, error=None)


@submissions_bp.route("/<int:submission_id>/unfeature", methods=["POST"])
@login_required
def unfeature_submission(submission_id):
    if current_user.role.value not in ("president", "vp_boys", "vp_girls"):
        abort(403)

    submission = Submission.query.get_or_404(submission_id)

    if current_user.role.value != "president":
        member_section = submission.member.section
        if member_section is None or not can_manage_section(current_user, member_section):
            abort(403)

    submission.is_featured = False
    db.session.commit()
    return redirect(url_for("submissions.all_submissions"))


@submissions_bp.route("/<int:submission_id>/approve", methods=["POST"])
@login_required
def approve_submission(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    if not can_review_submission(current_user, submission):
        abort(403)

    submission.status = SubmissionStatus.APPROVED
    submission.reviewed_by_id = current_user.id
    submission.reviewed_at = datetime.utcnow()
    db.session.commit()
    return redirect(url_for("submissions.all_submissions"))


@submissions_bp.route("/<int:submission_id>/reject", methods=["GET", "POST"])
@login_required
def reject_submission(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    if not can_review_submission(current_user, submission):
        abort(403)

    if request.method == "POST":
        feedback = request.form.get("feedback", "").strip()
        if not feedback:
            return render_template("submissions/reject_form.html", submission=submission, error="Feedback is required so the member knows what to fix.")

        submission.status = SubmissionStatus.REJECTED
        submission.reviewed_by_id = current_user.id
        submission.reviewed_at = datetime.utcnow()
        submission.feedback = feedback
        submission.is_featured = False
        db.session.commit()
        return redirect(url_for("submissions.all_submissions"))

    return render_template("submissions/reject_form.html", submission=submission, error=None)


@submissions_bp.route("/<int:submission_id>/edit", methods=["GET", "POST"])
@login_required
def edit_submission(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    if submission.member_id != current_user.id:
        abort(403)
    if submission.status != SubmissionStatus.REJECTED:
        abort(403)

    connection = current_user.hackatime_connection
    hackatime_projects = []
    if connection:
        resp = oauth.hackatime.get("api/v1/authenticated/projects", token={"access_token": connection.access_token})
        hackatime_projects = [p["name"] for p in resp.json().get("projects", [])] if resp.status_code == 200 else []

    if request.method == "POST":
        submission.title = request.form.get("title", "").strip()
        submission.description = request.form.get("description", "").strip()
        submission.hackatime_project_name = request.form.get("hackatime_project_name") or None
        submission.demo_url = request.form.get("demo_url", "").strip() or None
        submission.github_url = request.form.get("github_url", "").strip() or None

        submission.status = SubmissionStatus.PENDING
        submission.reviewed_by_id = None
        submission.reviewed_at = None
        submission.feedback = None

        db.session.commit()
        return redirect(url_for("submissions.my_submissions"))

    return render_template("submissions/edit.html", submission=submission, hackatime_projects=hackatime_projects)