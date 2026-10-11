import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from app.config import Config
import os
from app.extensions import db, login_manager, oauth, csrf, limiter
def create_app(config_override=None):
    app = Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    if Config.SENTRY_DSN:
        sentry_sdk.init(
            dsn=Config.SENTRY_DSN,
            integrations=[FlaskIntegration()],
            traces_sample_rate=0.1,
                        environment= os.environ.get("VERCEL_ENV", "development"),
        )

    app.config.from_object(Config)

    app.config.update(config_override or {})

    db.init_app(app)
    login_manager.init_app(app)
    oauth.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = None

    from app.utils.permissions import department_names_for_viewer, can_manage_event, can_manage_challenge
    app.jinja_env.globals["dept_names_for_viewer"] = department_names_for_viewer
    app.jinja_env.globals["can_manage_event"] = can_manage_event
    app.jinja_env.globals["can_manage_challenge"] = can_manage_challenge
    from app import models  # noqa: F401 -- registers models with SQLAlchemy
    from app import utils  # noqa: F401
    from app.utils.login import load_user  # noqa: F401 -- registers user_loader
    from app.utils.oauth_clients import register_oauth_clients

    register_oauth_clients(oauth, app)

    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.admin import admin_bp
    from app.routes.hackatime import hackatime_bp

    from app.routes.events import events_bp
    from app.routes.attendance import attendance_bp
    from app.routes.submissions import submissions_bp
    from app.routes.activity import activity_bp
    from app.routes.reports import reports_bp
    from app.routes.profile import profile_bp
    from app.routes.announcements import announcements_bp
    from app.routes.resources import resources_bp
    from app.routes.departments import departments_bp
    from app.routes.leaderboard import leaderboard_bp
    from app.routes.achievements import achievements_bp
    from app.routes.challenges import challenges_bp
    from app.routes.challenge_submissions import challenge_submissions_bp
    from app.routes.challenge_judging import challenge_judging_bp
    from app.routes.challenge_leaderboard import challenge_leaderboard_bp
    from app.routes.department_rankings import department_rankings_bp
    from app.routes.internal_cron import internal_cron_bp
    from app.utils.lapse_oauth import init_lapse_oauth
    from app.routes.lapse import bp as lapse_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(hackatime_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(submissions_bp)
    app.register_blueprint(activity_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(announcements_bp)
    app.register_blueprint(resources_bp)
    app.register_blueprint(departments_bp)
    app.register_blueprint(leaderboard_bp)
    app.register_blueprint(achievements_bp)
    app.register_blueprint(challenges_bp)
    app.register_blueprint(challenge_submissions_bp)
    app.register_blueprint(challenge_judging_bp)
    app.register_blueprint(challenge_leaderboard_bp)
    app.register_blueprint(department_rankings_bp)
    app.register_blueprint(internal_cron_bp)
    csrf.exempt(internal_cron_bp)

    from app.routes.errors import register_error_handlers
    register_error_handlers(app)

    @app.after_request
    def security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return resp
    app.register_blueprint(lapse_bp)
    init_lapse_oauth(app)

    return app