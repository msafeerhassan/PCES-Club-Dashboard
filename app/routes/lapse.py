from datetime import datetime, timedelta

import requests
from flask import Blueprint, current_app, flash, jsonify, redirect, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models.enums import RoleEnum
from app.models.lapse_connection import LapseConnection
from app.utils.lapse_client import verify_timelapse
from app.utils.lapse_oauth import lapse_oauth as oauth
from app.utils.timeutil import club_now

bp = Blueprint("lapse", __name__, url_prefix="/lapse")
lapse_bp = bp


def lapse_get(path, token, params=None):
    base = current_app.config["LAPSE_API_BASE"]
    r = requests.get(base + path, params=params, timeout=10,
                     headers={"Authorization": f"Bearer {token}"})
    return r.status_code, (r.json() if r.content else None)


@bp.route("/connect")
@login_required
def connect():
    return oauth.lapse.authorize_redirect(url_for("lapse.callback", _external=True))


@bp.route("/callback")
@login_required
def callback():
    try:
        token = oauth.lapse.authorize_access_token()
    except Exception as e:
        current_app.logger.error("LAPSE CALLBACK FAILED: %r", e)
        flash("Lapse connection failed. Please try again.", "error")
        return redirect(url_for("dashboard.index"))

    conn = LapseConnection.query.filter_by(member_id=current_user.id).first()
    if not conn:
        conn = LapseConnection(member_id=current_user.id, access_token=token["access_token"])
        db.session.add(conn)
    conn.access_token = token["access_token"]
    conn.refresh_token = token.get("refresh_token")
    if token.get("expires_in"):
        conn.expires_at = club_now() + timedelta(seconds=int(token["expires_in"]))

    try:
        status, body = lapse_get("/user/myself", conn.access_token)
        user = ((body or {}).get("data") or {}).get("user") or {}
        conn.lapse_user_id = user.get("id")
        conn.lapse_handle = user.get("handle")
    except Exception:
        pass

    db.session.commit()
    flash("Lapse connected.", "success")
    return redirect(url_for("dashboard.index"))


@bp.route("/disconnect", methods=["POST"])
@login_required
def disconnect():
    conn = LapseConnection.query.filter_by(member_id=current_user.id).first()
    if conn:
        db.session.delete(conn)
        db.session.commit()
        flash("Lapse disconnected.", "success")
    return redirect(url_for("dashboard.index"))


@bp.route("/debug")
@login_required
def debug():
    """President only: raw API shapes."""
    if current_user.role != RoleEnum.PRESIDENT:
        return jsonify(error="forbidden"), 403
    conn = LapseConnection.query.filter_by(member_id=current_user.id).first()
    if not conn:
        return jsonify(error="connect first at /lapse/connect"), 400
    out = {}
    for name, path, params in [
        ("myself", "/user/myself", None),
        ("timelapses", "/timelapse/myPublishedTimelapses", {"limit": 3}),
    ]:
        status, body = lapse_get(path, conn.access_token, params)
        out[name] = {"status": status, "body": body}
    return jsonify(out)


@bp.route("/verify-test")
@login_required
def verify_test():
    """President only: dry-run the verifier."""
    if current_user.role != RoleEnum.PRESIDENT:
        return jsonify(error="forbidden"), 403
    conn = LapseConnection.query.filter_by(member_id=current_user.id).first()
    start = datetime.fromisoformat(request.args.get("start", "2026-01-01"))
    end = datetime.fromisoformat(request.args.get("end", "2027-01-01"))
    return jsonify(verify_timelapse(conn, request.args.get("id"),
                                    request.args.get("project", ""), start, end))