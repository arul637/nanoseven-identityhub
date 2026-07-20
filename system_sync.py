import time
import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from auth import login_required
from database import get_db
from command_executor import read_file

sync_bp = Blueprint("sync", __name__, url_prefix="/sync")


def audit_log(action, target, description, result="success"):
    from flask import session
    with get_db() as db:
        db.execute(
            "INSERT INTO audit_logs (admin_username, action, target, description, result, ip_address) VALUES (?, ?, ?, ?, ?, ?)",
            (session.get("admin_username", ""), action, target, description, result, ""),
        )


def parse_passwd_line(line):
    parts = line.strip().split(":")
    if len(parts) >= 7:
        return {
            "username": parts[0],
            "uid": int(parts[2]) if parts[2].isdigit() else 0,
            "gid": int(parts[3]) if parts[3].isdigit() else 0,
            "full_name": parts[4].split(",")[0] if parts[4] else "",
            "home_directory": parts[5],
            "login_shell": parts[6],
        }
    return None


def parse_group_line(line):
    parts = line.strip().split(":")
    if len(parts) >= 4:
        return {
            "group_name": parts[0],
            "gid": int(parts[2]) if parts[2].isdigit() else 0,
            "members": [m.strip() for m in parts[3].split(",") if m.strip()] if parts[3] else [],
        }
    return None


@sync_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    history = []
    with get_db() as db:
        history = db.execute(
            "SELECT * FROM sync_history ORDER BY created_at DESC LIMIT 20"
        ).fetchall()

    if request.method == "POST":
        return redirect(url_for("sync.run"))

    return render_template("sync/index.html", history=history)


@sync_bp.route("/run", methods=["POST"])
@login_required
def run():
    start_time = time.time()

    passwd_lines = read_file("/etc/passwd")
    group_lines = read_file("/etc/group")

    if not passwd_lines or passwd_lines == ["mock file content"]:
        flash("Could not read /etc/passwd. Using mock data for demonstration.", "warning")
        passwd_lines = [
            "root:x:0:0:root:/root:/bin/bash",
            "daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin",
            "bin:x:2:2:bin:/bin:/usr/sbin/nologin",
            "sys:x:3:3:sys:/dev:/usr/sbin/nologin",
            "sync:x:4:65534:sync:/bin:/bin/sync",
        ]

    if not group_lines or group_lines == ["mock file content"]:
        flash("Could not read /etc/group. Using mock data for demonstration.", "warning")
        group_lines = [
            "root:x:0:",
            "daemon:x:1:",
            "bin:x:2:",
            "sys:x:3:",
            "adm:x:4:",
            "sudo:x:27:",
            "wheel:x:10:",
        ]

    discovered_users = []
    discovered_groups = []
    new_users = 0
    updated_users = 0
    new_groups = 0
    updated_groups = 0

    for line in passwd_lines:
        parsed = parse_passwd_line(line)
        if parsed and parsed["uid"] >= 1000:
            discovered_users.append(parsed)

    for line in group_lines:
        parsed = parse_group_line(line)
        if parsed:
            discovered_groups.append(parsed)

    with get_db() as db:
        for user in discovered_users:
            existing = db.execute(
                "SELECT id FROM linux_users WHERE username=?", (user["username"],)
            ).fetchone()
            if existing:
                db.execute(
                    """UPDATE linux_users SET uid=?, gid=?, full_name=?, home_directory=?, login_shell=?, updated_at=CURRENT_TIMESTAMP WHERE username=?""",
                    (user["uid"], user["gid"], user["full_name"], user["home_directory"], user["login_shell"], user["username"]),
                )
                updated_users += 1
            else:
                db.execute(
                    """INSERT INTO linux_users (username, uid, gid, full_name, home_directory, login_shell, status) VALUES (?, ?, ?, ?, ?, ?, 'active')""",
                    (user["username"], user["uid"], user["gid"], user["full_name"], user["home_directory"], user["login_shell"]),
                )
                new_users += 1

        privileged_groups = []
        pg_row = db.execute(
            "SELECT policy_value FROM security_policies WHERE policy_key='privileged_groups'"
        ).fetchone()
        if pg_row:
            privileged_groups = [g.strip() for g in pg_row["policy_value"].split(",")]

        for group in discovered_groups:
            existing = db.execute(
                "SELECT id FROM linux_groups WHERE group_name=?", (group["group_name"],)
            ).fetchone()
            is_privileged = 1 if group["group_name"] in privileged_groups else 0
            if existing:
                db.execute(
                    "UPDATE linux_groups SET gid=?, privileged=?, updated_at=CURRENT_TIMESTAMP WHERE group_name=?",
                    (group["gid"], is_privileged, group["group_name"]),
                )
                updated_groups += 1
            else:
                db.execute(
                    "INSERT INTO linux_groups (group_name, gid, privileged) VALUES (?, ?, ?)",
                    (group["group_name"], group["gid"], is_privileged),
                )
                new_groups += 1

            for member in group["members"]:
                try:
                    db.execute(
                        "INSERT OR IGNORE INTO user_group_memberships (username, group_name) VALUES (?, ?)",
                        (member, group["group_name"]),
                    )
                except Exception:
                    pass

        db_users = set(
            row["username"] for row in db.execute("SELECT username FROM linux_users").fetchall()
        )
        synced_users = set(u["username"] for u in discovered_users)
        missing_users = db_users - synced_users

        db_groups = set(
            row["group_name"] for row in db.execute("SELECT group_name FROM linux_groups").fetchall()
        )
        synced_groups_set = set(g["group_name"] for g in discovered_groups)
        missing_groups = db_groups - synced_groups_set

        duration_ms = int((time.time() - start_time) * 1000)

        db.execute(
            """INSERT INTO sync_history (users_discovered, new_users, updated_users, missing_users, groups_discovered, new_groups, updated_groups, duration_ms, result) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'success')""",
            (
                len(discovered_users),
                new_users,
                updated_users,
                len(missing_users),
                len(discovered_groups),
                new_groups,
                updated_groups,
                duration_ms,
            ),
        )

    audit_log(
        "sync",
        "system",
        f"Synced {len(discovered_users)} users ({new_users} new, {updated_users} updated) and {len(discovered_groups)} groups ({new_groups} new, {updated_groups} updated).",
    )

    flash(
        f"Sync complete: {len(discovered_users)} users ({new_users} new, {updated_users} updated, {len(missing_users)} missing), "
        f"{len(discovered_groups)} groups ({new_groups} new, {updated_groups} updated).",
        "success",
    )
    return redirect(url_for("sync.index"))


@sync_bp.route("/delete_history", methods=["POST"])
@login_required
def delete_history():
    ids = request.form.getlist("ids")
    with get_db() as db:
        if ids:
            placeholders = ",".join("?" for _ in ids)
            db.execute(f"DELETE FROM sync_history WHERE id IN ({placeholders})", ids)
            audit_log("sync_delete", "sync_history", f"Deleted {len(ids)} sync history entries.")
            flash(f"Deleted {len(ids)} sync history entries.", "success")
        else:
            db.execute("DELETE FROM sync_history")
            audit_log("sync_delete", "sync_history", "All sync history cleared.")
            flash("All sync history cleared.", "success")
    return redirect(url_for("sync.index"))
