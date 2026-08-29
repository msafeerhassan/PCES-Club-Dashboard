from flask import Blueprint, render_template, request, redirect, url_for, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models.achievement import Achievement
from app.models.member_achievement import MemberAchievement
from app.models.member import Member
from app.utils.permissions import ADMIN_ROLES, can_manage_member, assignable_departments
from app.utils.achievements import check_and_award_all

achievements_bp = Blueprint("achievements", __name__, url_prefix="/achievements")


@achievements_bp.route("/")
@login_required
def index():
    check_and_award_all(current_user)

    all_defs = Achievement.query.order_by(Achievement.is_manual, Achievement.id).all()
    earned_ids = {ma.achievement_id for ma in MemberAchievement.query.filter_by(member_id=current_user.id).all()}

    return render_template("achievements/index.html", achievements=all_defs, earned_ids=earned_ids)


@achievements_bp.route("/manage")
@login_required
def manage():
    if current_user.role not in ADMIN_ROLES:
        abort(403)
    custom = Achievement.query.filter_by(is_manual=True).order_by(Achievement.created_at.desc()).all()
    return render_template("achievements/manage.html", achievements=custom)


@achievements_bp.route("/manage/new", methods=["GET", "POST"])
@login_required
def new_achievement():
    if current_user.role not in ADMIN_ROLES:
        abort(403)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        glyph = request.form.get("glyph", "").strip() or "★"
        color = request.form.get("color", "red")

        achievement = Achievement(
            name=name, description=description, glyph=glyph, color=color,
            is_manual=True, created_by_id=current_user.id,
        )
        db.session.add(achievement)
        db.session.commit()
        return redirect(url_for("achievements.manage"))

    return render_template("achievements/form.html")


@achievements_bp.route("/manage/<int:achievement_id>/award", methods=["GET", "POST"])
@login_required
def award(achievement_id):
    from app.models.enums import RoleEnum
    from app.models.department import Department as Dept

    if current_user.role not in ADMIN_ROLES:
        abort(403)

    achievement = Achievement.query.get_or_404(achievement_id)

    if current_user.role.value == "president":
        candidates = Member.query.filter_by(role=RoleEnum.MEMBER).all()
    else:
        departments = assignable_departments(current_user)
        dept_ids = [d.id for d in departments]
        candidates = Member.query.filter(
            Member.departments.any(Dept.id.in_(dept_ids)), Member.role == RoleEnum.MEMBER
        ).all()

    if request.method == "POST":
        member_id = int(request.form.get("member_id"))
        member = Member.query.get_or_404(member_id)
        if not can_manage_member(current_user, member):
            abort(403)

        existing = MemberAchievement.query.filter_by(member_id=member.id, achievement_id=achievement.id).first()
        if existing is None:
            db.session.add(MemberAchievement(member_id=member.id, achievement_id=achievement.id, awarded_by_id=current_user.id))
            db.session.commit()
        return redirect(url_for("achievements.manage"))

    return render_template("achievements/award.html", achievement=achievement, candidates=candidates)