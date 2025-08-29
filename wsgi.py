import os
from flask import Flask, jsonify, request, make_response

try:
    from app import app as app  # use existing app if import works
except Exception:
    app = Flask(__name__)

# ---- Allowed origins (strict) ----
ALLOWED = [o.strip() for o in os.getenv("ALLOWED_ORIGINS","https://optilovesinvest.com,https://www.optilovesinvest.com").split(",") if o.strip()]

# ---- Uniform CORS (works even without flask-cors) ----
@app.after_request
def add_cors(resp):
    origin = request.headers.get("Origin")
    if origin and origin in ALLOWED:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Vary"] = "Origin"
        resp.headers["Access-Control-Allow-Credentials"] = "true"
        resp.headers["Access-Control-Allow-Headers"] = request.headers.get("Access-Control-Request-Headers","Content-Type, Authorization")
        resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return resp

# Root + Health
@app.get("/")
def root():
    return jsonify(ok=True, service="optiloves-backend"), 200

@app.get("/_health")
def _health():
    return jsonify(status="ok", service="optiloves-backend"), 200

# KYC blueprint (best-effort)
try:
    from kyc import kyc_bp
    if not any(r.rule.startswith("/api/kyc") for r in app.url_map.iter_rules()):
        app.register_blueprint(kyc_bp, url_prefix="/api/kyc")
except Exception:
    pass

# ---- Properties (explicit GET + OPTIONS) ----
def _properties_payload():
    return {"items":[{"id":"kin-001","city":"Kinshasa – Nsele","price":50,"supply":1000}]}

@app.route("/properties", methods=["GET","OPTIONS"])
def properties():
    if request.method == "OPTIONS":
        return make_response(("", 204))
    return jsonify(_properties_payload()), 200

@app.route("/api/properties", methods=["GET","OPTIONS"])
def api_properties():
    if request.method == "OPTIONS":
        return make_response(("", 204))
    return jsonify(_properties_payload()), 200