from datetime import datetime, timedelta, timezone

CLUB_TZ = timezone(timedelta(hours=5))  # Pakistan Standard Time, UTC+5 (no DST)


def club_now():
    return datetime.now(CLUB_TZ).replace(tzinfo=None)