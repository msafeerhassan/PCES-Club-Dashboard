from datetime import datetime
from app.extensions import db


class ChallengeRankSnapshot(db.Model):
    __tablename__ = "challenge_rank_snapshots"
    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=False)
    rank = db.Column(db.Integer, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (db.UniqueConstraint("department_id", "member_id", name="uq_dept_member_rank"),)


class DepartmentRankSnapshot(db.Model):
    __tablename__ = "department_rank_snapshots"
    id = db.Column(db.Integer, primary_key=True)
    metric = db.Column(db.String(20), nullable=False)  # 'hours' | 'shipped' | 'points'
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False)
    rank = db.Column(db.Integer, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (db.UniqueConstraint("metric", "department_id", name="uq_metric_dept_rank"),)