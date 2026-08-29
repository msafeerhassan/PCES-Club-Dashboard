from app.extensions import db

member_departments = db.Table(
    "member_departments",
    db.Column("member_id", db.Integer, db.ForeignKey("members.id"), primary_key=True),
    db.Column("department_id", db.Integer, db.ForeignKey("departments.id"), primary_key=True),
)

event_departments = db.Table(
    "event_departments",
    db.Column("event_id", db.Integer, db.ForeignKey("events.id"), primary_key=True),
    db.Column("department_id", db.Integer, db.ForeignKey("departments.id"), primary_key=True),
)

announcement_departments = db.Table(
    "announcement_departments",
    db.Column("announcement_id", db.Integer, db.ForeignKey("announcements.id"), primary_key=True),
    db.Column("department_id", db.Integer, db.ForeignKey("departments.id"), primary_key=True),
)