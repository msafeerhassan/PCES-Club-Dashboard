from flask import Blueprint, render_template, abort, redirect, url_for, request
from flask_login import login_required, current_user
from app.extensions import oauth
from app.models.member import Member
from app.utils.permissions import visible_departments, can_manage_member, VIEW_ALL_ROLES
from app.extensions import db
from app.utils.hackatime_client import (
    get_hours, get_streak, get_projects, get_active_now,
    get_weekly_trend, get_latest_heartbeat_details, update_longest_streak, get_club_average_hours,
)
from app.utils.dashboard_helpers import get_peer_members
activity_bp = Blueprint("activity", __name__, url_prefix="/activity")

import requests

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
    from app.models.department import Department
    from app.models.enums import RoleEnum

    departments = visible_departments(current_user)
    if not departments:
        abort(403)
    dept_ids = [d.id for d in departments]

    if current_user.role in VIEW_ALL_ROLES:
        query = Member.query.filter(Member.role == RoleEnum.MEMBER)
    else:
        query = Member.query.filter(
            Member.departments.any(Department.id.in_(dept_ids)), Member.role == RoleEnum.MEMBER
        )

    search = request.args.get("q", "").strip()
    if search:
        query = query.filter(Member.name.ilike(f"%{search}%"))

    dept_filter = request.args.get("department", "").strip()
    if dept_filter:
        dept_filter_id = int(dept_filter)
        if dept_filter_id not in dept_ids:
            abort(403)
        query = query.filter(Member.departments.any(Department.id == dept_filter_id))

    members = query.all()

    rows = []
    for m in members:
        connection = m.hackatime_connection
        if connection is None:
            rows.append({"member": m, "connected": False, "hours": None, "active": False, "streak": None})
            continue
        hours = get_hours(oauth, connection)
        active, _ = get_active_now(oauth, connection)
        streak = get_streak(oauth, connection)
        rows.append({
            "member": m,
            "connected": True,
            "hours": round(hours["total_seconds"] / 3600, 1) if hours else None,
            "active": active,
            "streak": streak.get("streak_days") if streak else None,
        })

    return render_template("activity/admin_list.html", rows=rows, search=search, dept_filter=dept_filter, departments=departments)

@activity_bp.route("/member/<int:member_id>")
@login_required
def member_detail(member_id):
    member = Member.query.get_or_404(member_id)

    if current_user.role not in VIEW_ALL_ROLES:
        if not can_manage_member(current_user, member):
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