from flask import Blueprint, render_template, request, redirect, url_for, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models.announcement import Announcement
from app.utils.permissions import ADMIN_ROLES

announcements_bp = Blueprint("announcements", __name__, url_prefix="/announcements")


@announcements_bp.route("/")
@login_required
def list_announcements():
    items = Announcement.query.order_by(Announcement.created_at.desc()).all()
    return render_template("announcements/list.html", items=items)


@announcements_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_announcement():
    if current_user.role not in ADMIN_ROLES:
        abort(403)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()
        announcement = Announcement(title=title, body=body, created_by_id=current_user.id)
        db.session.add(announcement)
        db.session.commit()
        return redirect(url_for("announcements.list_announcements"))

    return render_template("announcements/form.html")