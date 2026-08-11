from datetime import datetime
from app.extensions import db


class Attendance(db.Model):
    __tablename__ = "attendance"

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=False)

    present = db.Column(db.Boolean, default=False, nullable=False)
    marked_by_id = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=False)
    marked_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    event = db.relationship("Event", backref="attendance_records")
    member = db.relationship("Member", foreign_keys=[member_id])
    marked_by = db.relationship("Member", foreign_keys=[marked_by_id])

    __table_args__ = (
        db.UniqueConstraint("event_id", "member_id", name="uq_event_member"),
    )