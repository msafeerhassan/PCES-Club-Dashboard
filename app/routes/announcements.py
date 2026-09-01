from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models.announcement import Announcement
from app.models.department import Department
from app.utils.permissions import ADMIN_ROLES, can_view_announcement, can_manage_announcement, assignable_departments

announcements_bp = Blueprint("announcements", __name__, url_prefix="/announcements")


@announcements_bp.route("/")
@login_required
def list_announcements():
    all_items = Announcement.query.order_by(Announcement.created_at.desc()).all()
    items = [a for a in all_items if can_view_announcement(current_user, a)]
    return render_template("announcements/list.html", items=items)


@announcements_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_announcement():
    if current_user.role not in ADMIN_ROLES:
        abort(403)

    departments = assignable_departments(current_user)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()
        is_club_wide = request.form.get("is_club_wide") == "on"
        dept_ids = [int(d) for d in request.form.getlist("departments")]

        if current_user.role.value != "president":
            is_club_wide = False

        allowed_ids = {d.id for d in departments}
        if any(d not in allowed_ids for d in dept_ids):
            abort(403)
        if not is_club_wide and not dept_ids:
            return render_template(
                "announcements/form.html", departments=departments,
                error="Select at least one department, or mark this as club-wide."
            )

        announcement = Announcement(title=title, body=body, created_by_id=current_user.id, is_club_wide=is_club_wide)
        if not is_club_wide:
            announcement.departments = Department.query.filter(Department.id.in_(dept_ids)).all()

        db.session.add(announcement)
        db.session.commit()

        from app.utils.discord_notify import notify_scoped
        notify_scoped(
            is_club_wide, announcement.departments,
            "📢 New Announcement", f"**{title}**\n{body}", color=0xFF8C37, ping=True,
        )

        return redirect(url_for("announcements.list_announcements"))

    return render_template("announcements/form.html", departments=departments, error=None)

@announcements_bp.route("/<int:announcement_id>/delete", methods=["POST"])
@login_required
def delete_announcement(announcement_id):
    from app.utils.permissions import can_manage_announcement

    announcement = Announcement.query.get_or_404(announcement_id)
    if not can_manage_announcement(current_user, announcement):
        abort(403)

    db.session.delete(announcement)
    db.session.commit()
    return redirect(url_for("announcements.list_announcements"))