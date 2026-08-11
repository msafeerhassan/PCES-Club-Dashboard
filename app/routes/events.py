from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models.event import Event
from app.models.enums import EventScopeEnum
from app.utils.permissions import (
    admin_required,
    can_view_event,
    assignable_event_scopes,
    can_manage_section,
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
    scopes = assignable_event_scopes(current_user)
    if not scopes:
        abort(403)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        scope_value = request.form.get("scope")
        event_date = request.form.get("event_date")
        deadline_raw = request.form.get("submission_deadline")

        scope = EventScopeEnum(scope_value)
        if scope not in scopes:
            abort(403)

        deadline = datetime.fromisoformat(deadline_raw) if deadline_raw else None

        event = Event(
            title=title,
            description=description,
            scope=scope,
            event_date=datetime.strptime(event_date, "%Y-%m-%d").date(),
            submission_deadline=deadline,
            created_by_id=current_user.id,
        )
        db.session.add(event)
        db.session.commit()
        return redirect(url_for("events.list_events"))

    return render_template("events/form.html", scopes=scopes, event=None)


@events_bp.route("/<int:event_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_event(event_id):
    event = Event.query.get_or_404(event_id)

    if event.scope != EventScopeEnum.CLUB_WIDE:
        member_section_equiv = event.scope.value
        if not can_manage_section(current_user, _section_from_event_scope(event.scope)):
            abort(403)
    elif current_user.role.value != "president":
        abort(403)

    scopes = assignable_event_scopes(current_user)

    if request.method == "POST":
        event.title = request.form.get("title", "").strip()
        event.description = request.form.get("description", "").strip()
        event.event_date = datetime.strptime(request.form.get("event_date"), "%Y-%m-%d").date()
        deadline_raw = request.form.get("submission_deadline")
        event.submission_deadline = datetime.fromisoformat(deadline_raw) if deadline_raw else None
        db.session.commit()
        return redirect(url_for("events.list_events"))

    return render_template("events/form.html", scopes=scopes, event=event)


def _section_from_event_scope(scope):
    from app.models.enums import SectionEnum
    return SectionEnum(scope.value)