import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    HCA_CLIENT_ID = os.environ.get("HCA_CLIENT_ID")
    HCA_CLIENT_SECRET = os.environ.get("HCA_CLIENT_SECRET")
    HCA_BASE_URL = os.environ.get("HCA_BASE_URL")
    HCA_REDIRECT_URI = os.environ.get("HCA_REDIRECT_URI")

    HACKATIME_CLIENT_ID = os.environ.get("HACKATIME_CLIENT_ID")
    HACKATIME_CLIENT_SECRET = os.environ.get("HACKATIME_CLIENT_SECRET")
    HACKATIME_BASE_URL = os.environ.get("HACKATIME_BASE_URL")
    HACKATIME_REDIRECT_URI = os.environ.get("HACKATIME_REDIRECT_URI")

    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    SUPABASE_STORAGE_BUCKET = os.environ.get("SUPABASE_STORAGE_BUCKET")

    DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
    DISCORD_CLUBWIDE_CHANNEL_ID = os.environ.get("DISCORD_CLUBWIDE_CHANNEL_ID")
    SENTRY_DSN = os.environ.get("SENTRY_DSN")