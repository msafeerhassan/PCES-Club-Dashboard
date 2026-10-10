from datetime import datetime
from app.extensions import db


class ChallengeSubmission(db.Model):
    __tablename__ = "challenge_submissions"

    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey("challenges.id"), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False)

    github_url = db.Column(db.String(500), nullable=True)
    demo_url = db.Column(db.String(500), nullable=True)
    hackatime_project_name = db.Column(db.String(255), nullable=True)

    submitted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_late = db.Column(db.Boolean, nullable=False, default=False)
    late_reason = db.Column(db.Text, nullable=True)

    is_judged = db.Column(db.Boolean, nullable=False, default=False)
    functionality_score = db.Column(db.Integer, nullable=True)
    complexity_score = db.Column(db.Integer, nullable=True)
    creativity_score = db.Column(db.Integer, nullable=True)
    quality_score = db.Column(db.Integer, nullable=True)
    late_penalty_waived = db.Column(db.Boolean, nullable=False, default=False)
    judge_feedback = db.Column(db.Text, nullable=True)
    judged_by_id = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=True)
    judged_at = db.Column(db.DateTime, nullable=True)

    challenge = db.relationship("Challenge", backref="submissions")
    member = db.relationship("Member", foreign_keys=[member_id], backref="challenge_submissions")
    department = db.relationship("Department")
    judged_by = db.relationship("Member", foreign_keys=[judged_by_id])

    __table_args__ = (db.UniqueConstraint("challenge_id", "member_id", name="uq_challenge_member"),)

    @property
    def total_score(self):
        if not self.is_judged:
            return None
        base = (self.functionality_score or 0) + (self.complexity_score or 0) + (self.creativity_score or 0) + (self.quality_score or 0)
        if self.is_late and not self.late_penalty_waived:
            base -= 2
        return max(base, 0)