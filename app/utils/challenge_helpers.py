from app.models.challenge_submission import ChallengeSubmission
from app.utils.timeutil import club_now


def get_eligible_departments(member, challenge):
    if challenge.is_club_wide:
        return list(member.departments)
    challenge_dept_ids = {d.id for d in challenge.departments}
    return [d for d in member.departments if d.id in challenge_dept_ids]


def format_time_left(delta):
    total = int(delta.total_seconds())
    if total <= 0:
        return "Overdue"
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days:
        return f"{days}d {hours}h left"
    if hours:
        return f"{hours}h {minutes}m left"
    return f"{minutes}m left"


def get_member_challenge_state(member, challenge):
    submission = ChallengeSubmission.query.filter_by(challenge_id=challenge.id, member_id=member.id).first()
    now = club_now()
    overdue = now > challenge.deadline

    if submission is not None and submission.is_judged:
        state = "judged"
    elif submission is not None:
        state = "submitted"
    elif overdue:
        state = "overdue"
    else:
        state = "open"

    return {
        "state": state,
        "submission": submission,
        "overdue": overdue,
        "time_left": format_time_left(challenge.deadline - now),
        "can_submit": bool(get_eligible_departments(member, challenge)),
    }


def compute_challenge_streak(member):
    from app.models.challenge import Challenge

    now = club_now()
    submitted_ids = {s.challenge_id for s in ChallengeSubmission.query.filter_by(member_id=member.id).all()}
    member_dept_ids = {d.id for d in member.departments}

    streak = 0
    for c in Challenge.query.order_by(Challenge.release_date.desc(), Challenge.id.desc()).all():
        if not (c.is_club_wide or member_dept_ids & {d.id for d in c.departments}):
            continue
        if c.id in submitted_ids:
            streak += 1
        elif now <= c.deadline:
            continue  # still open, so it doesn't break the streak yet
        else:
            break
    return streak