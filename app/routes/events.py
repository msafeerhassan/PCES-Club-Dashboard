from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models.event import Event
from app.models.department import Department
from app.utils.permissions import (
    admin_required,
    can_view_event,
    can_manage_event,
    assignable_event_departments,
)

events_bp = Blueprint("events", __name__, url_prefix="/events")


@events_bp.route("/")
@login_required
def list_events():
    all_events = Event.query.order_by(Event.event_date.desc()).all()
    visible = [e for e in all_events if can_view_event(current_user, e)]
    return render_template("events/list.html", events=visible)


@events_bp.route("/new", methods=["GET", "POST"])
@login_required
@admin_required
def new_event():
    departments = assignable_event_departments(current_user)
    if not departments:
        abort(403)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        is_club_wide = request.form.get("is_club_wide") == "on"
        dept_ids = [int(d) for d in request.form.getlist("departments")]
        event_date = request.form.get("event_date")
        deadline_raw = request.form.get("submission_deadline")

        if current_user.role.value != "president":
            is_club_wide = False

        allowed_ids = {d.id for d in departments}
        if any(d not in allowed_ids for d in dept_ids):
            abort(403)
        if not is_club_wide and not dept_ids:
            return render_template(
                "events/form.html", departments=departments, event=None,
                error="Select at least one department, or mark the event as club-wide."
            )

        deadline = datetime.fromisoformat(deadline_raw) if deadline_raw else None

        event = Event(
            title=title,
            description=description,
            is_club_wide=is_club_wide,
            event_date=datetime.strptime(event_date, "%Y-%m-%d").date(),
            submission_deadline=deadline,
            created_by_id=current_user.id,
        )
        if not is_club_wide:
            event.departments = Department.query.filter(Department.id.in_(dept_ids)).all()

        db.session.add(event)
        db.session.commit()

        from app.utils.discord_notify import notify_scoped
        notify_scoped(
            is_club_wide, event.departments,
            "📅 New Event", f"**{title}** — {event.event_date.strftime('%B %d, %Y')}", color=0xEC3750, ping=True,
        )

        return redirect(url_for("events.list_events"))

    return render_template("events/form.html", departments=departments, event=None, error=None)


@events_bp.route("/<int:event_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_event(event_id):
    event = Event.query.get_or_404(event_id)

    if not can_manage_event(current_user, event):
        abort(403)

    departments = assignable_event_departments(current_user)

    if request.method == "POST":
        event.title = request.form.get("title", "").strip()
        event.description = request.form.get("description", "").strip()
        event.event_date = datetime.strptime(request.form.get("event_date"), "%Y-%m-%d").date()
        deadline_raw = request.form.get("submission_deadline")
        event.submission_deadline = datetime.fromisoformat(deadline_raw) if deadline_raw else None

        if not event.is_club_wide:
            dept_ids = [int(d) for d in request.form.getlist("departments")]
            allowed_ids = {d.id for d in departments}
            if any(d not in allowed_ids for d in dept_ids):
                abort(403)
            event.departments = Department.query.filter(Department.id.in_(dept_ids)).all()

        db.session.commit()
        return redirect(url_for("events.list_events"))

    return render_template("events/form.html", departments=departments, event=event, error=None)