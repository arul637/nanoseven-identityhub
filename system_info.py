import platform
import subprocess
from flask import Blueprint, render_template
from auth import login_required
from database import get_db
from config import Config

system_bp = Blueprint("system", __name__, url_prefix="/system")


def get_linux_distro():
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    return line.split("=", 1)[1].strip().strip('"')
    except Exception:
        pass
    try:
        with open("/etc/lsb-release") as f:
            for line in f:
                if line.startswith("DISTRIB_DESCRIPTION="):
                    return line.split("=", 1)[1].strip().strip('"')
    except Exception:
        pass
    return platform.system()


def get_kernel_version():
    return platform.release()


def get_hostname():
    return platform.node()


def get_architecture():
    return platform.machine()


def get_current_user():
    try:
        import getpass
        return getpass.getuser()
    except Exception:
        return "unknown"


@system_bp.route("/")
@login_required
def index():
    with get_db() as db:
        last_sync = db.execute(
            "SELECT created_at FROM sync_history ORDER BY id DESC LIMIT 1"
        ).fetchone()
        user_count = db.execute("SELECT COUNT(*) as c FROM linux_users").fetchone()["c"]
        group_count = db.execute("SELECT COUNT(*) as c FROM linux_groups").fetchone()["c"]

    if Config.MOCK_MODE:
        distro = "Mock Linux Distribution v1.0"
        kernel = "6.1.0-mock-generic"
    else:
        distro = get_linux_distro()
        kernel = get_kernel_version()

    return render_template(
        "system/info.html",
        distro=distro,
        kernel=kernel,
        hostname=get_hostname(),
        arch=get_architecture(),
        current_user=get_current_user(),
        last_sync=last_sync["created_at"] if last_sync else None,
        user_count=user_count,
        group_count=group_count,
        mock_mode=Config.MOCK_MODE,
    )
