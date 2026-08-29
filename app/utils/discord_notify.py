import requests
from flask import current_app


def _post(channel_id, embed, ping=False):
    if not channel_id:
        return
    token = current_app.config.get("DISCORD_BOT_TOKEN")
    if not token:
        return

    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {"Authorization": f"Bot {token}", "Content-Type": "application/json"}
    payload = {"embeds": [embed]}
    if ping:
        payload["content"] = "@everyone"
        payload["allowed_mentions"] = {"parse": ["everyone"]}

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=5)
        print(f"[DISCORD DEBUG] channel={channel_id} status={resp.status_code} body={resp.text}")
    except requests.RequestException as e:
        print(f"[DISCORD DEBUG] request failed: {e}")


def notify_scoped(is_club_wide, departments, title, description, color=0xEC3750, ping=False):
    embed = {"title": title, "description": description, "color": color}

    if is_club_wide:
        _post(current_app.config.get("DISCORD_CLUBWIDE_CHANNEL_ID"), embed, ping=ping)
        return

    seen = set()
    for d in departments:
        if d.discord_channel_id and d.discord_channel_id not in seen:
            seen.add(d.discord_channel_id)
            _post(d.discord_channel_id, embed, ping=ping)