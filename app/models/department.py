from datetime import datetime
from app.extensions import db
from app.models.associations import member_departments


class Department(db.Model):
    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    discord_channel_id = db.Column(db.String(30), nullable=True)
    members = db.relationship("Member", secondary=member_departments, back_populates="departments")