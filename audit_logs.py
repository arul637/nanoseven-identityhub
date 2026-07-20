from flask import Blueprint, render_template, request
from auth import login_required
from database import get_db

audit_bp = Blueprint("audit", __name__, url_prefix="/audit")


@audit_bp.route("/")
@login_required
def index():
    search = request.args.get("search", "").strip()
    action_filter = request.args.get("action", "").strip()
    admin_filter = request.args.get("admin", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 50

    with get_db() as db:
        query = "SELECT * FROM audit_logs WHERE 1=1"
        count_query = "SELECT COUNT(*) as cnt FROM audit_logs WHERE 1=1"
        params = []

        if search:
            like = f"%{search}%"
            query += " AND (target LIKE ? OR description LIKE ? OR admin_username LIKE ?)"
            count_query += " AND (target LIKE ? OR description LIKE ? OR admin_username LIKE ?)"
            params.extend([like, like, like])

        if action_filter:
            query += " AND action=?"
            count_query += " AND action=?"
            params.append(action_filter)

        if admin_filter:
            query += " AND admin_username=?"
            count_query += " AND admin_username=?"
            params.append(admin_filter)

        if date_from:
            query += " AND created_at >= ?"
            count_query += " AND created_at >= ?"
            params.append(date_from)

        if date_to:
            query += " AND created_at <= ?"
            count_query += " AND created_at <= ?"
            params.append(date_to + " 23:59:59")

        total = db.execute(count_query, params).fetchone()["cnt"]
        total_pages = max(1, (total + per_page - 1) // per_page)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([per_page, (page - 1) * per_page])

        logs = db.execute(query, params).fetchall()

        actions = db.execute(
            "SELECT DISTINCT action FROM audit_logs ORDER BY action"
        ).fetchall()

        admins = db.execute(
            "SELECT DISTINCT admin_username FROM audit_logs ORDER BY admin_username"
        ).fetchall()

    return render_template(
        "audit/index.html",
        logs=logs,
        actions=actions,
        admins=admins,
        search=search,
        action_filter=action_filter,
        admin_filter=admin_filter,
        date_from=date_from,
        date_to=date_to,
        page=page,
        total_pages=total_pages,
        total=total,
    )
