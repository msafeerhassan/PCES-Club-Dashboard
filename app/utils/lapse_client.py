from datetime import datetime, time

import requests
from flask import current_app

from app.utils.timeutil import CLUB_TZ

MODES = ("HACKATIME", "BOTH", "LAPSE")
MODE_LABELS = {
    "HACKATIME": "Hackatime only",
    "BOTH": "Hackatime + Lapse",
    "LAPSE": "Lapse only",
}


class LapseAuthError(Exception):
    pass


def needs_lapse(mode):
    return mode in ("BOTH", "LAPSE")


def clean_mode(raw):
    raw = (raw or "").strip().upper()
    return raw if raw in MODES else "HACKATIME"


def _to_ms(dt):
    """Naive club-time datetime -> epoch milliseconds."""
    return int(dt.replace(tzinfo=CLUB_TZ).timestamp() * 1000)


def _from_ms(ms):
    """Epoch milliseconds -> naive club-time datetime."""
    return datetime.fromtimestamp(ms / 1000, CLUB_TZ).replace(tzinfo=None)


def challenge_window(challenge, now):
    start = datetime.combine(challenge.release_date, time.min)
    return start, max(challenge.deadline, now)


def event_window(event, now):
    start = datetime.combine(event.event_date, time.min)
    end = max(event.submission_deadline, now) if event.submission_deadline else now
    return start, end


def list_published(token, max_pages=5):
    base = current_app.config["LAPSE_API_BASE"]
    headers = {"Authorization": f"Bearer {token}"}
    out, cursor = [], None
    for _ in range(max_pages):
        params = {"limit": 100}
        if cursor:
            params["cursor"] = cursor
        r = requests.get(base + "/timelapse/myPublishedTimelapses",
                         params=params, headers=headers, timeout=10)
        if r.status_code == 401:
            raise LapseAuthError()
        r.raise_for_status()
        data = r.json()["data"]
        out.extend(data["timelapses"])
        cursor = data.get("nextCursor")
        if not cursor:
            break
    return out


def timelapse_options(connection):
    """For the picker on submit pages. Returns (options, error_text)."""
    if not connection:
        return [], None
    try:
        items = list_published(connection.access_token)
    except LapseAuthError:
        return [], "Your Lapse login expired. Reconnect Lapse."
    except Exception:
        return [], "Could not reach Lapse right now."
    options = []
    for t in sorted(items, key=lambda x: x.get("createdAt") or 0, reverse=True):
        options.append({
            "id": t.get("id"),
            "name": t.get("name") or "Untitled",
            "minutes": round((t.get("duration") or 0) / 60),
            "created": _from_ms(t["createdAt"]).strftime("%b %d, %H:%M") if t.get("createdAt") else "?",
            "project": (t.get("private") or {}).get("hackatimeProject"),
            "visibility": t.get("visibility"),
        })
    return options, None


def verify_timelapse(connection, timelapse_id, project_name, window_start, window_end):
    """Return dict(status, note, duration, playback_url, name). Never raises."""
    empty = {"duration": None, "playback_url": None, "name": None}
    if not connection:
        return {**empty, "status": "NOT_CONNECTED", "note": "Member has not connected Lapse."}
    if not timelapse_id:
        return {**empty, "status": "FAILED", "note": "No timelapse selected."}
    try:
        items = list_published(connection.access_token)
    except LapseAuthError:
        return {**empty, "status": "ERROR", "note": "Lapse login expired; member must reconnect."}
    except Exception:
        return {**empty, "status": "ERROR", "note": "Could not reach Lapse."}

    t = next((x for x in items if x.get("id") == timelapse_id), None)
    if not t:
        return {**empty, "status": "FAILED", "note": "Timelapse not found on this member's Lapse account."}

    problems = []
    if t.get("visibility") != "PUBLIC":
        problems.append("not PUBLIC")
    if not t.get("playbackUrl"):
        problems.append("video still processing")
    created = t.get("createdAt") or 0
    if not (_to_ms(window_start) <= created <= _to_ms(window_end)):
        problems.append("created outside the allowed window")
    linked = ((t.get("private") or {}).get("hackatimeProject") or "").strip().lower()
    if not linked or linked != (project_name or "").strip().lower():
        problems.append("not linked to the submitted Hackatime project")

    return {
        "status": "FAILED" if problems else "VERIFIED",
        "note": ("; ".join(problems))[:255] if problems else "All Lapse checks passed.",
        "duration": int(t.get("duration") or 0),
        "playback_url": t.get("playbackUrl"),
        "name": (t.get("name") or "")[:200],
    }


def apply_lapse(record, mode, member, timelapse_id, project_name, window):
    """Run verification and store the result on a Submission or ChallengeSubmission.
    Returns the result dict, or None when the mode does not use Lapse."""
    if not needs_lapse(mode):
        record.lapse_timelapse_id = None
        record.lapse_status = None
        record.lapse_note = None
        record.lapse_duration = None
        record.lapse_playback_url = None
        record.lapse_title = None
        return None
    result = verify_timelapse(member.lapse_connection, timelapse_id, project_name, window[0], window[1])
    record.lapse_timelapse_id = (timelapse_id or None)
    record.lapse_status = result["status"]
    record.lapse_note = result["note"]
    record.lapse_duration = result["duration"]
    record.lapse_playback_url = result["playback_url"]
    record.lapse_title = result["name"]
    return result