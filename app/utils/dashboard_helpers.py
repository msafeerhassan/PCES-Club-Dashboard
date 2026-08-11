from datetime import datetime, timedelta
from app.models.event import Event
from app.models.submission import Submission
from app.models.enums import EventScopeEnum


def get_eligible_events(member):
    return [
        e for e in Event.query.all()
        if e.scope == EventScopeEnum.CLUB_WIDE or (member.section and e.scope.value == member.section.value)
    ]


def get_upcoming_events(member, limit=5):
    today = datetime.utcnow().date()
    events = [e for e in get_eligible_events(member) if e.event_date >= today]
    events.sort(key=lambda e: e.event_date)
    return events[:limit]


def get_pending_tasks(member, previous_login=None):
    tasks = []

    if member.hackatime_connection is None:
        tasks.append("Connect your Hackatime account")

    eligible = get_eligible_events(member)
    submitted_event_ids = {
        s.event_id for s in Submission.query.filter_by(member_id=member.id).all() if s.event_id
    }
    now = datetime.utcnow()
    for e in eligible:
        if e.submission_deadline and e.id not in submitted_event_ids:
            time_left = e.submission_deadline - now
            if timedelta(0) < time_left < timedelta(days=3):
                tasks.append(f"Submission due soon for '{e.title}'")

    if previous_login:
        new_events = [e for e in eligible if e.created_at > previous_login]
        for e in new_events:
            tasks.append(f"New event: '{e.title}'")

    return tasks

def get_peer_members(member):
    from app.models.member import Member
    from app.models.enums import RoleEnum

    if member.section is not None:
        return Member.query.filter_by(section=member.section, role=RoleEnum.MEMBER).all()
    return Member.query.filter_by(role=RoleEnum.MEMBER).all()