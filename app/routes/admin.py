from flask import Blueprint, render_template, request, redirect, url_for, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models.member import Member
from app.models.submission import Submission
from app.models.attendance import Attendance
from app.models.enums import RoleEnum, SectionEnum
from app.utils.permissions import (
    admin_required,
    visible_sections,
    can_manage_section,
    assignable_roles,
    assignable_sections,
    VIEW_ALL_ROLES,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/members")
@login_required
@admin_required
def members_list():
    sections = visible_sections(current_user)
    query = Member.query.filter(
        (Member.section.in_(sections)) | (Member.role == RoleEnum.PRESIDENT) | (Member.role == RoleEnum.FACULTY_ADVISOR)
    ) if sections else None

    search = request.args.get("q", "").strip()
    if query is not None and search:
        query = query.filter(Member.name.ilike(f"%{search}%"))

    members = query.all() if query is not None else []
    return render_template("admin/members_list.html", members=members, search=search)


def build_summary_data(current_user):
    from datetime import datetime
    from app.models.event import Event
    from app.models.attendance import Attendance
    from app.models.enums import SubmissionStatus
    from app.utils.hackatime_client import get_active_now, get_hours
    from app.extensions import oauth

    sections = visible_sections(current_user)
    if not sections:
        return None

    if current_user.role in VIEW_ALL_ROLES:
        members = Member.query.filter(Member.role == RoleEnum.MEMBER).all()
    else:
        members = Member.query.filter(Member.section.in_(sections)).all()

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

    section_comparison = None
    if current_user.role in VIEW_ALL_ROLES:
        boys_hours = sum(h for m, h in contributors if m.section and m.section.value == "boys")
        girls_hours = sum(h for m, h in contributors if m.section and m.section.value == "girls")
        boys_count = sum(1 for m in members if m.section and m.section.value == "boys")
        girls_count = sum(1 for m in members if m.section and m.section.value == "girls")
        section_comparison = {
            "boys_hours": round(boys_hours, 1), "girls_hours": round(girls_hours, 1),
            "boys_count": boys_count, "girls_count": girls_count,
        }

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
        "section_comparison": section_comparison,
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

@admin_bp.route("/members/new", methods=["GET", "POST"])
@login_required
@admin_required
def member_new():
    roles = assignable_roles(current_user)
    sections = assignable_sections(current_user)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        role_value = request.form.get("role")
        section_value = request.form.get("section") or None

        role = RoleEnum(role_value)
        section = SectionEnum(section_value) if section_value else None

        if role not in roles:
            abort(403)
        if section is not None and section not in sections:
            abort(403)

        member = Member(name=name, email=email, role=role, section=section)
        db.session.add(member)
        db.session.commit()
        return redirect(url_for("admin.members_list"))

    return render_template("admin/member_form.html", roles=roles, sections=sections, member=None)


@admin_bp.route("/members/<int:member_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def member_edit(member_id):
    member = Member.query.get_or_404(member_id)

    if member.section is not None and not can_manage_section(current_user, member.section):
        abort(403)

    roles = assignable_roles(current_user)
    sections = assignable_sections(current_user)

    if request.method == "POST":
        member.name = request.form.get("name", "").strip()
        role_value = request.form.get("role")
        section_value = request.form.get("section") or None

        role = RoleEnum(role_value)
        section = SectionEnum(section_value) if section_value else None

        if role not in roles:
            abort(403)
        if section is not None and section not in sections:
            abort(403)

        member.role = role
        member.section = section
        db.session.commit()
        return redirect(url_for("admin.members_list"))

    return render_template("admin/member_form.html", roles=roles, sections=sections, member=member)


@admin_bp.route("/members/<int:member_id>/disable", methods=["GET", "POST"])
@login_required
@admin_required
def member_disable(member_id):
    from datetime import datetime

    member = Member.query.get_or_404(member_id)

    if member.section is not None and not can_manage_section(current_user, member.section):
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


@admin_bp.route("/members/<int:member_id>/enable", methods=["POST"])
@login_required
@admin_required
def member_enable(member_id):
    member = Member.query.get_or_404(member_id)

    if member.section is not None and not can_manage_section(current_user, member.section):
        abort(403)

    member.is_disabled = False
    member.disabled_reason = None
    member.disabled_at = None
    db.session.commit()
    return redirect(url_for("admin.members_list"))