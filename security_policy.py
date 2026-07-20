from flask import Blueprint, render_template, request, redirect, url_for, flash
from auth import login_required
from database import get_db

security_bp = Blueprint("security", __name__, url_prefix="/security")


def audit_log(action, target, description, result="success"):
    from flask import session
    with get_db() as db:
        db.execute(
            "INSERT INTO audit_logs (admin_username, action, target, description, result, ip_address) VALUES (?, ?, ?, ?, ?, ?)",
            (session.get("admin_username", ""), action, target, description, result, ""),
        )


@security_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    with get_db() as db:
        policies = db.execute(
            "SELECT * FROM security_policies ORDER BY policy_key"
        ).fetchall()

    if request.method == "POST":
        with get_db() as db:
            for policy in policies:
                key = policy["policy_key"]
                value = request.form.get(key, "")
                if value != policy["policy_value"]:
                    db.execute(
                        "UPDATE security_policies SET policy_value=?, updated_at=CURRENT_TIMESTAMP WHERE policy_key=?",
                        (value, key),
                    )

        audit_log("policy_update", "security_policies", "Security policies updated.")
        flash("Security policies updated successfully.", "success")
        return redirect(url_for("security.index"))

    return render_template("security/policies.html", policies=policies)
