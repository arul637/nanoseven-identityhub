import os
from flask import Flask, redirect, url_for, session
from dotenv import load_dotenv

load_dotenv()

from config import Config
from database import init_db, init_default_policies


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.secret_key = Config.SECRET_KEY

    init_db()
    init_default_policies()

    from auth import auth_bp
    from dashboard import dashboard_bp
    from user_management import user_bp
    from group_management import group_bp
    from security_policy import security_bp
    from system_sync import sync_bp
    from audit_logs import audit_bp
    from system_info import system_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(group_bp)
    app.register_blueprint(security_bp)
    app.register_blueprint(sync_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(system_bp)

    @app.route("/")
    def index():
        if "admin_id" in session:
            return redirect(url_for("dashboard.index"))
        return redirect(url_for("auth.login"))

    @app.context_processor
    def inject_globals():
        from config import Config as Cfg
        return {
            "mock_mode": Cfg.MOCK_MODE,
            "current_admin": session.get("admin_username", ""),
        }

    return app


if __name__ == "__main__":
    app = create_app()
    mode = "MOCK MODE" if Config.MOCK_MODE else "LIVE SYSTEM MODE"
    print(f"Starting Linux User & Group Manager - {mode}")
    app.run(debug=Config.DEBUG, host="0.0.0.0", port=5000)
