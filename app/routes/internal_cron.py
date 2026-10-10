from flask import Blueprint, request, abort, current_app
from app.models.department import Department
from app.models.challenge_submission import ChallengeSubmission
from app.utils.discord_notify import notify_scoped

internal_cron_bp = Blueprint("internal_cron", __name__, url_prefix="/internal/cron")


@internal_cron_bp.route("/weekly-standings")
def weekly_standings():
    _check_department_rank_climbs()
    return {"status": "ok"}, 200


def _check_department_rank_climbs():
    from app.extensions import oauth, db
    from app.models.member import Member
    from app.models.submission import Submission
    from app.models.enums import SubmissionStatus, RoleEnum
    from app.models.rank_snapshot import DepartmentRankSnapshot
    from app.utils.hackatime_client import get_hours
    from app.config import Config

    departments = Department.query.order_by(Department.name).all()
    metrics = {}
    for metric in ("hours", "shipped", "points"):
        values = {}
        for d in departments:
            members = Member.query.filter(Member.departments.any(Department.id == d.id), Member.role == RoleEnum.MEMBER).all()
            member_ids = [m.id for m in members]

            if metric == "hours":
                total = 0
                for m in members:
                    conn = m.hackatime_connection
                    if conn:
                        data = get_hours(oauth, conn)
                        if data:
                            total += data.get("total_seconds", 0) / 3600
                values[d.id] = total
            elif metric == "shipped":
                values[d.id] = Submission.query.filter(
                    Submission.member_id.in_(member_ids), Submission.status == SubmissionStatus.APPROVED
                ).count() if member_ids else 0
            else:
                judged = ChallengeSubmission.query.filter(
                    ChallengeSubmission.member_id.in_(member_ids), ChallengeSubmission.is_judged == True
                ).all() if member_ids else []
                values[d.id] = sum(s.total_score for s in judged)

        ranked = sorted(values.items(), key=lambda x: x[1], reverse=True)
        metrics[metric] = {dept_id: i + 1 for i, (dept_id, _) in enumerate(ranked)}

    for metric, new_ranks in metrics.items():
        old_snapshots = {s.department_id: s for s in DepartmentRankSnapshot.query.filter_by(metric=metric).all()}
        for dept_id, new_rank in new_ranks.items():
            old = old_snapshots.get(dept_id)
            if old and new_rank < old.rank:
                overtaken_id = next((d for d, r in new_ranks.items() if r == new_rank + 1), None)
                if overtaken_id and old_snapshots.get(overtaken_id) and old_snapshots[overtaken_id].rank <= old.rank:
                    climber = next((d for d in departments if d.id == dept_id), None)
                    overtaken = next((d for d in departments if d.id == overtaken_id), None)
                    if climber and overtaken:
                        notify_scoped(
                            True, [],
                            "🚀 Department Rank Climb", f"**{climber.name}** has overtaken **{overtaken.name}** in {metric}!",
                            color=0xFF8C37,
                        )
                db.session.merge(DepartmentRankSnapshot(metric=metric, department_id=dept_id, rank=new_rank))
            elif not old:
                db.session.add(DepartmentRankSnapshot(metric=metric, department_id=dept_id, rank=new_rank))
            else:
                old.rank = new_rank

    db.session.commit()

    return {"status": "ok"}, 200