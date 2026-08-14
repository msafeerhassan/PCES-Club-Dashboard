from flask import Flask
from app.config import Config
from app.extensions import db, login_manager, oauth


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    oauth.init_app(app)

    login_manager.login_view = "auth.login"

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

    return app