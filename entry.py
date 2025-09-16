# entry.py â€” single source of truth for Gunicorn
# Tries to import your Flask app object no matter its name/location,
# then ensures the KYC blueprint is registered, plus a health check.

try:
    import app as m
except Exception as e:
    raise RuntimeError("Cannot import app module") from e

# Support app named either `app` or `application`
app = getattr(m, "app", None) or getattr(m, "application", None)
if app is None:
    raise RuntimeError("No Flask app object found in app module")

from app_kyc import kyc
if "kyc" not in app.blueprints:
    app.register_blueprint(kyc, url_prefix="/api/kyc")

@app.get("/_health")
def _health():
    return {"ok": True, "service": "backend"}
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
# === BEGIN: portfolio+routes (attached to app) ===
from flask import request, jsonify, current_app as _ca

@app.get('/api/routes')
def _list_routes():
    rules=[{'rule':str(r),'endpoint':r.endpoint,'methods':sorted(list(r.methods))} for r in _ca.url_map.iter_rules()]
    return {'ok':True,'routes':rules},200

@app.get('/api/portfolio/<owner>')
def _pf_owner(owner):
    owner=(owner or '').strip()
    if not owner: return jsonify({'owner':'','items':[],'total':0,'source':'attached'}),200
    return jsonify({'owner':owner,'items':[],'total':0,'source':'attached'}),200

@app.get('/api/portfolio')
def _pf_q():
    owner=(request.args.get('owner','') or '').strip()
    if not owner: return jsonify({'error':'missing owner'}),400
    return jsonify({'owner':owner,'items':[],'total':0,'source':'attached'}),200
# === END: portfolio+routes ===
