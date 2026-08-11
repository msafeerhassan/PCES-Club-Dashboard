from flask import Blueprint, render_template, request, redirect, url_for, abort, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models.gallery_photo import GalleryPhoto
from app.utils.storage import upload_submission_file
from app.utils.permissions import ADMIN_ROLES

gallery_bp = Blueprint("gallery", __name__, url_prefix="/gallery")


@gallery_bp.route("/manage", methods=["GET", "POST"])
@login_required
def manage():
    if current_user.role not in ADMIN_ROLES:
        abort(403)

    if request.method == "POST":
        caption = request.form.get("caption", "").strip() or None
        image_url, _ = upload_submission_file(current_app, request.files.get("photo"))
        if image_url:
            photo = GalleryPhoto(image_url=image_url, caption=caption, uploaded_by_id=current_user.id)
            db.session.add(photo)
            db.session.commit()
        return redirect(url_for("gallery.manage"))

    photos = GalleryPhoto.query.order_by(GalleryPhoto.uploaded_at.desc()).all()
    return render_template("gallery/manage.html", photos=photos)


@gallery_bp.route("/manage/<int:photo_id>/delete", methods=["POST"])
@login_required
def delete_photo(photo_id):
    if current_user.role not in ADMIN_ROLES:
        abort(403)
    photo = GalleryPhoto.query.get_or_404(photo_id)
    db.session.delete(photo)
    db.session.commit()
    return redirect(url_for("gallery.manage"))