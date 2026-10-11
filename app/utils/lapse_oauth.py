from authlib.integrations.flask_client import OAuth

lapse_oauth = OAuth()


def init_lapse_oauth(app):
    lapse_oauth.init_app(app)
    lapse_oauth.register(
        name="lapse",
        client_id=app.config.get("LAPSE_CLIENT_ID"),
        client_secret=app.config.get("LAPSE_CLIENT_SECRET"),
        authorize_url="https://api.lapse.hackclub.com/api/auth/authorize",
        access_token_url="https://api.lapse.hackclub.com/api/auth/token",
        client_kwargs={
            "scope": "user:read timelapse:read",
            "code_challenge_method": "S256",
            "token_endpoint_auth_method": "client_secret_post",
        },
    )