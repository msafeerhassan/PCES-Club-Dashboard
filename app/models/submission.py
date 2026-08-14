from datetime import datetime
from app.extensions import db
from app.models.enums import SubmissionStatus


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

    status = db.Column(db.Enum(SubmissionStatus), nullable=False, default=SubmissionStatus.PENDING)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    feedback = db.Column(db.Text, nullable=True)

    member = db.relationship("Member", backref="submissions", foreign_keys=[member_id])
    event = db.relationship("Event", backref="submissions")
    reviewed_by = db.relationship("Member", foreign_keys=[reviewed_by_id])

    @property
    def is_late(self):
        if self.event is None or self.event.submission_deadline is None:
            return False
        return self.submitted_at > self.event.submission_deadline