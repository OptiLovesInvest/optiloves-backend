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
        try: c=psycopg2.connect(PG_DSN); c.close(); ok=True
        except Exception as e: err=str(e)
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
    if not psycopg2 or not PG_DSN: return jsonify({"error":"server db not configured"}), 500
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
