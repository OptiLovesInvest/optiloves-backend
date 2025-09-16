import os
from flask import Blueprint, request, jsonify
try:
    import psycopg2
except Exception:
    psycopg2 = None

shim = Blueprint("opti_shim", __name__)
API_KEY = os.getenv("OPTI_API_KEY","")
PG_DSN  = os.getenv("PG_DSN","")

def _guard():
    k = request.headers.get("x-api-key","")
    if not API_KEY or k != API_KEY:
        return jsonify({"error":"forbidden"}), 403

@shim.get("/api/ping")
def api_ping():
    return jsonify({"msg":"api alive","ok":True})

@shim.get("/api/diag")
def api_diag():
    ok=False; err=None
    if psycopg2 and PG_DSN:
        try:
            c=psycopg2.connect(PG_DSN); c.close(); ok=True
        except Exception as e:
            err=str(e)
    return jsonify({"pg_dsn_set": bool(PG_DSN), "db_ok": ok, "error": err})

@shim.post("/webhooks/payment")
def payment_webhook():
    g=_guard()
    if g: return g
    data = request.get_json(silent=True) or {}
    order_id = data.get("order_id")
    property_id = data.get("property_id")
    owner = data.get("owner") or data.get("wallet") or data.get("investor_wallet")
    try:
        qty = int(data.get("quantity") or data.get("qty_tokens") or 0)
    except Exception:
        qty = 0
    try:
        price = float(data.get("unit_price_usd") or data.get("unit_price") or 50.0)
    except Exception:
        price = 50.0
    status = (data.get("status") or "completed").lower()
    if not order_id or not property_id or not owner or qty <= 0:
        return jsonify({"error":"invalid payload","need":["order_id","property_id","owner","quantity>0"]}), 400
    if not psycopg2 or not PG_DSN:
        return jsonify({"error":"server db not configured"}), 500
    sql = """
    insert into public.orders (order_id,property_id,owner,quantity,unit_price_usd,status,created_at)
    values (%s,%s,%s,%s,%s,%s, now())
    on conflict (order_id) do update set
      property_id=excluded.property_id,
      owner=excluded.owner,
      quantity=excluded.quantity,
      unit_price_usd=excluded.unit_price_usd,
      status=excluded.status;
    """
    try:
        conn=psycopg2.connect(PG_DSN)
        with conn, conn.cursor() as cur:
            cur.execute(sql,(order_id,property_id,owner,qty,price,status))
        conn.close()
        return jsonify({"ok":True,"order_id":order_id})
    except Exception as e:
        return jsonify({"ok":False,"error":str(e)}), 500
# ==== BEGIN PORTFOLIO (stable shim) ====
from flask import request, jsonify

@shim.get('/portfolio/<owner>')
def _portfolio_owner(owner):
    owner = (owner or '').strip()
    if not owner:
        return jsonify({'owner':'', 'items':[], 'total':0, 'source':'shim'}), 200
    return jsonify({'owner': owner, 'items': [], 'total': 0, 'source': 'shim'}), 200

@shim.get('/portfolio')
def _portfolio_query():
    owner = request.args.get('owner','').strip()
    if not owner:
        return jsonify({'error':'missing owner'}), 400
    return jsonify({'owner': owner, 'items': [], 'total': 0, 'source': 'shim'}), 200
# ==== END PORTFOLIO (stable shim) ====
# == BEGIN: portfolio+routes (shim) ==
from flask import request, jsonify, current_app as _ca

@shim.get('/portfolio/<owner>')
def _shim_portfolio_owner(owner):
    owner=(owner or '').strip()
    if not owner: return jsonify({'owner':'','items':[],'total':0,'source':'shim'}),200
    return jsonify({'owner':owner,'items':[],'total':0,'source':'shim'}),200

@shim.get('/portfolio')
def _shim_portfolio_q():
    owner=(request.args.get('owner','') or '').strip()
    if not owner: return jsonify({'error':'missing owner'}),400
    return jsonify({'owner':owner,'items':[],'total':0,'source':'shim'}),200

@shim.get('/routes')
def _shim_routes():
    rules=[{'rule':str(r),'endpoint':r.endpoint,'methods':sorted(list(r.methods))} for r in _ca.url_map.iter_rules()]
    return {'ok':True,'routes':rules},200
# == END: portfolio+routes (shim) ==
