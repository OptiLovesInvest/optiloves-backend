from flask import Blueprint, request, jsonify
import os, psycopg

bp = Blueprint("admin_sql", __name__)

ALLOWED_PREFIXES = (
    "select", "create table", "create extension", "insert", "update", "delete",
    "alter table", "drop table if exists"  # keep tight; expand only if needed
)

@bp.route("/api/admin/sql", methods=["POST"])
def admin_sql():
    if request.json.get("secret") != os.environ.get("ADMIN_SECRET"):
        return {"error":"unauthorized"}, 403
    sql = (request.json.get("sql") or "").strip()
    if not sql:
        return {"error":"empty sql"}, 400
    # simple guard
    lower = sql.lower().lstrip()
    if not lower.startswith(ALLOWED_PREFIXES):
        return {"error":"sql not allowed"}, 400

    out = []
    with psycopg.connect(os.environ["SUPABASE_DB_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            if cur.description:
                cols = [d[0] for d in cur.description]
                out = [dict(zip(cols, row)) for row in cur.fetchall()]
            conn.commit()
    return jsonify(out)