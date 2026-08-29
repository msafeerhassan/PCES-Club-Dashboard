from flask import Blueprint, render_template, request, redirect, url_for, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models.member import Member
from app.models.submission import Submission
from app.models.attendance import Attendance
from app.models.enums import RoleEnum
from app.utils.permissions import (
    admin_required,
    visible_departments,
    can_manage_member,
    assignable_roles,
    assignable_departments,
    VIEW_ALL_ROLES,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

def build_summary_data(current_user):
    from datetime import datetime
    from app.models.event import Event
    from app.models.attendance import Attendance
    from app.models.enums import SubmissionStatus
    from app.utils.hackatime_client import get_active_now, get_hours
    from app.extensions import oauth

    from app.models.department import Department

    departments = visible_departments(current_user)
    if not departments:
        return None
    dept_ids = [d.id for d in departments]

    if current_user.role in VIEW_ALL_ROLES:
        members = Member.query.filter(Member.role == RoleEnum.MEMBER).all()
    else:
        members = Member.query.filter(
            Member.departments.any(Department.id.in_(dept_ids)), Member.role == RoleEnum.MEMBER
        ).all()

    member_ids = [m.id for m in members]
    total_members = len(members)
    upcoming_events = Event.query.filter(Event.event_date >= datetime.utcnow().date()).count()

    submission_count = Submission.query.filter(
        Submission.member_id.in_(member_ids), Submission.status == SubmissionStatus.APPROVED
    ).count()
    pending_review_count = Submission.query.filter(
        Submission.member_id.in_(member_ids), Submission.status == SubmissionStatus.PENDING
    ).count()

    active_now = 0
    contributors = []
    for m in members:
        conn = m.hackatime_connection
        hours = 0
        if conn:
            active, _ = get_active_now(oauth, conn)
            if active:
                active_now += 1
            data = get_hours(oauth, conn)
            hours = round(data.get("total_seconds", 0) / 3600, 1) if data else 0
        contributors.append((m, hours))

    contributors.sort(key=lambda x: x[1], reverse=True)
    top_contributors = contributors[:5]

    never_logged_in = [m for m in members if not m.is_active_account]

    recent_submissions = Submission.query.filter(
        Submission.member_id.in_(member_ids), Submission.status == SubmissionStatus.APPROVED
    ).order_by(Submission.submitted_at.desc()).limit(5).all()

    department_breakdown = []
    for dept in departments:
        dept_members = [m for m in members if dept in m.departments]
        dept_hours = sum(h for m, h in contributors if dept in m.departments)
        department_breakdown.append({
            "name": dept.name,
            "member_count": len(dept_members),
            "hours": round(dept_hours, 1),
        })
    department_breakdown.sort(key=lambda d: d["hours"], reverse=True)
    all_attendance = Attendance.query.filter(Attendance.member_id.in_(member_ids)).all()
    total_marked = len(all_attendance)
    attended = sum(1 for a in all_attendance if a.present)
    overall_attendance_rate = round((attended / total_marked) * 100, 1) if total_marked else None

    connected_count = sum(1 for m in members if m.hackatime_connection)
    hackatime_adoption_pct = round((connected_count / total_members) * 100, 1) if total_members else 0
    disabled_count = sum(1 for m in members if m.is_disabled)
    featured_count = Submission.query.filter(
        Submission.member_id.in_(member_ids), Submission.is_featured == True
    ).count()
    next_event = Event.query.filter(Event.event_date >= datetime.utcnow().date()).order_by(Event.event_date).first()
    days_to_next_event = (next_event.event_date - datetime.utcnow().date()).days if next_event else None

    return {
        "total_members": total_members,
        "upcoming_events": upcoming_events,
        "submission_count": submission_count,
        "pending_review_count": pending_review_count,
        "active_now": active_now,
        "top_contributors": top_contributors,
        "never_logged_in": never_logged_in,
        "recent_submissions": recent_submissions,
        "department_breakdown": department_breakdown,
        "overall_attendance_rate": overall_attendance_rate,
        "connected_count": connected_count,
        "hackatime_adoption_pct": hackatime_adoption_pct,
        "disabled_count": disabled_count,
        "featured_count": featured_count,
        "next_event": next_event,
        "days_to_next_event": days_to_next_event,
    }

@admin_bp.route("/summary")
@login_required
def summary():
    data = build_summary_data(current_user)
    if data is None:
        abort(403)
    return render_template("admin/summary.html", **data)

@admin_bp.route("/members")
@login_required
def members_list():
    if current_user.role.value not in ('president', 'department_admin', 'faculty_advisor'):
        abort(403)
    from app.models.department import Department

    if current_user.role in VIEW_ALL_ROLES:
        query = Member.query
    else:
        departments = visible_departments(current_user)
        dept_ids = [d.id for d in departments]
        if not dept_ids:
            query = Member.query.filter(False)
        else:
            query = Member.query.filter(
                (Member.departments.any(Department.id.in_(dept_ids))) | (Member.role == RoleEnum.PRESIDENT) | (Member.role == RoleEnum.FACULTY_ADVISOR)
            )

    search = request.args.get("q", "").strip()
    if search:
        query = query.filter(Member.name.ilike(f"%{search}%"))

    members = query.all()
    return render_template("admin/members_list.html", members=members, search=search)

@admin_bp.route("/members/<int:member_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def member_edit(member_id):
    from app.models.department import Department

    member = Member.query.get_or_404(member_id)

    if not can_manage_member(current_user, member):
        abort(403)

    roles = assignable_roles(current_user)
    departments = assignable_departments(current_user)

    if request.method == "POST":
        member.name = request.form.get("name", "").strip()
        role_value = request.form.get("role")
        dept_ids = [int(d) for d in request.form.getlist("departments")]

        role = RoleEnum(role_value)
        if role not in roles:
            abort(403)

        allowed_ids = {d.id for d in departments}
        if any(d not in allowed_ids for d in dept_ids):
            abort(403)

        member.role = role
        member.departments = Department.query.filter(Department.id.in_(dept_ids)).all()
        db.session.commit()
        return redirect(url_for("admin.members_list"))

    return render_template("admin/member_form.html", roles=roles, departments=departments, member=member)

@admin_bp.route("/members/<int:member_id>/disable", methods=["GET", "POST"])
@login_required
@admin_required
def member_disable(member_id):
    from datetime import datetime

    member = Member.query.get_or_404(member_id)

    if not can_manage_member(current_user, member):
        abort(403)

    if request.method == "POST":
        reason = request.form.get("reason", "").strip()
        if not reason:
            return render_template("admin/disable_form.html", member=member, error="A reason is required.")

        member.is_disabled = True
        member.disabled_reason = reason
        member.disabled_at = datetime.utcnow()
        db.session.commit()
        return redirect(url_for("admin.members_list"))

    return render_template("admin/disable_form.html", member=member, error=None)

@admin_bp.route("/members/new", methods=["GET", "POST"])
@login_required
@admin_required
def member_new():
    from app.models.department import Department

    roles = assignable_roles(current_user)
    departments = assignable_departments(current_user)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        role_value = request.form.get("role")
        dept_ids = [int(d) for d in request.form.getlist("departments")]

        role = RoleEnum(role_value)
        if role not in roles:
            abort(403)

        allowed_ids = {d.id for d in departments}
        if any(d not in allowed_ids for d in dept_ids):
            abort(403)

        member = Member(name=name, email=email, role=role)
        member.departments = Department.query.filter(Department.id.in_(dept_ids)).all()
        db.session.add(member)
        db.session.commit()
        return redirect(url_for("admin.members_list"))

    return render_template("admin/member_form.html", roles=roles, departments=departments, member=None)

@admin_bp.route("/members/<int:member_id>/enable", methods=["POST"])
@login_required
@admin_required
def member_enable(member_id):
    member = Member.query.get_or_404(member_id)

    if not can_manage_member(current_user, member):
        abort(403)

    member.is_disabled = False
    member.disabled_reason = None
    member.disabled_at = None
    db.session.commit()
    return redirect(url_for("admin.members_list"))

@admin_bp.route("/department-health")
@login_required
def department_health():
    from app.models.department import Department
    from app.models.submission import Submission
    from app.models.attendance import Attendance
    from app.models.achievement import Achievement
    from app.models.member_achievement import MemberAchievement
    from app.models.enums import SubmissionStatus
    from app.utils.hackatime_client import get_hours, get_active_now

    if current_user.role.value == "president":
        available = Department.query.order_by(Department.name).all()
    elif current_user.role.value == "department_admin":
        available = list(current_user.departments)
    else:
        abort(403)

    if not available:
        return render_template("admin/department_health.html", available=[], selected=None, data=None)

    selected_id = request.args.get("department_id", type=int)
    selected = None
    if selected_id:
        selected = next((d for d in available if d.id == selected_id), None)
        if selected is None:
            abort(403)
    else:
        selected = available[0]

    members = Member.query.filter(Member.departments.any(Department.id == selected.id), Member.role == RoleEnum.MEMBER).all()
    member_ids = [m.id for m in members]

    submission_count = Submission.query.filter(
        Submission.department_id == selected.id, Submission.status == SubmissionStatus.APPROVED
    ).count()
    pending_count = Submission.query.filter(
        Submission.department_id == selected.id, Submission.status == SubmissionStatus.PENDING
    ).count()

    attendance_records = Attendance.query.filter(Attendance.member_id.in_(member_ids)).all()
    total_marked = len(attendance_records)
    attended = sum(1 for a in attendance_records if a.present)
    attendance_rate = round((attended / total_marked) * 100, 1) if total_marked else None

    contributors = []
    active_now = 0
    connected_count = 0
    for m in members:
        conn = m.hackatime_connection
        hours = 0
        if conn:
            connected_count += 1
            active, _ = get_active_now(oauth, conn)
            if active:
                active_now += 1
            hours_data = get_hours(oauth, conn)
            hours = round(hours_data.get("total_seconds", 0) / 3600, 1) if hours_data else 0
        contributors.append((m, hours))
    contributors.sort(key=lambda x: x[1], reverse=True)

    achievements_earned = MemberAchievement.query.filter(MemberAchievement.member_id.in_(member_ids)).count() if member_ids else 0

    data = {
        "member_count": len(members),
        "submission_count": submission_count,
        "pending_count": pending_count,
        "attendance_rate": attendance_rate,
        "top_contributors": contributors[:5],
        "active_now": active_now,
        "adoption_pct": round((connected_count / len(members)) * 100, 1) if members else 0,
        "achievements_earned": achievements_earned,
    }

    return render_template("admin/department_health.html", available=available, selected=selected, data=data)