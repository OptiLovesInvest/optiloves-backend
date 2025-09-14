from flask import Flask, request, jsonify
import os
import psycopg

app = Flask(__name__)

@app.route("/_health")
def _health():
    return jsonify(ok=True, service="optiloves-backend"), 200

@app.route("/__meta")
def __meta():
    rules = [{"rule": str(r), "endpoint": r.endpoint, "methods": sorted(list(r.methods))} for r in app.url_map.iter_rules()]
    return jsonify(ok=True, marker="minimal_service", routes=rules), 200

def _to_str(x): return (x or "").strip()
def _to_int(x, default=None):
    try: return int(x)
    except Exception: return default
def _to_float(x, default=None):
    try: return float(x)
    except Exception: return default

@app.route("/webhooks/payment3", methods=["POST"])
def payment3():
    payload = request.get_json(silent=True) or {}
    order_id    = _to_str(payload.get("order_id"))
    property_id = _to_str(payload.get("property_id"))
    owner       = _to_str(payload.get("owner"))
    quantity    = _to_int(payload.get("quantity"), 0)
    up_cents    = _to_int(payload.get("unit_price_cents"))
    up_usd      = _to_float(payload.get("unit_price_usd"))
    if up_cents is None and up_usd is not None:
        up_cents = int(round(up_usd * 100))
    status_in = _to_str(payload.get("status")).lower()
    status = {"settled":"completed","completed":"completed","pending":"pending"}.get(status_in, "pending")

    missing = []
    if not order_id:    missing.append("order_id")
    if not property_id: missing.append("property_id")
    if not owner:       missing.append("owner")
    if quantity is None or quantity <= 0: missing.append("quantity>0")
    if up_cents is None or up_cents <= 0: missing.append("unit_price_cents>0 or unit_price_usd>0")
    if missing:
        return jsonify(error="invalid payload", missing=missing, marker="ms"), 400

    unit_price_usd = round(up_cents/100.0, 2)

    try:
        url = os.environ["SUPABASE_DB_URL"]
        with psycopg.connect(url) as conn, conn.cursor() as cur:
            # Ensure table exists (idempotent)
            cur.execute("""
                create table if not exists public.orders (
                  id bigserial primary key,
                  order_id text unique not null,
                  property_id text not null,
                  owner text not null,
                  quantity integer not null check (quantity > 0),
                  unit_price_usd numeric(12,2) not null check (unit_price_usd > 0),
                  status text not null,
                  created_at timestamptz not null default now()
                );
            """)
            cur.execute("""
                insert into orders (order_id, property_id, owner, quantity, unit_price_usd, status)
                values (%s,%s,%s,%s,%s,%s)
                on conflict (order_id) do update set
                  property_id=excluded.property_id,
                  owner=excluded.owner,
                  quantity=excluded.quantity,
                  unit_price_usd=excluded.unit_price_usd,
                  status=excluded.status
                returning id
            """, (order_id, property_id, owner, quantity, unit_price_usd, status))
            _ = cur.fetchone()
    except KeyError:
        return jsonify(error="db-config-missing", need="SUPABASE_DB_URL", marker="ms"), 500
    except Exception as e:
        return jsonify(error="db-insert-failed", detail=str(e), marker="ms"), 500

    return jsonify(ok=True, marker="ms", order_id=order_id, unit_price_usd=unit_price_usd, status=status), 200
from flask import jsonify, request
import os
try:
    import psycopg2
except Exception:
    psycopg2 = None

API_KEY = os.getenv("OPTI_API_KEY","")
PG_DSN  = os.getenv("PG_DSN","")

@app.get("/api/ping")
def _opti_ping():
    return jsonify({"ok": True})

@app.get("/api/diag")
def _opti_diag():
    ok=False; err=None
    if psycopg2 and PG_DSN:
        try:
            c=psycopg2.connect(PG_DSN); c.close(); ok=True
        except Exception as e:
            err=str(e)
    return jsonify({"pg_dsn_set": bool(PG_DSN), "db_ok": ok, "error": err})

@app.post("/webhooks/payment")
def _opti_payment():
    if not API_KEY or request.headers.get("x-api-key","") != API_KEY:
        return jsonify({"error":"forbidden"}), 403
    d = request.get_json(silent=True) or {}
    oid=d.get("order_id"); pid=d.get("property_id")
    owner=d.get("owner") or d.get("wallet") or d.get("investor_wallet")
    try: qty=int(d.get("quantity") or d.get("qty_tokens") or 0)
    except: qty=0
    try: price=float(d.get("unit_price_usd") or d.get("unit_price") or 50.0)
    except: price=50.0
    raw_status=str((d.get("status") or "")).strip().lower()
    _status_map={"settled":"completed","complete":"completed","completed":"completed",
                 "succeeded":"completed","success":"completed","paid":"completed","captured":"completed",
                 "pending":"pending","processing":"pending","authorized":"pending","authorised":"pending"}
    status=_status_map.get(raw_status,"pending")
    if not oid or not pid or not owner or qty<=0:
        return jsonify({"error":"invalid payload","need":["order_id","property_id","owner","quantity>0"]}), 400
    if not psycopg2 or not PG_DSN:
        return jsonify({"error":"server db not configured"}), 500
    sql="""insert into public.orders (order_id,property_id,owner,quantity,unit_price_usd,status,created_at)
           values (%s,%s,%s,%s,%s,%s, now())
           on conflict (order_id) do update set
             property_id=excluded.property_id, owner=excluded.owner, quantity=excluded.quantity,
             unit_price_usd=excluded.unit_price_usd, status=excluded.status;"""
    try:
        conn=psycopg2.connect(PG_DSN)
        with conn, conn.cursor() as cur: cur.execute(sql,(oid,pid,owner,qty,price,status))
        conn.close(); return jsonify({"ok":True,"order_id":oid})
    except Exception as e:
        return jsonify({"ok":False,"error":str(e)}), 500
# === whoami diag (guarded) ===
try:
    app
    from flask import jsonify
    @app.get("/__whoami")
    def __whoami():
        try:
            return jsonify({"import_name": app.import_name, "root_path": app.root_path, "module_file": __file__})
        except Exception:
            return jsonify({"import_name": getattr(app,"import_name",None), "module_file": __file__})
except NameError:
    pass
# === end whoami ===
