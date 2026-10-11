import io


def _login(client, member):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(member.id)
        sess["_fresh"] = True


def test_cron_requires_secret(app):
    client = app.test_client()
    assert client.get("/internal/cron/weekly-standings").status_code == 403
    assert client.get("/internal/cron/weekly-standings",
                      headers={"Authorization": "Bearer wrong"}).status_code == 403


def test_styled_404(app):
    r = app.test_client().get("/definitely-not-a-page")
    assert r.status_code == 404
    assert b"Not found" in r.data


def test_security_headers(app):
    r = app.test_client().get("/definitely-not-a-page")
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["X-Content-Type-Options"] == "nosniff"


def test_upload_rejects_bad_type():
    from app.utils.uploads import validate_uploads
    from werkzeug.datastructures import FileStorage
    bad = FileStorage(stream=io.BytesIO(b"x"), filename="virus.exe")
    ok = FileStorage(stream=io.BytesIO(b"x"), filename="notes.pdf")
    assert "not allowed" in validate_uploads([bad])
    assert validate_uploads([ok]) is None


def test_upload_rejects_oversize():
    from app.utils.uploads import validate_uploads
    from werkzeug.datastructures import FileStorage
    big = FileStorage(stream=io.BytesIO(b"0" * (4 * 1024 * 1024 + 1)), filename="big.pdf")
    assert "4 MB" in validate_uploads([big])


def test_csrf_blocks_post_without_token(app, president):
    app.config["WTF_CSRF_ENABLED"] = True
    client = app.test_client()
    _login(client, president)
    r = client.post("/events/1/delete")
    assert r.status_code == 400


def test_logged_in_user_sees_styled_404(app, president):
    client = app.test_client()
    _login(client, president)
    r = client.get("/definitely-not-a-page")
    assert r.status_code == 404
    assert b"Not found" in r.data


def test_every_post_form_has_csrf_token():
    import pathlib, re
    form_re = re.compile(r"<form\b[^>]*\bmethod\s*=\s*[\"']post[\"'][^>]*>(.*?)</form>", re.I | re.S)
    missing = []
    for p in pathlib.Path("app/templates").rglob("*.html"):
        for m in form_re.finditer(p.read_text(encoding="utf-8")):
            if "csrf_token" not in m.group(1):
                missing.append(str(p))
    assert not missing, missing