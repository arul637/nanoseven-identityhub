import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", os.urandom(32).hex())
    DATABASE_PATH = os.path.join(basedir, "database", "linux_manager.db")
    DEBUG = os.environ.get("FLASK_DEBUG", "True").lower() == "true"
    MOCK_MODE = os.environ.get("MOCK_MODE", "True").lower() == "true"
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = os.environ.get("PORT", 5000)
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 3600
    MAX_LOGIN_ATTEMPTS = 5
    ACCOUNT_LOCKOUT_MINUTES = 15
    COMMAND_TIMEOUT = 30
