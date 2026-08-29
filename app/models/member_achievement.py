from datetime import datetime
from app.extensions import db


class MemberAchievement(db.Model):
    __tablename__ = "member_achievements"

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey("achievements.id"), nullable=False)
    earned_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    awarded_by_id = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=True)  # set only for manual awards

    member = db.relationship("Member", foreign_keys=[member_id], backref="achievements")
    achievement = db.relationship("Achievement")
    awarded_by = db.relationship("Member", foreign_keys=[awarded_by_id])

    __table_args__ = (db.UniqueConstraint("member_id", "achievement_id", name="uq_member_achievement"),)