import csv
import io
from datetime import datetime
from flask import Blueprint, Response, abort
from flask_login import login_required, current_user
from app.extensions import oauth
from app.models.member import Member
from app.models.attendance import Attendance
from app.models.submission import Submission
from app.models.enums import RoleEnum
from app.utils.permissions import visible_sections, VIEW_ALL_ROLES
from app.utils.hackatime_client import get_hours

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


@reports_bp.route("/export.csv")
@login_required
def export_csv():
    sections = visible_sections(current_user)
    if not sections:
        abort(403)

    if current_user.role in VIEW_ALL_ROLES:
        members = Member.query.filter(Member.role == RoleEnum.MEMBER).all()
    else:
        members = Member.query.filter(Member.section.in_(sections)).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Name", "Email", "Section", "Role",
        "Events Attended", "Total Events Marked", "Submissions",
        "Hackatime Connected", "Hours (last 7 days)",
    ])

    for m in members:
        attendance_records = Attendance.query.filter_by(member_id=m.id).all()
        attended = sum(1 for a in attendance_records if a.present)
        total_marked = len(attendance_records)
        submission_count = Submission.query.filter_by(member_id=m.id).count()

        connection = m.hackatime_connection
        hours_value = "-"
        if connection:
            hours = get_hours(oauth, connection)
            hours_value = round(hours["total_seconds"] / 3600, 1) if hours else "unavailable"

        writer.writerow([
            m.name, m.email, m.section.value if m.section else "-", m.role.value,
            attended, total_marked, submission_count,
            "Yes" if connection else "No", hours_value,
        ])

    filename = f"pces_report_{datetime.utcnow().strftime('%Y%m%d')}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )