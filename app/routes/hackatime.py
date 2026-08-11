from datetime import datetime, timedelta
from flask import Blueprint, redirect, url_for
from flask_login import login_required, current_user
from app.extensions import oauth, db
from app.models.hackatime_connection import HackatimeConnection

hackatime_bp = Blueprint("hackatime", __name__, url_prefix="/hackatime")


@hackatime_bp.route("/connect")
@login_required
def connect():
    redirect_uri = url_for("hackatime.callback", _external=True)
    return oauth.hackatime.authorize_redirect(redirect_uri)


@hackatime_bp.route("/callback")
@login_required
def callback():
    token = oauth.hackatime.authorize_access_token()
    resp = oauth.hackatime.get("api/v1/authenticated/me", token=token)
    data = resp.json()

    emails = data.get("emails") or []
    identifier = emails[0] if emails else str(data.get("id"))

    expires_in = token.get("expires_in")
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in) if expires_in else None

    connection = HackatimeConnection.query.filter_by(member_id=current_user.id).first()
    if connection is None:
        connection = HackatimeConnection(member_id=current_user.id)
        db.session.add(connection)

    connection.access_token = token["access_token"]
    connection.refresh_token = token.get("refresh_token")
    connection.token_expires_at = expires_at
    connection.hackatime_username = identifier
    connection.connected_at = datetime.utcnow()

    db.session.commit()
    return redirect(url_for("dashboard.index"))