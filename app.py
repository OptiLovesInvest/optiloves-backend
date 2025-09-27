from flask import Flask, request, jsonify, make_response

app = Flask(__name__)

# --- health ---
@app.get("/_health")
def _health():
    return jsonify(ok=True), 200

# --- version header so we can verify deploys ---
@app.after_request
def after_request(resp):
    resp.headers["X-Opti-Version"] = "buy-stub-20250927-final"
    return resp

# --- early CORS preflight for /api/* and /buy/* (OPTIONS 204) ---
@app.before_request
def _early_preflight():
    if request.method == "OPTIONS" and (request.path.startswith("/api/") or request.path.startswith("/buy/")):
        resp = make_response("", 204)
        origin = request.headers.get("Origin", "")
        # Allow only production origins (your policy)
        if origin in {"https://optilovesinvest.com", "https://www.optilovesinvest.com"}:
            resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Vary"] = "Origin"
        resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "x-api-key, content-type"
        return resp  # short-circuit preflight

# --- debug: list routes (temporary) ---
@app.get("/__routes")
def __routes():
    rules = [str(r) for r in app.url_map.iter_rules()]
    return jsonify(ok=True, routes=sorted(rules)), 200

# --- BUY INTENT (stub) ---
@app.post("/buy/intent")
def buy_intent():
    data = (request.get_json(silent=True) or {})
    property_id = (data.get("property_id") or "").strip()
    owner = (data.get("owner") or "").strip()
    try:
        quantity = int(data.get("quantity") or 0)
    except Exception:
        quantity = 0
    if not property_id or not owner or quantity < 1:
        return jsonify(error="invalid_request",
                       message="property_id, owner, quantity>=1 required"), 400
    unit_price_usd = 50.00
    total_usd = unit_price_usd * quantity
    return jsonify(status="ok",
                   property_id=property_id,
                   owner=owner,
                   quantity=quantity,
                   unit_price_usd=unit_price_usd,
                   total_usd=total_usd,
                   client_secret="test_stub"), 200

# --- optional: register your existing blueprint safely (won't crash if missing) ---
try:
    from opti_routes import opti_routes
    app.register_blueprint(opti_routes, url_prefix="/api")
except Exception:
    pass
