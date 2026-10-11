from datetime import datetime
from app.extensions import db


class Challenge(db.Model):
    __tablename__ = "challenges"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    theme = db.Column(db.String(150), nullable=False)
    technology = db.Column(db.String(100), nullable=False)
    objective = db.Column(db.Text, nullable=False)
    submission_requirements = db.Column(db.Text, nullable=False)

    is_club_wide = db.Column(db.Boolean, nullable=False, default=True)
    release_date = db.Column(db.Date, nullable=False)
    deadline = db.Column(db.DateTime, nullable=False)
    verification_mode = db.Column(db.String(12), nullable=False, default="HACKATIME", server_default="HACKATIME")
    created_by_id = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    created_by = db.relationship("Member")
    departments = db.relationship("Department", secondary="challenge_departments", backref="challenges")