from datetime import datetime
from app.extensions import db


class Submission(db.Model):
    __tablename__ = "submissions"

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=True)  # null = standalone/personal

    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    hackatime_project_name = db.Column(db.String(255), nullable=True)
    demo_url = db.Column(db.String(500), nullable=True)
    github_url = db.Column(db.String(500), nullable=True)

    submitted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_featured = db.Column(db.Boolean, default=False, nullable=False)
    member = db.relationship("Member", backref="submissions")
    event = db.relationship("Event", backref="submissions")

    @property
    def is_late(self):
        if self.event is None or self.event.submission_deadline is None:
            return False
        return self.submitted_at > self.event.submission_deadline