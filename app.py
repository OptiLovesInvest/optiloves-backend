from routes_shim import shim as _opti_shim
from flask import Flask, request, jsonify
import os

app = Flask(__name__)
app.register_blueprint(_opti_shim)
# Opti shim routes
app.register_blueprint(_opti_shim)
@app.after_request
def _opti_marker_after_request(resp):
    import os
    resp.headers['X-Opti-Marker'] = 'app.py-v3'
    resp.headers['X-Opti-Commit'] = os.environ.get('RENDER_GIT_COMMIT','unknown')
    return resp
# === canonical payment webhook (guarded) ===
# ensure endpoint uniqueness at import time
try:
    app.view_functions.pop('payment_webhook', None)
    app.view_functions.pop('payment_webhook_v2', None)
    app.view_functions.pop('payment_webhook_v3', None)
except Exception:
    pass

def _to_int(x, default=None):
    try:
        return int(x)
    except (TypeError, ValueError):
        return default

def _to_float(x, default=None):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default

def _to_str(x):
    return (x or "").strip()

if 'payment_webhook_v3' not in app.view_functions:
    @app.route('/webhooks/payment', methods=['POST'], endpoint='payment_webhook_v3')
    def payment_webhook_v3():
        from flask import request, jsonify
        payload = request.get_json(silent=True) or {}

        order_id    = _to_str(payload.get("order_id"))
        property_id = _to_str(payload.get("property_id"))
        owner       = _to_str(payload.get("owner"))
        quantity    = _to_int(payload.get("quantity"), 0)

        # Accept cents or usd, numbers or strings
        up_cents = _to_int(payload.get("unit_price_cents"), None)
        up_usd   = _to_float(payload.get("unit_price_usd"), None)
        if up_cents is None and up_usd is not None:
            up_cents = int(round(up_usd * 100))

        status_in = _to_str(payload.get("status")).lower()
        status_map = {"settled":"completed","completed":"completed","pending":"pending"}
        status = status_map.get(status_in, "pending")

        missing = []
        if not order_id:    missing.append("order_id")
        if not property_id: missing.append("property_id")
        if not owner:       missing.append("owner")
        if quantity is None or quantity <= 0: missing.append("quantity>0")
        if (up_cents is None or up_cents <= 0) and (up_usd is None or up_usd <= 0):
            missing.append("unit_price_cents>0 or unit_price_usd>0")

        if missing:
            app.logger.warning("invalid payload (v3): %r (missing=%s)", payload, missing)
            return jsonify({"error":"invalid payload","missing":missing,"marker":"v3","got":payload}), 400

        unit_price_usd = round(up_cents / 100.0, 2)

        # Persist to Supabase Postgres (idempotent upsert)
        import os, psycopg
        try:
            with psycopg.connect(os.environ["SUPABASE_DB_URL"]) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        insert into orders (order_id, property_id, owner, quantity, unit_price_usd, status)
                        values (%s, %s, %s, %s, %s, %s)
                        on conflict (order_id) do update set
                            property_id    = excluded.property_id,
                            owner          = excluded.owner,
                            quantity       = excluded.quantity,
                            unit_price_usd = excluded.unit_price_usd,
                            status         = excluded.status
                        returning id
                    """, (order_id, property_id, owner, quantity, unit_price_usd, status))
                    row = cur.fetchone()
                    inserted_id = row[0] if row else None
        except Exception as e:
            app.logger.exception("db-insert-failed (v3): %s", e)
            return jsonify({"error":"db-insert-failed","detail":str(e),"marker":"v3"}), 500

        return jsonify({
            "ok": True,
            "marker": "v3",
            "order_id": order_id,
            "property_id": property_id,
            "owner": owner,
            "quantity": quantity,
            "unit_price_usd": unit_price_usd,
            "status": status,
            "id": inserted_id
        }), 200
# === end canonical ===

from opti_routes import bp as _opti_bp
try:
    if 'opti' in app.blueprints:
        # register with a different public name if 'opti' is already present
        app.register_blueprint(_opti_bp, name='opti2')
    else:
    pass
try:
    if 'opti' in app.blueprints:
        app.register_blueprint(_opti_bp, name='opti2')
    else:
        if 'opti' not in app.blueprints:
            if 'opti' not in app.blueprints:
                app.register_blueprint(_opti_bp)
            else:
    pass
41    app.logger.info("blueprint 'opti' already registered; skipping")
except Exception as _e:
    app.logger.warning("blueprint-register failed: %s", _e)




@app.route('/__meta', methods=['GET'])
def __opti_meta():
    from flask import jsonify
    import os
    rules = [{'rule': str(r), 'endpoint': r.endpoint, 'methods': sorted(list(r.methods))} for r in app.url_map.iter_rules()]
    return jsonify({'ok': True, 'marker': 'app.py-v3', 'commit': os.environ.get('RENDER_GIT_COMMIT','unknown'), 'routes': rules}), 200
from math import isfinite

def _to_int(x, default=None):
    try:
        v = int(x)
        return v
    except Exception:
        return default

def _to_float(x, default=None):
    try:
        v = float(x)
        return v if (v == v and v != float('inf') and v != float('-inf')) else default
    except Exception:
        return default

def _to_str(x):
    return (x or '').strip()

@app.route('/webhooks/payment3', methods=['POST'], endpoint='payment_webhook3')
def payment_webhook3():
    from flask import request, jsonify
    payload = request.get_json(silent=True) or {}

    order_id    = _to_str(payload.get('order_id'))
    property_id = _to_str(payload.get('property_id'))
    owner       = _to_str(payload.get('owner'))
    quantity    = _to_int(payload.get('quantity'), 0)

    up_cents = _to_int(payload.get('unit_price_cents'))
    up_usd   = _to_float(payload.get('unit_price_usd'))
    if up_cents is None and up_usd is not None:
        up_cents = int(round(up_usd * 100))

    status_in = _to_str(payload.get('status')).lower()
    status = {'settled':'completed','completed':'completed','pending':'pending'}.get(status_in, 'pending')

    missing = []
    if not order_id:    missing.append('order_id')
    if not property_id: missing.append('property_id')
    if not owner:       missing.append('owner')
    if quantity is None or quantity <= 0: missing.append('quantity>0')
    if (up_cents is None or up_cents <= 0) and (up_usd is None or up_usd <= 0):
        missing.append('unit_price_cents>0 or unit_price_usd>0')

    if missing:
        return jsonify({'error':'invalid payload','missing':missing,'marker':'v3','got':payload}), 400

    unit_price_usd = round(up_cents / 100.0, 2)

    # Persist to Supabase Postgres (idempotent upsert)
    import os, psycopg
    try:
        url = os.environ['SUPABASE_DB_URL']
        with psycopg.connect(url) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    insert into orders (order_id, property_id, owner, quantity, unit_price_usd, status)
                    values (%s, %s, %s, %s, %s, %s)
                    on conflict (order_id) do update set
                        property_id    = excluded.property_id,
                        owner          = excluded.owner,
                        quantity       = excluded.quantity,
                        unit_price_usd = excluded.unit_price_usd,
                        status         = excluded.status
                    returning id
                """, (order_id, property_id, owner, quantity, unit_price_usd, status))
                row = cur.fetchone()
                inserted_id = row[0] if row else None
    except KeyError:
        return jsonify({'error':'db-config-missing','need':'SUPABASE_DB_URL','marker':'v3'}), 500
    except Exception as e:
        app.logger.exception('db-insert-failed (v3): %s', e)
        return jsonify({'error':'db-insert-failed','detail':str(e),'marker':'v3'}), 500

    return jsonify({
        'ok': True,
        'marker': 'v3',
        'order_id': order_id,
        'property_id': property_id,
        'owner': owner,
        'quantity': quantity,
        'unit_price_usd': unit_price_usd,
        'status': status,
        'id': inserted_id
    }), 200




# === Opti attach & ping (stable) ===
try:
    from routes_shim import shim as _opti_shim
    app.register_blueprint(_opti_shim)
except Exception as _e:
    pass

from flask import jsonify
@app.get("/api/ping")
def _opti_ping_ok():
    return jsonify({"ok": True})
# === end Opti attach ===
