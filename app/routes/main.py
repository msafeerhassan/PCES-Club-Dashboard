from flask import Blueprint, render_template
from app.models.member import Member
from app.models.event import Event
from app.models.submission import Submission
from app.models.enums import RoleEnum

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    total_members = Member.query.filter_by(is_disabled=False).count()
    total_events = Event.query.count()
    total_submissions = Submission.query.count()

    leadership = Member.query.filter(
        Member.role.in_([RoleEnum.PRESIDENT, RoleEnum.VP_BOYS, RoleEnum.VP_GIRLS, RoleEnum.FACULTY_ADVISOR])
    ).all()

    featured_projects = [
        s for s in Submission.query.filter_by(is_featured=True).order_by(Submission.submitted_at.desc()).limit(12).all()
        if s.screenshots
    ][:6]


    return render_template(
        "main/home.html",
        total_members=total_members,
        total_events=total_events,
        total_submissions=total_submissions,
        leadership=leadership,
        featured_projects=featured_projects,
    )