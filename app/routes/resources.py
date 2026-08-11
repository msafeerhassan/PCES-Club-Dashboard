from flask import Blueprint, render_template, request, redirect, url_for, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models.resource import Resource
from app.utils.permissions import ADMIN_ROLES

resources_bp = Blueprint("resources", __name__, url_prefix="/resources")


@resources_bp.route("/")
@login_required
def list_resources():
    items = Resource.query.order_by(Resource.category, Resource.title).all()
    return render_template("resources/list.html", items=items)


@resources_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_resource():
    if current_user.role not in ADMIN_ROLES:
        abort(403)

    if request.method == "POST":
        resource = Resource(
            title=request.form.get("title", "").strip(),
            description=request.form.get("description", "").strip() or None,
            url=request.form.get("url", "").strip(),
            category=request.form.get("category", "").strip() or None,
            created_by_id=current_user.id,
        )
        db.session.add(resource)
        db.session.commit()
        return redirect(url_for("resources.list_resources"))

    return render_template("resources/form.html")


@resources_bp.route("/<int:resource_id>/delete", methods=["POST"])
@login_required
def delete_resource(resource_id):
    if current_user.role not in ADMIN_ROLES:
        abort(403)
    resource = Resource.query.get_or_404(resource_id)
    db.session.delete(resource)
    db.session.commit()
    return redirect(url_for("resources.list_resources"))