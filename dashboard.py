from flask import Blueprint, render_template
from auth import login_required
from database import get_db

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.route("/")
@login_required
def index():
    with get_db() as db:
        total_users = db.execute("SELECT COUNT(*) as c FROM linux_users").fetchone()["c"]
        active_users = db.execute(
            "SELECT COUNT(*) as c FROM linux_users WHERE status='active' AND locked=0"
        ).fetchone()["c"]
        locked_users = db.execute(
            "SELECT COUNT(*) as c FROM linux_users WHERE locked=1"
        ).fetchone()["c"]
        expired_users = db.execute(
            "SELECT COUNT(*) as c FROM linux_users WHERE expired=1"
        ).fetchone()["c"]
        total_groups = db.execute("SELECT COUNT(*) as c FROM linux_groups").fetchone()["c"]
        privileged_groups = db.execute(
            "SELECT COUNT(*) as c FROM linux_groups WHERE privileged=1"
        ).fetchone()["c"]

        recent_logs = db.execute(
            "SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 10"
        ).fetchall()

        last_sync = db.execute(
            "SELECT created_at FROM sync_history ORDER BY id DESC LIMIT 1"
        ).fetchone()

        shell_counts = db.execute(
            "SELECT login_shell, COUNT(*) as cnt FROM linux_users GROUP BY login_shell ORDER BY cnt DESC"
        ).fetchall()

    return render_template(
        "dashboard.html",
        total_users=total_users,
        active_users=active_users,
        locked_users=locked_users,
        expired_users=expired_users,
        total_groups=total_groups,
        privileged_groups=privileged_groups,
        recent_logs=recent_logs,
        last_sync=last_sync["created_at"] if last_sync else None,
        shell_counts=shell_counts,
    )
