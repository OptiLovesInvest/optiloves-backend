import hmac
try:
    from opti_routes import opti_routes
    HAS_OPTI = True
except Exception as _e:
    HAS_OPTI = False
from routes_shim import shim as _opti_shim
from flask import Flask, request, jsonify, redirect

hmac
app = Flask(__name__)
if HAS_OPTI:
    try:
        app.register_blueprint(opti_routes, url_prefix="/api")
    except Exception as e:
        app.logger.warning("opti_routes blueprint not loaded: %s", e)

try:
    app.wsgi_app = _ApiKeyGate(app.wsgi_app)
except NameError:
    class _NoGate:
        def __init__(self, app): self.app = app
        def __call__(self, environ, start_response):
            return self.app(environ, start_response)
    app.wsgi_app = _NoGate(app.wsgi_app)
@app.before_request
def _api_key_gate():
    p = request.path or ""
    if p.startswith("/api/"):
        supplied = request.headers.get("x-api-key", "")
        expected = os.environ.get("OPTI_API_KEY", "")
        # Deny if no expected key on server
        if not expected:
            return {"error":"forbidden"}, 403
        # Constant-time comparison
        if not hmac.compare_digest(supplied, expected):
            return {"error":"forbidden"}, 403
try:
    if 'opti_shim' not in app.blueprints:
        app.register_blueprint(_opti_shim, url_prefix='/api')
except Exception:
    pass
# Opti shim routes
try:
    if 'opti_shim' not in app.blueprints:
        app.register_blueprint(_opti_shim, url_prefix='/api')
except Exception:
    pass
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
        from flask import request, jsonify, redirect
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
    # Register once, safely
    if 'opti' not in app.blueprints and 'opti_routes' not in app.blueprints:
        app.register_blueprint(_opti_bp)
    else:
        app.logger.info("blueprint already registered; skipping")
except Exception as e:
    app.logger.exception("failed to register blueprint: %s", e)




class _ApiKeyGate(object):
    def __init__(self, app):
        self.app = app
    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "") or ""
        if path.startswith("/api/"):
            supplied = environ.get("HTTP_X_API_KEY", "")
            expected = os.environ.get("OPTI_API_KEY", "")
            if not expected or not hmac.compare_digest(supplied, expected):
                start_response("403 FORBIDDEN", [("Content-Type","application/json"),("X-Opti-Gate","wrapped")])
                return [b"{\"error\":\"forbidden\"}"]
        def _sr(status, headers, exc_info=None):
            try: headers = list(headers)
            except: headers = []
            headers.append(("X-Opti-Gate","wrapped"))
            return start_response(status, headers, exc_info)
        return self.app(environ, _sr)

@app.route("/api/portfolio/<owner>", methods=["GET"])
def api_portfolio_owner(owner):
    # Keep logic single-sourced: redirect to query form
    return redirect(f"/api/portfolio?owner={owner}", code=307)


# ==== BEGIN ROUTE LISTER (temporary) ====
try:
    @app.get("/_routes")
    def _route_list():
        try:
            rules = []
            for r in app.url_map.iter_rules():
                rules.append({"rule": str(r), "endpoint": r.endpoint, "methods": sorted(list(r.methods))})
            return {"ok": True, "routes": rules}
        except Exception as e:
            return {"ok": False, "error": str(e)}, 500
except Exception as _e:
    pass
# ==== END ROUTE LISTER ====
# ==== BEGIN OPTI PORTFOLIO SHIMS (no-404, stable) ====
from flask import request, jsonify

def _call_portfolio_handler(owner: str):
    # Try the real handlers if present
    try:
        from opti_routes import portfolio_owner as _h1
        return _h1(owner)
    except Exception:
        pass
    try:
        from opti_routes import portfolio as _h2
        # expects request.args['owner']
        with app.test_request_context(f"/api/portfolio?owner={owner}"):
            return _h2()
    except Exception:
        pass
    # Fallback: return empty but valid shape (prevents 404 loops)
    return jsonify({"owner": owner, "items": [], "total": 0, "source": "shim"}), 200

@app.get("/api/portfolio/<owner>")
def _opti_portfolio_owner(owner):
    return _call_portfolio_handler(owner)

@app.get("/api/portfolio")
def _opti_portfolio_query():
    owner = request.args.get("owner","").strip()
    if not owner:
        return jsonify({"error":"missing owner"}), 400
    return _call_portfolio_handler(owner)
# ==== END OPTI PORTFOLIO SHIMS ====# ==== BEGIN OPTI PORTFOLIO (WSGI SHIM) ====
from flask import request, jsonify

def _opti_get_portfolio(owner: str):
    owner = (owner or "").strip()
    if not owner:
        return {"owner":"", "items":[], "total":0, "source":"wsgi_shim"}
    # TODO: replace with real RPC lookup; stable placeholder avoids 404
    return {"owner": owner, "items": [], "total": 0, "source": "wsgi_shim"}

@app.get("/api/portfolio/<owner>")
def opti_portfolio_owner(owner):
    return jsonify(_opti_get_portfolio(owner)), 200

@app.get("/api/portfolio")
def opti_portfolio_query():
    owner = request.args.get("owner","")
    if not owner:
        return jsonify({"error":"missing owner"}), 400
    return jsonify(_opti_get_portfolio(owner)), 200
# ==== END OPTI PORTFOLIO (WSGI SHIM) ====
# ==== BEGIN HELLO PROBE ====
@app.get("/api/hello")
def _hello_probe():
    return {"ok": True, "source": "app.py decorator"}, 200
# ==== END HELLO PROBE ====
# -- ensure routes_shim is mounted under /api (idempotent) --
try:
    from routes_shim import shim
    try:
        app.register_blueprint(shim, url_prefix="/api")
    except Exception as e:
        # already registered or harmless error
        try: app.logger.warning("routes_shim not (re)registered: %s", e)
        except Exception: pass
except Exception as e:
    try: app.logger.warning("routes_shim import failed: %s", e)
    except Exception: pass
# == BEGIN: force-mount blueprints ==
try:
    from routes_shim import shim
    try: app.register_blueprint(shim, url_prefix="/api")
    except Exception as e: 
        try: app.logger.warning("shim not (re)registered: %s", e)
        except: pass
except Exception as e:
    try: app.logger.warning("routes_shim import failed: %s", e)
    except: pass

try:
    from opti_routes import opti_routes
    try: app.register_blueprint(opti_routes, url_prefix="/api")
    except Exception as e:
        try: app.logger.warning("opti_routes not (re)registered: %s", e)
        except: pass
except Exception as e:
    try: app.logger.warning("opti_routes import failed: %s", e)
    except: pass
# == END: force-mount blueprints ==
# === BEGIN last-resort routes (stable, idempotent) ===
try:
    from flask import request, jsonify, current_app as _ca

    def __pf_owner(owner):
        owner = (owner or "").strip()
        if not owner:
            return jsonify({"owner":"", "items":[], "total":0, "source":"fallback"}), 200
        return jsonify({"owner":owner, "items":[], "total":0, "source":"fallback"}), 200

    def __pf_q():
        owner = (request.args.get("owner","") or "").strip()
        if not owner:
            return jsonify({"error":"missing owner"}), 400
        return jsonify({"owner":owner, "items":[], "total":0, "source":"fallback"}), 200

    def __routes():
        rules=[{"rule":str(r),"endpoint":r.endpoint,"methods":sorted(list(r.methods))} for r in _ca.url_map.iter_rules()]
        return {"ok": True, "routes": rules}, 200

    _rules = {str(r) for r in app.url_map.iter_rules()}
    if "/api/portfolio/<owner>" not in _rules:
        app.add_url_rule("/api/portfolio/<owner>", endpoint="__pf_owner", view_func=__pf_owner, methods=["GET"])
    if "/api/portfolio" not in _rules:
        app.add_url_rule("/api/portfolio", endpoint="__pf_q", view_func=__pf_q, methods=["GET"])
    if "/api/routes" not in _rules:
        app.add_url_rule("/api/routes", endpoint="__routes", view_func=__routes, methods=["GET"])
except Exception as __e:
    try:
        app.logger.warning("fallback routes attach skipped: %s", __e)
    except Exception:
        pass
# === END last-resort routes ===
# === BEGIN TEMP DIAG ===
try:
    from flask import request, jsonify
    import os, hashlib
    @app.route('/api/diag-auth', methods=['GET'])
    def api_diag_auth():
        # server side
        server_key = os.getenv('OPTI_API_KEY','')
        server_len = len(server_key)
        server_sha = hashlib.sha256(server_key.encode('utf-8')).hexdigest() if server_key else ''
        # client header
        hdr = request.headers.get('x-api-key') or request.headers.get('X-API-KEY') or request.headers.get('X-Api-Key') or ''
        hdr_len = len(hdr)
        hdr_present = bool(hdr_len)
        # safe boolean only
        match = (hdr == server_key) and bool(server_key)
        return jsonify({
            "server_key_len": server_len,
            "server_key_sha256": server_sha,
            "client_header_present": hdr_present,
            "client_header_len": hdr_len,
            "match": match
        }), 200
except Exception as _e:
    pass
# === END TEMP DIAG ===

# --- alias: buy checkout -> webhooks/payment ---
from flask import request, jsonify
import os, requests

@app.post("/buy/checkout")
def buy_checkout_alias():
    want = os.environ.get("OPTI_API_KEY")
    got  = request.headers.get("x-api-key") or request.headers.get("X-Api-Key") or request.headers.get("X-API-KEY")
    if not want or not got or got != want:
        return jsonify({"error":"unauthorized"}), 401

    url = f"{os.environ.get('SELF_BASE_URL','https://optiloves-backend.onrender.com')}/webhooks/payment"
    r = requests.post(url, headers={"x-api-key": want, "Content-Type":"application/json"}, data=request.data, timeout=15)
    return (r.text, r.status_code, {"Content-Type": r.headers.get("Content-Type","application/json")})
# --- OptiLoves CORS preflight shim (stable, idempotent) ---
from flask import request, make_response

_ALLOWED_ORIGINS = {'https://optilovesinvest.com', 'https://www.optilovesinvest.com'}

@app.before_request
def _opt_preflight_204():
    # Return 204 for CORS preflight on /buy/* and /api/*, echoing allowed origin
    if request.method == 'OPTIONS' and (request.path.startswith('/buy/') or request.path.startswith('/api/')):
        origin = request.headers.get('Origin')
        resp = make_response('', 204)
        h = resp.headers
        if origin in _ALLOWED_ORIGINS:
            h['Access-Control-Allow-Origin'] = origin
            h['Vary'] = 'Origin'
        h['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
        h['Access-Control-Allow-Headers'] = 'Content-Type, X-API-Key'
        return resp
# --- end shim ---
