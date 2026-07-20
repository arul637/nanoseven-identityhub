from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from auth import login_required
from database import get_db
from command_executor import execute, user_exists

group_bp = Blueprint("groups", __name__, url_prefix="/groups")


def audit_log(action, target, description, result="success"):
    from flask import session
    with get_db() as db:
        db.execute(
            "INSERT INTO audit_logs (admin_username, action, target, description, result, ip_address) VALUES (?, ?, ?, ?, ?, ?)",
            (session.get("admin_username", ""), action, target, description, result, ""),
        )


def get_privileged_groups():
    with get_db() as db:
        row = db.execute(
            "SELECT policy_value FROM security_policies WHERE policy_key='privileged_groups'"
        ).fetchone()
        if row:
            return [g.strip() for g in row["policy_value"].split(",")]
        return ["sudo", "wheel", "adm", "docker", "root"]


def get_groups_require_confirmation():
    with get_db() as db:
        row = db.execute(
            "SELECT policy_value FROM security_policies WHERE policy_key='groups_require_confirmation'"
        ).fetchone()
        if row:
            return [g.strip() for g in row["policy_value"].split(",")]
        return ["sudo", "wheel", "docker", "root", "adm"]


@group_bp.route("/")
@login_required
def index():
    search = request.args.get("search", "").strip()
    gid_filter = request.args.get("gid", "").strip()

    with get_db() as db:
        query = """
            SELECT g.*, (SELECT COUNT(*) FROM user_group_memberships WHERE group_name=g.group_name) as member_count
            FROM linux_groups g WHERE 1=1
        """
        params = []
        if search:
            query += " AND g.group_name LIKE ?"
            params.append(f"%{search}%")
        if gid_filter:
            query += " AND g.gid = ?"
            params.append(gid_filter)
        query += " ORDER BY g.group_name ASC"
        groups = db.execute(query, params).fetchall()

    system_groups = [g for g in groups if g["gid"] is None or g["gid"] < 1000]
    user_groups = [g for g in groups if g["gid"] is not None and g["gid"] >= 1000]

    privileged = get_privileged_groups()
    return render_template("groups/index.html", user_groups=user_groups, system_groups=system_groups, search=search, gid=gid_filter, privileged=privileged)


@group_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        group_name = request.form.get("group_name", "").strip()

        if not group_name or not group_name.isalnum():
            flash("Group name must be alphanumeric.", "danger")
            return render_template("groups/create.html")

        with get_db() as db:
            existing = db.execute(
                "SELECT id FROM linux_groups WHERE group_name=?", (group_name,)
            ).fetchone()
            if existing:
                flash(f"Group '{group_name}' already exists.", "danger")
                return render_template("groups/create.html")

        result = execute("groupadd", [group_name])
        if result["success"]:
            gid = None
            gid_result = execute("getent", ["group", group_name])
            if gid_result["success"] and gid_result["stdout"]:
                parts = gid_result["stdout"].strip().split(":")
                if len(parts) >= 3 and parts[2].isdigit():
                    gid = int(parts[2])
            privileged = group_name in get_privileged_groups()
            with get_db() as db:
                db.execute(
                    "INSERT INTO linux_groups (group_name, gid, privileged) VALUES (?, ?, ?)",
                    (group_name, gid, 1 if privileged else 0),
                )
            audit_log("group_create", group_name, f"Group '{group_name}' created.")
            flash(f"Group '{group_name}' created.", "success")
            return redirect(url_for("groups.index"))
        else:
            flash(f"Failed to create group: {result['stderr']}", "danger")

    return render_template("groups/create.html")


@group_bp.route("/<group_name>/view")
@login_required
def view(group_name):
    with get_db() as db:
        group = db.execute(
            "SELECT * FROM linux_groups WHERE group_name=?", (group_name,)
        ).fetchone()
        if not group:
            flash("Group not found.", "danger")
            return redirect(url_for("groups.index"))

        members = db.execute(
            """SELECT u.*, m.added_at FROM user_group_memberships m
               JOIN linux_users u ON u.username=m.username
               WHERE m.group_name=? ORDER BY u.username""",
            (group_name,),
        ).fetchall()

        non_members = db.execute(
            """SELECT username FROM linux_users WHERE username NOT IN
               (SELECT username FROM user_group_memberships WHERE group_name=?)
               ORDER BY username""",
            (group_name,),
        ).fetchall()

    return render_template("groups/view.html", group=group, members=members, non_members=non_members)


@group_bp.route("/<group_name>/rename", methods=["POST"])
@login_required
def rename(group_name):
    new_name = request.form.get("new_name", "").strip()
    if not new_name or not new_name.isalnum():
        flash("New group name must be alphanumeric.", "danger")
        return redirect(url_for("groups.view", group_name=group_name))

    result = execute("groupmod", ["-n", new_name, group_name])
    if result["success"]:
        with get_db() as db:
            db.execute("UPDATE linux_groups SET group_name=? WHERE group_name=?", (new_name, group_name))
            db.execute("UPDATE user_group_memberships SET group_name=? WHERE group_name=?", (new_name, group_name))
        audit_log("group_rename", f"{group_name}->{new_name}", f"Group '{group_name}' renamed to '{new_name}'.")
        flash(f"Group renamed to '{new_name}'.", "success")
        return redirect(url_for("groups.view", group_name=new_name))
    else:
        flash(f"Failed to rename group: {result['stderr']}", "danger")
        return redirect(url_for("groups.view", group_name=group_name))


@group_bp.route("/<group_name>/delete", methods=["POST"])
@login_required
def delete(group_name):
    result = execute("groupdel", [group_name])
    if result["success"]:
        with get_db() as db:
            db.execute("DELETE FROM linux_groups WHERE group_name=?", (group_name,))
            db.execute("DELETE FROM user_group_memberships WHERE group_name=?", (group_name,))
        audit_log("group_delete", group_name, f"Group '{group_name}' deleted.")
        flash(f"Group '{group_name}' deleted.", "success")
    else:
        flash(f"Failed to delete group: {result['stderr']}", "danger")
    return redirect(url_for("groups.index"))


@group_bp.route("/<group_name>/add_user", methods=["POST"])
@login_required
def add_user(group_name):
    username = request.form.get("username", "").strip()
    if not username:
        flash("Username is required.", "danger")
        return redirect(url_for("groups.view", group_name=group_name))

    if not user_exists(username):
        flash(f"User '{username}' does not exist.", "danger")
        return redirect(url_for("groups.view", group_name=group_name))

    with get_db() as db:
        existing = db.execute(
            "SELECT id FROM user_group_memberships WHERE username=? AND group_name=?",
            (username, group_name),
        ).fetchone()
        if existing:
            flash(f"User '{username}' is already a member of '{group_name}'.", "warning")
            return redirect(url_for("groups.view", group_name=group_name))

    confirm_groups = get_groups_require_confirmation()
    if group_name in confirm_groups:
        confirmed = request.form.get("confirmed", "0") == "1"
        if not confirmed:
            flash(
                f"WARNING: '{group_name}' is a privileged group. Confirm adding '{username}'.",
                "warning",
            )
            return render_template("groups/confirm_add.html", group_name=group_name, username=username)

    result = execute("usermod", ["-aG", group_name, username])
    if result["success"]:
        with get_db() as db:
            try:
                db.execute(
                    "INSERT INTO user_group_memberships (username, group_name) VALUES (?, ?)",
                    (username, group_name),
                )
                db.execute(
                    "UPDATE linux_groups SET privileged=1 WHERE group_name=? AND group_name IN (SELECT policy_value FROM security_policies WHERE policy_key='privileged_groups')",
                    (group_name,),
                )
            except Exception:
                pass
        audit_log("group_add_user", f"{group_name}:{username}", f"Added '{username}' to '{group_name}'.")
        flash(f"Added '{username}' to '{group_name}'.", "success")
    else:
        flash(f"Failed to add user to group: {result['stderr']}", "danger")

    return redirect(url_for("groups.view", group_name=group_name))


@group_bp.route("/<group_name>/remove_user", methods=["POST"])
@login_required
def remove_user(group_name):
    username = request.form.get("username", "").strip()
    if not username:
        flash("Username is required.", "danger")
        return redirect(url_for("groups.view", group_name=group_name))

    result = execute("gpasswd", ["-d", username, group_name])
    if result["success"]:
        with get_db() as db:
            db.execute(
                "DELETE FROM user_group_memberships WHERE username=? AND group_name=?",
                (username, group_name),
            )
        audit_log("group_remove_user", f"{group_name}:{username}", f"Removed '{username}' from '{group_name}'.")
        flash(f"Removed '{username}' from '{group_name}'.", "success")
    else:
        flash(f"Failed to remove user: {result['stderr']}", "danger")
    return redirect(url_for("groups.view", group_name=group_name))
