# === Opti global shim: attach routes to every Flask app instance ===
import os
try:
    import psycopg2
except Exception:
    psycopg2 = None

from flask import Flask, jsonify, request

_API_KEY = os.getenv("OPTI_API_KEY", "")
_PG_DSN  = os.getenv("PG_DSN", "")

_orig_init = Flask.__init__

def _attach_routes(app: Flask):
    if getattr(app, "_opti_routes_attached", False):
        return
    app._opti_routes_attached = True

    @app.get("/api/ping")
    def _opti_ping():
        return jsonify({"ok": True})

    @app.get("/api/diag")
    def _opti_diag():
        ok = False; err = None
        if psycopg2 and _PG_DSN:
            try:
                c = psycopg2.connect(_PG_DSN); c.close(); ok = True
            except Exception as e:
                err = str(e)
        return jsonify({"pg_dsn_set": bool(_PG_DSN), "db_ok": ok, "error": err})

    @app.post("/webhooks/payment")
    def _opti_payment():
        if _API_KEY and request.headers.get("x-api-key","") != _API_KEY:
            return jsonify({"error":"forbidden"}), 403
        d = request.get_json(silent=True) or {}
        oid = d.get("order_id"); pid = d.get("property_id")
        owner = d.get("owner") or d.get("wallet") or d.get("investor_wallet")
        try: qty = int(d.get("quantity") or d.get("qty_tokens") or 0)
        except: qty = 0
        try: price = float(d.get("unit_price_usd") or d.get("unit_price") or 50.0)
        except: price = 50.0
        raw = str((d.get("status") or "")).strip().lower()
        _map = {
            "settled":"completed","complete":"completed","completed":"completed",
            "succeeded":"completed","success":"completed","paid":"completed","captured":"completed",
            "pending":"pending","processing":"pending","authorized":"pending","authorised":"pending"
        }
        status = _map.get(raw,"pending")
        if not oid or not pid or not owner or qty <= 0:
            return jsonify({"error":"invalid payload","need":["order_id","property_id","owner","quantity>0"]}), 400
        if not psycopg2 or not _PG_DSN:
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
            conn = psycopg2.connect(_PG_DSN)
            with conn, conn.cursor() as cur:
                cur.execute(sql,(oid,pid,owner,qty,price,status))
            conn.close()
            return jsonify({"ok":True,"order_id":oid})
        except Exception as e:
            return jsonify({"ok":False,"error":str(e)}), 500

def _init_wrapper(self, *a, **kw):
    _orig_init(self, *a, **kw)
    try:
        _attach_routes(self)
    except Exception:
        pass

Flask.__init__ = _init_wrapper
# === end shim ===
