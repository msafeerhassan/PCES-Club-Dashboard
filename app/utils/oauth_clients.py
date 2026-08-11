def register_oauth_clients(oauth, app):
    oauth.register(
        name="hca",
        client_id=app.config["HCA_CLIENT_ID"],
        client_secret=app.config["HCA_CLIENT_SECRET"],
        access_token_url="https://auth.hackclub.com/oauth/token",
        authorize_url="https://auth.hackclub.com/oauth/authorize",
        api_base_url="https://auth.hackclub.com/",
        client_kwargs={"scope": "email name slack_id verification_status"},
    )

    oauth.register(
        name="hackatime",
        client_id=app.config["HACKATIME_CLIENT_ID"],
        client_secret=app.config["HACKATIME_CLIENT_SECRET"],
        access_token_url="https://hackatime.hackclub.com/oauth/token",
        authorize_url="https://hackatime.hackclub.com/oauth/authorize",
        api_base_url="https://hackatime.hackclub.com/",
        client_kwargs={"scope": "profile read"},
    )