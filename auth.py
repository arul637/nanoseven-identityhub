from functools import wraps
from datetime import datetime, timedelta
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
)
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db
from config import Config

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "admin_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def get_admin_count():
    with get_db() as db:
        row = db.execute("SELECT COUNT(*) as count FROM admins").fetchone()
        return row["count"] if row else 0


def is_locked(username):
    with get_db() as db:
        cutoff = datetime.utcnow() - timedelta(minutes=Config.ACCOUNT_LOCKOUT_MINUTES)
        attempts = db.execute(
            "SELECT COUNT(*) as cnt FROM login_attempts WHERE username=? AND success=0 AND created_at > ?",
            (username, cutoff.isoformat()),
        ).fetchone()
        return attempts and attempts["cnt"] >= Config.MAX_LOGIN_ATTEMPTS


def log_login_attempt(username, success, ip=""):
    with get_db() as db:
        db.execute(
            "INSERT INTO login_attempts (username, ip_address, success) VALUES (?, ?, ?)",
            (username, ip, 1 if success else 0),
        )


@auth_bp.route("/setup", methods=["GET", "POST"])
def setup():
    if get_admin_count() > 0:
        flash("Administrator already exists.", "info")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if not username or not password:
            flash("Username and password are required.", "danger")
            return render_template("setup.html")

        if len(username) < 3:
            flash("Username must be at least 3 characters.", "danger")
            return render_template("setup.html")

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("setup.html")

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "danger")
            return render_template("setup.html")

        pw_hash = generate_password_hash(password)
        with get_db() as db:
            try:
                db.execute(
                    "INSERT INTO admins (username, password_hash) VALUES (?, ?)",
                    (username, pw_hash),
                )
                flash("Administrator created successfully. Please log in.", "success")
                return redirect(url_for("auth.login"))
            except Exception as e:
                flash(f"Error creating admin: {str(e)}", "danger")

    return render_template("setup.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if get_admin_count() == 0:
        return redirect(url_for("auth.setup"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        ip = request.remote_addr or ""

        if is_locked(username):
            log_login_attempt(username, False, ip)
            flash(
                f"Account locked due to too many failed attempts. Try again in {Config.ACCOUNT_LOCKOUT_MINUTES} minutes.",
                "danger",
            )
            return render_template("login.html")

        admin = None
        with get_db() as db:
            admin = db.execute(
                "SELECT * FROM admins WHERE username = ?", (username,)
            ).fetchone()

        if admin and check_password_hash(admin["password_hash"], password):
            session["admin_id"] = admin["id"]
            session["admin_username"] = admin["username"]
            session.permanent = True
            with get_db() as db:
                db.execute(
                    "UPDATE admins SET last_login = ? WHERE id = ?",
                    (datetime.utcnow().isoformat(), admin["id"]),
                )
            log_login_attempt(username, True, ip)
            flash(f"Welcome back, {username}!", "success")
            return redirect(url_for("dashboard.index"))
        else:
            log_login_attempt(username, False, ip)
            flash("Invalid username or password.", "danger")

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/check_setup")
def check_setup():
    return jsonify({"needs_setup": get_admin_count() == 0})
