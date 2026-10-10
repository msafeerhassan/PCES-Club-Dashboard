from datetime import datetime, timedelta
from app.models.event import Event
from app.models.submission import Submission
from app.utils.timeutil import club_now

def get_eligible_events(member):
    from app.utils.permissions import can_view_event
    return [e for e in Event.query.all() if can_view_event(member, e)]


def get_upcoming_events(member, limit=5):
    today = club_now().date()
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
    now = club_now()
    for e in eligible:
        if e.submission_deadline and e.id not in submitted_event_ids:
            time_left = e.submission_deadline - now
            if timedelta(0) < time_left < timedelta(days=3):
                tasks.append(f"Submission due soon for '{e.title}'")

    if previous_login:
        new_events = [e for e in eligible if e.created_at > previous_login]
        for e in new_events:
            tasks.append(f"New event: '{e.title}'")

    from app.models.challenge import Challenge
    from app.utils.challenge_helpers import get_member_challenge_state
    from app.utils.permissions import can_view_challenge
    now_local = club_now()
    for c in Challenge.query.filter(Challenge.deadline >= now_local).order_by(Challenge.deadline).all():
        if not can_view_challenge(member, c):
            continue
        st = get_member_challenge_state(member, c)
        if st["state"] == "open" and st["can_submit"] and (c.deadline - now_local) <= timedelta(days=3):
            tasks.append(f"Challenge due soon: '{c.title}' ({st['time_left']})")

    return tasks

def get_peer_members(member):
    from app.models.member import Member
    from app.models.department import Department
    from app.models.enums import RoleEnum

    dept_ids = [d.id for d in member.departments]
    if dept_ids:
        return Member.query.filter(
            Member.departments.any(Department.id.in_(dept_ids)), Member.role == RoleEnum.MEMBER
        ).all()
    return Member.query.filter_by(role=RoleEnum.MEMBER).all()