from app.extensions import db, oauth
from app.models.achievement import Achievement
from app.models.member_achievement import MemberAchievement
from app.models.submission import Submission
from app.models.attendance import Attendance
from app.models.enums import SubmissionStatus
from app.utils.hackatime_client import get_hours, get_streak, update_longest_streak


def _award(member, key):
    achievement = Achievement.query.filter_by(key=key).first()
    if achievement is None:
        return
    existing = MemberAchievement.query.filter_by(member_id=member.id, achievement_id=achievement.id).first()
    if existing is not None:
        return
    db.session.add(MemberAchievement(member_id=member.id, achievement_id=achievement.id))
    db.session.commit()

    from app.utils.discord_notify import notify_scoped
    notify_scoped(
        False, member.departments,
        "🏆 Achievement Unlocked", f"**{member.name}** earned **{achievement.name}**!", color=0xD4AF37,
    )


def check_and_award_all(member):
    approved_count = Submission.query.filter_by(member_id=member.id, status=SubmissionStatus.APPROVED).count()
    if approved_count >= 1:
        _award(member, "first_ship")
    if approved_count >= 5:
        _award(member, "shipper")

    attendance_records = Attendance.query.filter_by(member_id=member.id).all()
    total_marked = len(attendance_records)
    attended = sum(1 for a in attendance_records if a.present)
    if total_marked >= 3 and attended == total_marked:
        _award(member, "perfect_attendance")

    connection = member.hackatime_connection
    if connection:
        streak = get_streak(oauth, connection)
        if streak:
            update_longest_streak(db, connection, streak.get("streak_days"))
        if connection.longest_streak_seen >= 7:
            _award(member, "consistent")
        if connection.longest_streak_seen >= 30:
            _award(member, "dedicated")

        all_time = get_hours(oauth, connection)
        if all_time and all_time.get("total_seconds", 0) >= 100 * 3600:
            _award(member, "century_club")