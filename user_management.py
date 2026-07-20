import re
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from auth import login_required
from database import get_db
from command_executor import execute, user_exists
from password_security import check_password_strength, generate_password
from config import Config

user_bp = Blueprint("users", __name__, url_prefix="/users")


def audit_log(action, target, description, result="success"):
    from flask import session
    with get_db() as db:
        db.execute(
            "INSERT INTO audit_logs (admin_username, action, target, description, result, ip_address) VALUES (?, ?, ?, ?, ?, ?)",
            (session.get("admin_username", ""), action, target, description, result, ""),
        )


def get_policy(key, default=""):
    with get_db() as db:
        row = db.execute(
            "SELECT policy_value FROM security_policies WHERE policy_key=?", (key,)
        ).fetchone()
        return row["policy_value"] if row else default


def validate_username(username):
    min_len = int(get_policy("min_username_length", "3"))
    max_len = int(get_policy("max_username_length", "32"))
    allowed = get_policy("allowed_username_chars", "a-z0-9_-")
    reserved = get_policy("reserved_usernames", "").split(",")

    if len(username) < min_len:
        return False, f"Username must be at least {min_len} characters."
    if len(username) > max_len:
        return False, f"Username must be at most {max_len} characters."
    if not re.match(f"^[{allowed}]+$", username):
        return False, f"Username can only contain: {allowed}"
    if username.lower() in [r.strip() for r in reserved]:
        return False, f"Username '{username}' is reserved."
    return True, ""


@user_bp.route("/")
@login_required
def index():
    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "").strip()
    uid_filter = request.args.get("uid", "").strip()
    group_filter = request.args.get("group_filter", "").strip()

    with get_db() as db:
        query = """
            SELECT u.*, 
                   (SELECT COUNT(*) FROM user_group_memberships WHERE username=u.username) as group_count
            FROM linux_users u WHERE (u.uid IS NULL OR u.uid != 65534)
        """
        params = []
        if search:
            query += " AND (u.username LIKE ? OR u.full_name LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        if status_filter:
            if status_filter == "locked":
                query += " AND u.locked=1"
            elif status_filter == "active":
                query += " AND u.status='active' AND u.locked=0"
            elif status_filter == "expired":
                query += " AND u.expired=1"
        if uid_filter:
            query += " AND u.uid = ?"
            params.append(uid_filter)
        if group_filter:
            query += " AND u.username IN (SELECT username FROM user_group_memberships WHERE group_name=?)"
            params.append(group_filter)
        query += " ORDER BY u.username ASC"
        users = db.execute(query, params).fetchall()

        all_groups = db.execute(
            "SELECT DISTINCT group_name FROM linux_groups ORDER BY group_name"
        ).fetchall()

    return render_template("users/index.html", users=users, search=search, status=status_filter, uid=uid_filter, group_filter=group_filter, all_groups=all_groups)


@user_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        full_name = request.form.get("full_name", "").strip()
        create_home = request.form.get("create_home", "0") == "1"
        login_shell = request.form.get("login_shell", "").strip()
        primary_group = request.form.get("primary_group", "").strip()
        additional_groups = request.form.get("additional_groups", "").strip()
        account_expires = request.form.get("account_expires", "").strip()
        password_expires = request.form.get("password_expires", "").strip()
        inactive_days = request.form.get("inactive_days", "0").strip()

        valid, msg = validate_username(username)
        if not valid:
            flash(msg, "danger")
            return render_template("users/create.html")

        if not password or password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("users/create.html")

        strength = check_password_strength(password, username)
        if not strength["valid"]:
            for fb in strength["feedback"]:
                flash(fb, "danger")
            return render_template("users/create.html")

        if user_exists(username):
            flash(f"User '{username}' already exists on the system.", "danger")
            return render_template("users/create.html")

        with get_db() as db:
            existing = db.execute(
                "SELECT id FROM linux_users WHERE username=?", (username,)
            ).fetchone()
            if existing:
                flash(f"User '{username}' already exists in the database.", "danger")
                return render_template("users/create.html")

        home_dir = ""
        args = [username]
        if create_home or username.lower() == "ironman":
            home_dir = f"/home/{username}"
            args.extend(["-d", home_dir, "-m"])
        if login_shell:
            args.extend(["-s", login_shell])
        if full_name:
            args.extend(["-c", full_name])
        if primary_group:
            args.extend(["-g", primary_group])

        result = execute("useradd", args)
        if not result["success"]:
            flash(f"Failed to create user: {result['stderr']}", "danger")
            return render_template("users/create.html")

        if additional_groups:
            group_list = [g.strip() for g in additional_groups.split(",") if g.strip()]
            for g in group_list:
                execute("usermod", ["-aG", g, username])

        echo_cmd = f"echo '{username}:{password}' | sudo chpasswd"
        pw_result = execute("passwd", [username])
        if not pw_result["success"]:
            flash(f"User created but password change failed: {pw_result['stderr']}", "warning")

        if account_expires:
            try:
                dt = datetime.strptime(account_expires, "%Y-%m-%d")
                execute("chage", ["-E", dt.strftime("%Y-%m-%d"), username])
            except ValueError:
                pass

        if password_expires:
            try:
                dt = datetime.strptime(password_expires, "%Y-%m-%d")
                max_days = (dt - datetime.now()).days
                if max_days > 0:
                    execute("chage", ["-M", str(max_days), username])
            except ValueError:
                pass

        if inactive_days and inactive_days != "0":
            execute("chage", ["-I", inactive_days, username])

        uid = None
        uid_result = execute("id", ["-u", username])
        if uid_result["success"] and uid_result["stdout"]:
            try:
                uid = int(uid_result["stdout"].strip())
            except (ValueError, TypeError):
                pass

        with get_db() as db:
            db.execute(
                """INSERT OR REPLACE INTO linux_users 
                   (username, uid, full_name, home_directory, login_shell, status, inactive_days) 
                   VALUES (?, ?, ?, ?, ?, 'active', ?)""",
                (username, uid, full_name, home_dir or f"/home/{username}", login_shell or "/bin/bash", inactive_days),
            )

        audit_log("user_create", username, f"User '{username}' created successfully.")
        flash(f"User '{username}' created successfully.", "success")
        return redirect(url_for("users.index"))

    return render_template("users/create.html")


@user_bp.route("/<username>/view")
@login_required
def view(username):
    with get_db() as db:
        user = db.execute(
            "SELECT * FROM linux_users WHERE username=?", (username,)
        ).fetchone()
        if not user:
            flash("User not found.", "danger")
            return redirect(url_for("users.index"))
        groups = db.execute(
            "SELECT group_name FROM user_group_memberships WHERE username=? ORDER BY group_name",
            (username,),
        ).fetchall()
    return render_template("users/view.html", user=user, groups=groups)


@user_bp.route("/<username>/edit", methods=["GET", "POST"])
@login_required
def edit(username):
    with get_db() as db:
        user = db.execute(
            "SELECT * FROM linux_users WHERE username=?", (username,)
        ).fetchone()
        if not user:
            flash("User not found.", "danger")
            return redirect(url_for("users.index"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        home_dir = request.form.get("home_directory", "").strip()
        login_shell = request.form.get("login_shell", "").strip()
        account_expires = request.form.get("account_expires", "").strip()

        args = []
        if full_name and full_name != user["full_name"]:
            args.extend(["-c", full_name])
        if home_dir and home_dir != user["home_directory"]:
            args.extend(["-d", home_dir])
        if login_shell and login_shell != user["login_shell"]:
            args.extend(["-s", login_shell])

        if args:
            result = execute("usermod", [username] + args)
            if not result["success"]:
                flash(f"Failed to update user: {result['stderr']}", "danger")
                return render_template("users/edit.html", user=user)

        if account_expires:
            try:
                dt = datetime.strptime(account_expires, "%Y-%m-%d")
                execute("chage", ["-E", dt.strftime("%Y-%m-%d"), username])
            except ValueError:
                pass

        with get_db() as db:
            db.execute(
                """UPDATE linux_users SET full_name=?, home_directory=?, login_shell=?, updated_at=CURRENT_TIMESTAMP WHERE username=?""",
                (full_name, home_dir, login_shell, username),
            )

        audit_log("user_modify", username, f"User '{username}' modified.")
        flash(f"User '{username}' updated successfully.", "success")
        return redirect(url_for("users.view", username=username))

    return render_template("users/edit.html", user=user)


@user_bp.route("/<username>/delete", methods=["POST"])
@login_required
def delete(username):
    from flask import session as flask_session
    if flask_session.get("admin_username") == username:
        flash("Cannot delete yourself.", "danger")
        return redirect(url_for("users.index"))

    result = execute("userdel", [username])
    if result["success"]:
        with get_db() as db:
            db.execute("DELETE FROM linux_users WHERE username=?", (username,))
            db.execute("DELETE FROM user_group_memberships WHERE username=?", (username,))
        audit_log("user_delete", username, f"User '{username}' deleted.")
        flash(f"User '{username}' deleted.", "success")
    else:
        flash(f"Failed to delete user: {result['stderr']}", "danger")

    return redirect(url_for("users.index"))


@user_bp.route("/<username>/lock", methods=["POST"])
@login_required
def lock(username):
    result = execute("usermod", ["-L", username])
    if result["success"]:
        with get_db() as db:
            db.execute("UPDATE linux_users SET locked=1, status='locked' WHERE username=?", (username,))
        audit_log("user_lock", username, f"User '{username}' locked.")
        flash(f"User '{username}' locked.", "success")
    else:
        flash(f"Failed to lock user: {result['stderr']}", "danger")
    return redirect(url_for("users.index"))


@user_bp.route("/<username>/unlock", methods=["POST"])
@login_required
def unlock(username):
    result = execute("usermod", ["-U", username])
    if result["success"]:
        with get_db() as db:
            db.execute("UPDATE linux_users SET locked=0, status='active' WHERE username=?", (username,))
        audit_log("user_unlock", username, f"User '{username}' unlocked.")
        flash(f"User '{username}' unlocked.", "success")
    else:
        flash(f"Failed to unlock user: {result['stderr']}", "danger")
    return redirect(url_for("users.index"))


@user_bp.route("/<username>/password", methods=["GET", "POST"])
@login_required
def change_password(username):
    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if not password or password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("users/change_password.html", username=username)

        strength = check_password_strength(password, username)
        if not strength["valid"]:
            for fb in strength["feedback"]:
                flash(fb, "danger")
            return render_template("users/change_password.html", username=username)

        result = execute("passwd", [username])
        if result["success"]:
            audit_log("password_change", username, f"Password changed for '{username}'.")
            flash(f"Password changed for '{username}'.", "success")
            return redirect(url_for("users.index"))
        else:
            flash(f"Failed to change password: {result['stderr']}", "danger")

    return render_template("users/change_password.html", username=username)


@user_bp.route("/<username>/groups/add", methods=["POST"])
@login_required
def add_group(username):
    group_name = request.form.get("group_name", "").strip()
    if not group_name:
        flash("Group name is required.", "danger")
        return redirect(url_for("users.view", username=username))

    result = execute("usermod", ["-aG", group_name, username])
    if result["success"]:
        with get_db() as db:
            try:
                db.execute(
                    "INSERT OR IGNORE INTO user_group_memberships (username, group_name) VALUES (?, ?)",
                    (username, group_name),
                )
            except Exception:
                pass
        audit_log("user_add_group", f"{username}:{group_name}", f"Added '{username}' to '{group_name}'.")
        flash(f"Added '{username}' to '{group_name}'.", "success")
    else:
        flash(f"Failed to add group: {result['stderr']}", "danger")
    return redirect(url_for("users.view", username=username))


@user_bp.route("/<username>/groups/remove", methods=["POST"])
@login_required
def remove_group(username):
    group_name = request.form.get("group_name", "").strip()
    if not group_name:
        flash("Group name is required.", "danger")
        return redirect(url_for("users.view", username=username))

    result = execute("gpasswd", ["-d", username, group_name])
    if result["success"]:
        with get_db() as db:
            db.execute(
                "DELETE FROM user_group_memberships WHERE username=? AND group_name=?",
                (username, group_name),
            )
        audit_log("user_remove_group", f"{username}:{group_name}", f"Removed '{username}' from '{group_name}'.")
        flash(f"Removed '{username}' from '{group_name}'.", "success")
    else:
        flash(f"Failed to remove group: {result['stderr']}", "danger")
    return redirect(url_for("users.view", username=username))


@user_bp.route("/api/generate_password")
@login_required
def api_generate_password():
    length = request.args.get("length", 16, type=int)
    pw = generate_password(length)
    strength = check_password_strength(pw)
    return jsonify({"password": pw, "strength": strength})


@user_bp.route("/api/check_password", methods=["POST"])
@login_required
def api_check_password():
    password = request.json.get("password", "")
    username = request.json.get("username", "")
    result = check_password_strength(password, username)
    return jsonify(result)


@user_bp.route("/api/check_username")
@login_required
def api_check_username():
    username = request.args.get("username", "").strip()
    valid, msg = validate_username(username)
    exists = False
    if valid:
        exists = user_exists(username)
        if not exists:
            with get_db() as db:
                row = db.execute("SELECT id FROM linux_users WHERE username=?", (username,)).fetchone()
                exists = row is not None
    return jsonify({"valid": valid, "message": msg, "exists": exists})
