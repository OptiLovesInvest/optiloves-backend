from flask import Blueprint, request, jsonify
import os, psycopg

bp = Blueprint("admin_sql", __name__)

@bp.get("/api/admin/sql/diag")
def admin_sql_diag():
    has_url = bool(os.environ.get("SUPABASE_DB_URL"))
    db_ok = False
    err = None
    if has_url:
        try:
            with psycopg.connect(os.environ["SUPABASE_DB_URL"]) as conn:
                with conn.cursor() as cur:
                    cur.execute("select 1")
                    cur.fetchone()
            db_ok = True
        except Exception as e:
            err = str(e)
    return jsonify({"ok": True, "has_url": has_url, "db_ok": db_ok, "error": err})

ALLOWED_PREFIXES = (
    "select","create table","create extension","insert","update","delete",
    "alter table","drop table if exists"
)

@bp.post("/api/admin/sql")
def admin_sql():
    if request.json.get("secret") != os.environ.get("ADMIN_SECRET"):
        return {"error":"unauthorized"}, 403
    sql = (request.json.get("sql") or "").strip()
    if not sql: return {"error":"empty sql"}, 400
    if not sql.lower().lstrip().startswith(ALLOWED_PREFIXES):
        return {"error":"sql not allowed"}, 400

    out = []
    try:
        with psycopg.connect(os.environ["SUPABASE_DB_URL"]) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                if cur.description:
                    cols = [d[0] for d in cur.description]
                    out = [dict(zip(cols, row)) for row in cur.fetchall()]
                conn.commit()
        return jsonify(out)
    except Exception as e:
        return jsonify({"error":"db_error","detail":str(e)}), 500
