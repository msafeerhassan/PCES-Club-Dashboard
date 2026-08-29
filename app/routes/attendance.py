from flask import Blueprint, render_template, request, redirect, url_for, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models.event import Event
from app.models.member import Member
from app.models.attendance import Attendance
from app.utils.permissions import can_manage_event
from app.models.department import Department

attendance_bp = Blueprint("attendance", __name__, url_prefix="/attendance")


@attendance_bp.route("/event/<int:event_id>", methods=["GET", "POST"])
@login_required
def mark_attendance(event_id):
    event = Event.query.get_or_404(event_id)

    if not can_manage_event(current_user, event):
        abort(403)
    
    if event.is_club_wide:
        eligible = Member.query.filter_by(is_disabled=False).all()
    else:
        dept_ids = [d.id for d in event.departments]
        eligible = Member.query.filter(
            Member.departments.any(Department.id.in_(dept_ids)), Member.is_disabled == False
        ).all()

    if request.method == "POST":
        present_ids = set(request.form.getlist("present"))
        for member in eligible:
            record = Attendance.query.filter_by(event_id=event.id, member_id=member.id).first()
            is_present = str(member.id) in present_ids
            if record is None:
                record = Attendance(
                    event_id=event.id,
                    member_id=member.id,
                    present=is_present,
                    marked_by_id=current_user.id,
                )
                db.session.add(record)
            else:
                record.present = is_present
                record.marked_by_id = current_user.id
        db.session.commit()
        return redirect(url_for("events.list_events"))

    existing = {a.member_id: a.present for a in event.attendance_records}
    return render_template("attendance/mark.html", event=event, eligible=eligible, existing=existing)


@attendance_bp.route("/me")
@login_required
def my_attendance():
    records = Attendance.query.filter_by(member_id=current_user.id).all()
    return render_template("attendance/my_history.html", records=records)