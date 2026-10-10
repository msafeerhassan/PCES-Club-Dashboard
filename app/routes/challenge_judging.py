from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models.challenge_submission import ChallengeSubmission
from app.models.department import Department
from app.utils.permissions import ADMIN_ROLES, can_manage_challenge_submission, assignable_departments

challenge_judging_bp = Blueprint("challenge_judging", __name__, url_prefix="/challenges")


@challenge_judging_bp.route("/judge")
@login_required
def judge_list():
    if current_user.role not in ADMIN_ROLES:
        abort(403)

    if current_user.role.value == "president":
        submissions = ChallengeSubmission.query.order_by(ChallengeSubmission.submitted_at.desc()).all()
    else:
        dept_ids = [d.id for d in assignable_departments(current_user)]
        submissions = ChallengeSubmission.query.filter(
            ChallengeSubmission.department_id.in_(dept_ids)
        ).order_by(ChallengeSubmission.submitted_at.desc()).all()

    return render_template("challenges/judge_list.html", submissions=submissions)


def _score(field):
    try:
        value = int(request.form.get(field, 0))
    except (TypeError, ValueError):
        value = 0
    return max(0, min(5, value))


def _hackatime_evidence(submission):
    from app.extensions import oauth
    from app.utils.hackatime_client import get_projects

    conn = submission.member.hackatime_connection
    if not conn or not submission.hackatime_project_name:
        return None, None

    for p in get_projects(oauth, conn):
        if p.get("name") == submission.hackatime_project_name:
            active = None
            try:
                last = datetime.fromisoformat(p["most_recent_heartbeat"].replace("Z", "+00:00"))
                active = last.date() >= submission.challenge.release_date
            except (KeyError, ValueError, AttributeError, TypeError):
                pass
            return p, active
    return None, None


@challenge_judging_bp.route("/judge/<int:submission_id>", methods=["GET", "POST"])
@login_required
def judge_submission(submission_id):
    import sentry_sdk
    from app.utils.achievements import check_and_award_all

    submission = ChallengeSubmission.query.get_or_404(submission_id)
    if not can_manage_challenge_submission(current_user, submission):
        abort(403)

    if request.method == "POST":
        was_judged = submission.is_judged

        submission.functionality_score = _score("functionality_score")
        submission.complexity_score = _score("complexity_score")
        submission.creativity_score = _score("creativity_score")
        submission.quality_score = _score("quality_score")
        submission.late_penalty_waived = request.form.get("waive_penalty") == "on"
        submission.judge_feedback = request.form.get("feedback", "").strip() or None
        submission.is_judged = True
        submission.judged_by_id = current_user.id
        submission.judged_at = datetime.utcnow()
        db.session.commit()

        if not was_judged:
            from app.utils.discord_notify import notify_scoped
            notify_scoped(
                False, [submission.department],
                "📊 Challenge Judged", f"**{submission.member.name}** scored **{submission.total_score}/20** on **{submission.challenge.title}**",
                color=0x33D6A6,
            )

        _check_rank_climb(submission.department)

        try:
            check_and_award_all(submission.member, departments=[submission.department])
        except Exception as exc:
            sentry_sdk.capture_exception(exc)

        return redirect(url_for("challenge_judging.judge_list"))

    evidence, evidence_active = _hackatime_evidence(submission)
    return render_template(
        "challenges/judge_form.html", submission=submission,
        evidence=evidence, evidence_active=evidence_active,
    )

def _check_rank_climb(department):
    from app.models.rank_snapshot import ChallengeRankSnapshot
    from app.utils.discord_notify import notify_scoped

    judged = ChallengeSubmission.query.filter_by(department_id=department.id, is_judged=True).all()
    totals = {}
    for s in judged:
        totals[s.member_id] = totals.get(s.member_id, 0) + s.total_score

    ranked = sorted(totals.items(), key=lambda x: x[1], reverse=True)
    new_ranks = {member_id: i + 1 for i, (member_id, _) in enumerate(ranked)}

    old_snapshots = {
        s.member_id: s for s in ChallengeRankSnapshot.query.filter_by(department_id=department.id).all()
    }

    for member_id, new_rank in new_ranks.items():
        old = old_snapshots.get(member_id)
        if old and new_rank < old.rank:
            overtaken_id = next((m for m, r in new_ranks.items() if r == new_rank + 1), None)
            if overtaken_id and old_snapshots.get(overtaken_id) and old_snapshots[overtaken_id].rank <= old.rank:
                from app.models.member import Member
                climber = Member.query.get(member_id)
                overtaken = Member.query.get(overtaken_id)
                if climber and overtaken:
                    notify_scoped(
                        False, [department],
                        "📈 Rank Climb", f"**{climber.name}** has overtaken **{overtaken.name}** on the Challenge Leaderboard — now **#{new_rank}**!",
                        color=0xFF8C37,
                    )
            db.session.merge(ChallengeRankSnapshot(department_id=department.id, member_id=member_id, rank=new_rank))
        elif not old:
            db.session.add(ChallengeRankSnapshot(department_id=department.id, member_id=member_id, rank=new_rank))
        else:
            old.rank = new_rank

    db.session.commit()