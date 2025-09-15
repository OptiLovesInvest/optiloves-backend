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
# === Opti minimal ping (stable) ===
from flask import jsonify
try:
    app
    @app.get("/api/ping")
    def _opti_ping_ok():
        return jsonify({"ok": True})
except NameError:
    pass
# === end ===




# === portfolio fallback (idempotent) ===
try:
    from opti_portfolio_fallback import bp as _opti_pf
    _app = globals().get('app') or globals().get('application')
    if _app:
        have_pf = any(str(r.rule).startswith('/api/portfolio') for r in _app.url_map.iter_rules())
        if not have_pf: _app.register_blueprint(_opti_pf)
except Exception as _e:
    pass
# === /api/portfolio fallback (inline, idempotent) ===
import os, json, time, urllib.request
def _opti_rpc(url, method, params):
    data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(url, data=data, headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=10) as r: return json.loads(r.read().decode())

def _opti_rpc_url(): return os.getenv("SOLANA_RPC","https://api.mainnet-beta.solana.com")
def _opti_mints():
    ms=[m.strip() for m in os.getenv("OPTILOVES_MINTS","").split(",") if m.strip()]
    return ms or ["5ihsE55yaFFZXoizZKv5xsd6YjEuvaXiiMr2FLjQztN9"]

def _opti_items(owner):
    out=[]; rpc=_opti_rpc_url()
    for m in _opti_mints():
        resp=_opti_rpc(rpc,"getTokenAccountsByOwner",[owner,{"mint":m},{"encoding":"jsonParsed"}])
        total=0.0
        for v in resp.get("result",{}).get("value",[]):
            ui=v["account"]["data"]["parsed"]["info"]["tokenAmount"].get("uiAmount",0) or 0
            try: total+=float(ui)
            except: pass
        price=float(os.getenv("OPTILOVES_BASE_PRICE_USD","50"))
        out.append({"mint":m,"balance":total,"price":price,"estValue":round(total*price,2)})
    return out

try:
    # Prefer existing API blueprint if present
    bp = api  # noqa: F821 (resolved at runtime if defined above)
except Exception:
    bp = None

if bp:
    @bp.get("/portfolio/<owner>")
    def opti_portfolio_owner_fallback(owner):
        return jsonify({"owner":owner,"items":_opti_items(owner),"ts":int(time.time()*1000)})
    @bp.get("/portfolio")
    def opti_portfolio_query_fallback():
        from flask import request
        owner=(request.args.get("owner","") or "").strip()
        return jsonify({"owner":owner,"items":_opti_items(owner),"ts":int(time.time()*1000)})
else:
    @app.get("/api/portfolio/<owner>")
    def opti_portfolio_owner_fallback_app(owner):
        return jsonify({"owner":owner,"items":_opti_items(owner),"ts":int(time.time()*1000)})
    @app.get("/api/portfolio")
    def opti_portfolio_query_fallback_app():
        from flask import request
        owner=(request.args.get("owner","") or "").strip()
        return jsonify({"owner":owner,"items":_opti_items(owner),"ts":int(time.time()*1000)})
# === end /api/portfolio fallback ===
# === /api/portfolio inline fallback (idempotent) ===
try:
    import os, json, time, urllib.request
    from flask import jsonify, request

    def _rpc(u,m,p):
        d=json.dumps({'jsonrpc':'2.0','id':1,'method':m,'params':p}).encode()
        r=urllib.request.Request(u,data=d,headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(r,timeout=10) as x: return json.loads(x.read().decode())

    def _rpc_url(): return os.getenv('SOLANA_RPC','https://api.mainnet-beta.solana.com')
    def _mints():
        ms=[m.strip() for m in os.getenv('OPTILOVES_MINTS','').split(',') if m.strip()]
        return ms or ['5ihsE55yaFFZXoizZKv5xsd6YjEuvaXiiMr2FLjQztN9']

    def _items(owner):
        out=[]; rpc=_rpc_url()
        for m in _mints():
            resp=_rpc(rpc,'getTokenAccountsByOwner',[owner,{'mint':m},{'encoding':'jsonParsed'}])
            total=0.0
            for v in resp.get('result',{}).get('value',[]):
                ui=v['account']['data']['parsed']['info']['tokenAmount'].get('uiAmount',0) or 0
                try: total+=float(ui)
                except: pass
            price=float(os.getenv('OPTILOVES_BASE_PRICE_USD','50'))
            out.append({'mint':m,'balance':total,'price':price,'estValue':round(total*price,2)})
        return out

    def _pf_owner(owner):
        return jsonify({'owner':owner,'items':_items(owner),'ts':int(time.time()*1000)})

    def _pf_query():
        ow=(request.args.get('owner','') or '').strip()
        return jsonify({'owner':ow,'items':_items(ow),'ts':int(time.time()*1000)})

    # register on whichever module actually owns `app`
    try:
        have = any(str(r.rule).startswith('/api/portfolio') for r in app.url_map.iter_rules())
        if not have:
            app.add_url_rule('/api/portfolio/<owner>','opti_pf_owner',_pf_owner,methods=['GET'])
            app.add_url_rule('/api/portfolio','opti_pf_query',_pf_query,methods=['GET'])
    except Exception:
        pass
except Exception:
    pass
# === end /api/portfolio inline fallback ===

@app.before_request
def _api_key_gate():
    # Protect only /api/* endpoints
    p = request.path or ""
    if p.startswith("/api/"):
        supplied = request.headers.get("x-api-key", "")
        expected = os.environ.get("OPTI_API_KEY", "")
        if not expected or supplied != expected:
            return {"error":"forbidden"}, 403

