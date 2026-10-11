from app.extensions import db
from app.utils.timeutil import club_now


class LapseConnection(db.Model):
    __tablename__ = "lapse_connections"

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id", ondelete="CASCADE"),
                          unique=True, nullable=False)
    access_token = db.Column(db.Text, nullable=False)
    refresh_token = db.Column(db.Text)
    expires_at = db.Column(db.DateTime)
    lapse_user_id = db.Column(db.String(64))
    lapse_handle = db.Column(db.String(64))
    connected_at = db.Column(db.DateTime, default=club_now)

    member = db.relationship(
        "Member",
        backref=db.backref("lapse_connection", uselist=False, cascade="all, delete-orphan"),
    )