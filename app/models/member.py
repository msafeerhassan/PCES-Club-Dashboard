from datetime import datetime
from flask_login import UserMixin
from app.extensions import db
from app.models.enums import RoleEnum


class Member(db.Model, UserMixin):
    __tablename__ = "members"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    role = db.Column(db.Enum(RoleEnum), nullable=False, default=RoleEnum.MEMBER)

    hca_sub = db.Column(db.String(255), unique=True, nullable=True)
    is_active_account = db.Column(db.Boolean, default=False, nullable=False)
    is_disabled = db.Column(db.Boolean, default=False, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    disabled_reason = db.Column(db.Text, nullable=True)
    disabled_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def get_id(self):
        return str(self.id)

    departments = db.relationship("Department", secondary="member_departments", back_populates="members")