from datetime import datetime
from app.extensions import db


class HackatimeConnection(db.Model):
    __tablename__ = "hackatime_connections"

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"), unique=True, nullable=False)

    access_token = db.Column(db.String(500), nullable=False)
    refresh_token = db.Column(db.String(500), nullable=True)
    token_expires_at = db.Column(db.DateTime, nullable=True)

    hackatime_username = db.Column(db.String(255), nullable=True)
    connected_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    longest_streak_seen = db.Column(db.Integer, default=0, nullable=False)
    member = db.relationship("Member", backref=db.backref("hackatime_connection", uselist=False))