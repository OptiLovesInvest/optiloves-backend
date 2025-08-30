import os
from flask import Flask, jsonify, request, make_response

# Prefer existing app if importable
try:
    from app import app as app
except Exception:
    app = Flask(__name__)

ALLOWED = [o.strip() for o in os.getenv("ALLOWED_ORIGINS","https://optilovesinvest.com,https://www.optilovesinvest.com").split(",") if o.strip()]

def has_rule(path:str)->bool:
    try:
        return any(r.rule == path for r in app.url_map.iter_rules())
    except Exception:
        return False

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

# Root
if not has_rule("/"):
    def _root(): return jsonify(ok=True, service="optiloves-backend"), 200
    app.add_url_rule("/", endpoint="root_ok", view_func=_root, methods=["GET"])

# Health
if not has_rule("/_health"):
    def _health(): return jsonify(status="ok", service="optiloves-backend"), 200
    app.add_url_rule("/_health", endpoint="health_ok", view_func=_health, methods=["GET"])

# KYC (best-effort)
try:
    from kyc import kyc_bp
    if not any(r.rule.startswith("/api/kyc") for r in app.url_map.iter_rules()):
        app.register_blueprint(kyc_bp, url_prefix="/api/kyc")
except Exception:
    pass

# Properties payload
def _properties_payload():
    return {"items":[{"id":"kin-001","city":"Kinshasa – Nsele","price":50,"supply":1000},
                     {"id":"lua-001","city":"Luanda – Ilha","price":50,"supply":3000}]}

# /properties (GET + OPTIONS)
if not has_rule("/properties"):
    def _props_get():  return jsonify(_properties_payload()), 200
    def _props_opts(): return make_response(("",204))
    app.add_url_rule("/properties", endpoint="props_get", view_func=_props_get, methods=["GET"])
    app.add_url_rule("/properties", endpoint="props_opts", view_func=_props_opts, methods=["OPTIONS"])

# /api/properties (GET + OPTIONS)
if not has_rule("/api/properties"):
    def _apiprops_get():  return jsonify(_properties_payload()), 200
    def _apiprops_opts(): return make_response(("",204))
    app.add_url_rule("/api/properties", endpoint="apiprops_get", view_func=_apiprops_get, methods=["GET"])
    app.add_url_rule("/api/properties", endpoint="apiprops_opts", view_func=_apiprops_opts, methods=["OPTIONS"])