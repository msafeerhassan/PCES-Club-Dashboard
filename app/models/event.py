from datetime import datetime
from app.extensions import db
from app.models.enums import EventScopeEnum


class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    scope = db.Column(db.Enum(EventScopeEnum), nullable=False, default=EventScopeEnum.CLUB_WIDE)

    event_date = db.Column(db.Date, nullable=False)
    submission_deadline = db.Column(db.DateTime, nullable=True)

    created_by_id = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    created_by = db.relationship("Member")