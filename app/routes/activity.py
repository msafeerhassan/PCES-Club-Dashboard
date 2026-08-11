from flask import Blueprint, render_template, abort, redirect, url_for
from flask_login import login_required, current_user
from app.extensions import oauth
from app.models.member import Member
from app.utils.permissions import visible_sections, can_manage_section, VIEW_ALL_ROLES
from app.extensions import db
from app.utils.hackatime_client import (
    get_hours, get_streak, get_projects, get_active_now,
    get_weekly_trend, get_latest_heartbeat_details, update_longest_streak, get_club_average_hours,
)
from app.utils.dashboard_helpers import get_peer_members
activity_bp = Blueprint("activity", __name__, url_prefix="/activity")


@activity_bp.route("/me")
@login_required
def my_activity():
    connection = current_user.hackatime_connection
    if connection is None:
        return redirect(url_for("hackatime.connect"))

    hours = get_hours(oauth, connection)
    streak = get_streak(oauth, connection)
    projects = get_projects(oauth, connection)
    active, last_seen = get_active_now(oauth, connection)

    if streak:
        update_longest_streak(db, connection, streak.get("streak_days"))

    weekly_trend = get_weekly_trend(oauth, connection)
    latest_heartbeat = get_latest_heartbeat_details(oauth, connection)
    peers = get_peer_members(current_user)
    club_average = get_club_average_hours(oauth, peers)

    return render_template(
        "activity/me.html",
        hours=hours,
        streak=streak,
        projects=projects,
        active=active,
        last_seen=last_seen,
        weekly_trend=weekly_trend,
        latest_heartbeat=latest_heartbeat,
        longest_streak=connection.longest_streak_seen,
        club_average=club_average,
    )


@activity_bp.route("/admin")
@login_required
def admin_list():
    sections = visible_sections(current_user)
    if not sections:
        abort(403)

    from app.models.enums import RoleEnum

    if current_user.role in VIEW_ALL_ROLES:
        members = Member.query.filter(Member.role == RoleEnum.MEMBER).all()
    else:
        members = Member.query.filter(Member.section.in_(sections)).all()

    rows = []
    for m in members:
        connection = m.hackatime_connection
        if connection is None:
            rows.append({"member": m, "connected": False, "hours": None, "active": False})
            continue
        hours = get_hours(oauth, connection)
        active, _ = get_active_now(oauth, connection)
        rows.append({
            "member": m,
            "connected": True,
            "hours": round(hours["total_seconds"] / 3600, 1) if hours else None,
            "active": active,
        })

    return render_template("activity/admin_list.html", rows=rows)


@activity_bp.route("/member/<int:member_id>")
@login_required
def member_detail(member_id):
    member = Member.query.get_or_404(member_id)

    if current_user.role not in VIEW_ALL_ROLES:
        if member.section is None or not can_manage_section(current_user, member.section):
            abort(403)

    connection = member.hackatime_connection
    if connection is None:
        return render_template("activity/member_detail.html", member=member, connected=False)

    hours = get_hours(oauth, connection)
    streak = get_streak(oauth, connection)
    projects = get_projects(oauth, connection)
    active, last_seen = get_active_now(oauth, connection)

    if streak:
        update_longest_streak(db, connection, streak.get("streak_days"))

    weekly_trend = get_weekly_trend(oauth, connection)
    latest_heartbeat = get_latest_heartbeat_details(oauth, connection)
    peers = get_peer_members(member)
    club_average = get_club_average_hours(oauth, peers)

    return render_template(
        "activity/member_detail.html",
        member=member,
        connected=True,
        hours=hours,
        streak=streak,
        projects=projects,
        active=active,
        last_seen=last_seen,
        weekly_trend=weekly_trend,
        latest_heartbeat=latest_heartbeat,
        longest_streak=connection.longest_streak_seen,
        club_average=club_average,
    )