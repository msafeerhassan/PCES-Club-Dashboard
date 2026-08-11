from datetime import datetime, timezone

ACTIVE_THRESHOLD_SECONDS = 300


def get_hours(oauth, connection, start_date=None, end_date=None):
    params = {}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    resp = oauth.hackatime.get(
        "api/v1/authenticated/hours", token={"access_token": connection.access_token}, params=params
    )
    return resp.json() if resp.status_code == 200 else None


def get_streak(oauth, connection):
    resp = oauth.hackatime.get("api/v1/authenticated/streak", token={"access_token": connection.access_token})
    return resp.json() if resp.status_code == 200 else None


def get_projects(oauth, connection):
    resp = oauth.hackatime.get("api/v1/authenticated/projects", token={"access_token": connection.access_token})
    return resp.json().get("projects", []) if resp.status_code == 200 else []


def get_active_now(oauth, connection):
    resp = oauth.hackatime.get(
        "api/v1/authenticated/heartbeats/latest", token={"access_token": connection.access_token}
    )
    if resp.status_code != 200:
        return False, None

    data = resp.json()
    created_at = data.get("created_at")
    if not created_at:
        return False, None

    last_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    delta = (datetime.now(timezone.utc) - last_time).total_seconds()
    return delta < ACTIVE_THRESHOLD_SECONDS, last_time

from datetime import date, timedelta as td


def get_weekly_trend(oauth, connection):
    trend = []
    today = date.today()
    for i in range(6, -1, -1):
        day = today - td(days=i)
        day_str = day.isoformat()
        data = get_hours(oauth, connection, start_date=day_str, end_date=day_str)
        seconds = data.get("total_seconds") if data else 0
        trend.append({"date": day_str, "hours": round((seconds or 0) / 3600, 1)})
    return trend

def get_latest_heartbeat_details(oauth, connection):
    resp = oauth.hackatime.get(
        "api/v1/authenticated/heartbeats/latest", token={"access_token": connection.access_token}
    )
    if resp.status_code != 200:
        return None
    data = resp.json()
    return {
        "editor": data.get("editor"),
        "operating_system": data.get("operating_system"),
        "time": data.get("created_at"),
    }


def update_longest_streak(db, connection, current_streak_days):
    if current_streak_days and current_streak_days > connection.longest_streak_seen:
        connection.longest_streak_seen = current_streak_days
        db.session.commit()


def get_club_average_hours(oauth, members):
    totals = []
    for m in members:
        conn = m.hackatime_connection
        if conn:
            data = get_hours(oauth, conn)
            if data:
                totals.append(data.get("total_seconds", 0))
    if not totals:
        return 0
    return round((sum(totals) / len(totals)) / 3600, 1)