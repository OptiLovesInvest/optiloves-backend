from flask import Blueprint, request, jsonify
import os, psycopg

bp = Blueprint("admin_sql", __name__)


def _safe_err(kind, exc=None, code=500):
    msg = kind
    if exc is not None:
        cls = type(exc).__name__
        msg = f"{kind}: {cls}"
    return jsonify({"ok": False, "error": msg}), code
ALLOWED_PREFIXES = (
    "select","create table","create extension","insert","update","delete",
    "alter table","drop table if exists"
)

@bp.route("/api/admin/sql", methods=["POST"])
def admin_sql():
    if request.json.get("secret") != os.environ.get("ADMIN_SECRET"):
        return {"error":"unauthorized"}, 403
    sql = (request.json.get("sql") or "").strip()
    if not sql: return {"error":"empty sql"}, 400
    if not sql.lower().lstrip().startswith(ALLOWED_PREFIXES):
        return {"error":"sql not allowed"}, 400

    out = []
if not os.environ.get("SUPABASE_DB_URL"):
    return _safe_err("SUPABASE_DB_URL missing", code=500)
try:
    with psycopg.connect(os.environ["SUPABASE_DB_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            if cur.description:
                cols = [d[0] for d in cur.description]
                out = [dict(zip(cols, row)) for row in cur.fetchall()]
            conn.commit()\n    return jsonify(out)\nexcept Exception as e:\n    return _safe_err('db_error', e, 500)