from datetime import datetime
from app.extensions import db


class Achievement(db.Model):
    __tablename__ = "achievements"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=True)  # set for automatic ones, null for custom
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    glyph = db.Column(db.String(4), nullable=False, default="★")
    color = db.Column(db.String(20), nullable=False, default="red")  # red / orange / blue / green / purple
    is_manual = db.Column(db.Boolean, nullable=False, default=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)