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
