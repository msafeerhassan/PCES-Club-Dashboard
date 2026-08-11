from flask import Blueprint, render_template, session as flask_session
from flask_login import login_required, current_user
from datetime import datetime
from app.extensions import oauth
from app.utils.permissions import visible_sections, is_read_only_admin, ADMIN_ROLES
from app.utils.dashboard_helpers import get_pending_tasks, get_upcoming_events
from app.routes.admin import build_summary_data
from app.utils.hackatime_client import get_weekly_trend
from app.models.announcement import Announcement

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.route("/")
@login_required
def index():
    sections = visible_sections(current_user)
    connection = current_user.hackatime_connection

    recent_seconds = None
    if connection:
        resp = oauth.hackatime.get("api/v1/authenticated/hours", token={"access_token": connection.access_token})
        if resp.status_code == 200:
            recent_seconds = resp.json().get("total_seconds")

    previous_login_raw = flask_session.pop("previous_login", None)
    previous_login = datetime.fromisoformat(previous_login_raw) if previous_login_raw else None

    pending_tasks = get_pending_tasks(current_user, previous_login)
    upcoming_events = get_upcoming_events(current_user)

    admin_summary = None
    if current_user.role in ADMIN_ROLES:
        admin_summary = build_summary_data(current_user)

    weekly_trend = get_weekly_trend(oauth, connection) if connection else []
    recent_announcements = Announcement.query.order_by(Announcement.created_at.desc()).limit(3).all()

    return render_template(
        "dashboard/index.html",
        member=current_user,
        sections=sections,
        read_only=is_read_only_admin(current_user),
        hackatime_connected=connection is not None,
        recent_seconds=recent_seconds,
        pending_tasks=pending_tasks,
        upcoming_events=upcoming_events,
        admin_summary=admin_summary,
        weekly_trend=weekly_trend,
        recent_announcements=recent_announcements,
    )