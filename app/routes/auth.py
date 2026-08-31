from flask import Blueprint, redirect, url_for
from flask_login import current_user, login_user, logout_user, login_required
from app.extensions import oauth, db
from app.models.member import Member

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login")
def login():
    redirect_uri = url_for("auth.hca_callback", _external=True)
    return oauth.hca.authorize_redirect(redirect_uri)


@auth_bp.route("/hca/callback")
def hca_callback():
    from authlib.integrations.base_client.errors import OAuthError

    try:
        token = oauth.hca.authorize_access_token()
    except OAuthError:
        if current_user.is_authenticated:
            return redirect(url_for("dashboard.index"))
        return redirect(url_for("main.home", login_error="1"))
    resp = oauth.hca.get("api/v1/me", token=token)
    data = resp.json()
    identity = data["identity"]

    email = identity.get("primary_email")
    hca_id = identity.get("id")

    member = Member.query.filter_by(email=email).first()

    if member is None:
        return "No account found for this email. Contact an admin to be added.", 403

    if member.is_disabled:
        return "This account has been disabled. Contact an admin.", 403

    from datetime import datetime
    from flask import session as flask_session

    flask_session["previous_login"] = member.last_login.isoformat() if member.last_login else None

    member.hca_sub = hca_id
    member.is_active_account = True
    member.last_login = datetime.utcnow()
    db.session.commit()

    login_user(member)
    return redirect(url_for("dashboard.index"))


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))