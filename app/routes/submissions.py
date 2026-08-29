from flask import Blueprint, render_template, request, redirect, url_for, abort, current_app
from flask_login import login_required, current_user
from app.extensions import db, oauth
from app.models.submission import Submission
from app.models.event import Event
from app.models.member import Member
from app.utils.permissions import visible_departments, can_manage_submission, can_view_submission, VIEW_ALL_ROLES
from app.utils.storage import upload_submission_files
from app.models.submission_file import SubmissionFile
from app.models.submission_screenshot import SubmissionScreenshot
from app.models.enums import SubmissionStatus
from datetime import datetime, date
from app.models.department import Department

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

    from app.utils.dashboard_helpers import get_eligible_events
    eligible_events = get_eligible_events(current_user)
    eligible_events_annotated = [
        (e, e.submission_deadline is not None and datetime.utcnow() > e.submission_deadline)
        for e in eligible_events
    ]

    member_departments = current_user.departments

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        hackatime_project_name = request.form.get("hackatime_project_name") or None
        event_id = request.form.get("event_id") or None
        demo_url = request.form.get("demo_url", "").strip() or None
        github_url = request.form.get("github_url", "").strip() or None

        department = None
        if len(member_departments) > 1:
            department_id = request.form.get("department_id")
            if not department_id:
                return render_template(
                    "submissions/new.html", hackatime_projects=hackatime_projects,
                    eligible_events_annotated=eligible_events_annotated, member_departments=member_departments,
                    error="Select which department this project belongs to."
                )
            department_id = int(department_id)
            if department_id not in {d.id for d in member_departments}:
                abort(403)
            department = Department.query.get(department_id)
        elif len(member_departments) == 1:
            department = member_departments[0]

        event = None
        if event_id:
            event = Event.query.get_or_404(int(event_id))
            if event not in eligible_events:
                abort(403)

        submission = Submission(
            member_id=current_user.id,
            event_id=event.id if event else None,
            department_id=department.id if department else None,
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
        member_departments=member_departments,
        error=None,
    )


@submissions_bp.route("/mine")
@login_required
def my_submissions():
    subs = Submission.query.filter_by(member_id=current_user.id).order_by(Submission.submitted_at.desc()).all()
    return render_template("submissions/my_list.html", submissions=subs)

@submissions_bp.route("/all")
@login_required
def all_submissions():
    from app.models.department import Department
    from app.models.enums import SubmissionStatus

    departments = visible_departments(current_user)
    if not departments:
        abort(403)
    dept_ids = [d.id for d in departments]

    from sqlalchemy import or_, and_

    query = Submission.query.join(Member, Submission.member_id == Member.id)
    if current_user.role not in VIEW_ALL_ROLES:
        query = query.filter(
            or_(
                Submission.department_id.in_(dept_ids),
                and_(Submission.department_id.is_(None), Member.departments.any(Department.id.in_(dept_ids))),
            )
        )

    search = request.args.get("q", "").strip()
    if search:
        query = query.filter(Member.name.ilike(f"%{search}%"))

    status_filter = request.args.get("status", "").strip()
    if status_filter:
        query = query.filter(Submission.status == SubmissionStatus(status_filter.upper()))

    dept_filter = request.args.get("department", "").strip()
    if dept_filter:
        dept_filter_id = int(dept_filter)
        if dept_filter_id not in dept_ids:
            abort(403)
        query = query.filter(Submission.department_id == dept_filter_id)

    subs = query.order_by(Submission.submitted_at.desc()).all()
    return render_template(
        "submissions/admin_list.html", submissions=subs, search=search,
        status_filter=status_filter, dept_filter=dept_filter, departments=departments
    )

@submissions_bp.route("/<int:submission_id>/hackatime")
@login_required
def hackatime_detail(submission_id):
    submission = Submission.query.get_or_404(submission_id)

    if not can_view_submission(current_user, submission):
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

    if not can_manage_member(current_user, submission.member):
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

    if not can_manage_member(current_user, submission.member):
        abort(403)

    submission.is_featured = False
    db.session.commit()
    return redirect(url_for("submissions.all_submissions"))


@submissions_bp.route("/<int:submission_id>/approve", methods=["POST"])
@login_required
def approve_submission(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    if not can_manage_submission(current_user, submission):
        abort(403)

    submission.status = SubmissionStatus.APPROVED
    submission.reviewed_by_id = current_user.id
    submission.reviewed_at = datetime.utcnow()
    db.session.commit()

    from app.utils.discord_notify import notify_scoped
    notify_departments = [submission.department] if submission.department else submission.member.departments
    notify_scoped(
        False, notify_departments,
        "🚀 Project Shipped", f"**{submission.member.name}** just got **{submission.title}** approved!", color=0x33D6A6,
    )

    return redirect(url_for("submissions.all_submissions"))


@submissions_bp.route("/<int:submission_id>/reject", methods=["GET", "POST"])
@login_required
def reject_submission(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    if not can_manage_submission(current_user, submission):
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

        from app.utils.discord_notify import notify_scoped
        notify_departments = [submission.department] if submission.department else submission.member.departments
        notify_scoped(
            False, notify_departments,
            "🔁 Submission Needs Changes", f"**{submission.member.name}**'s **{submission.title}** was sent back for revisions.", color=0xEC3750,
        )
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