from datetime import datetime
from app.extensions import db


class SubmissionFile(db.Model):
    __tablename__ = "submission_files"

    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey("submissions.id"), nullable=False)

    file_url = db.Column(db.String(500), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    submission = db.relationship("Submission", backref="files")