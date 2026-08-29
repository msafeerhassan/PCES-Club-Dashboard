from flask import Blueprint, render_template, request, redirect, url_for, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models.department import Department

departments_bp = Blueprint("departments", __name__, url_prefix="/departments")


def _require_president():
    if current_user.role.value != "president":
        abort(403)


@departments_bp.route("/")
@login_required
def list_departments():
    _require_president()
    items = Department.query.order_by(Department.name).all()
    return render_template("departments/list.html", items=items)


@departments_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_department():
    _require_president()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        discord_channel_id = request.form.get("discord_channel_id", "").strip() or None
        if name:
            existing = Department.query.filter_by(name=name).first()
            if existing is None:
                db.session.add(Department(name=name, discord_channel_id=discord_channel_id))
                db.session.commit()
                return redirect(url_for("departments.list_departments"))
            return render_template("departments/form.html", department=None, error="A department with this name already exists.")

    return render_template("departments/form.html", department=None, error=None)


@departments_bp.route("/<int:department_id>/edit", methods=["GET", "POST"])
@login_required
def edit_department(department_id):
    _require_president()
    department = Department.query.get_or_404(department_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        discord_channel_id = request.form.get("discord_channel_id", "").strip() or None
        if name:
            department.name = name
            department.discord_channel_id = discord_channel_id
            db.session.commit()
            return redirect(url_for("departments.list_departments"))

    return render_template("departments/form.html", department=department, error=None)


@departments_bp.route("/<int:department_id>/delete", methods=["POST"])
@login_required
def delete_department(department_id):
    _require_president()
    department = Department.query.get_or_404(department_id)
    db.session.delete(department)
    db.session.commit()
    return redirect(url_for("departments.list_departments"))