from app import app  # Flask app instance must be named `app`
# ==== OPTI CORS v20250831 (strict, idempotent) ====
try:
    from flask import request
    _OPTI_ALLOWED = {"https://optilovesinvest.com","https://www.optilovesinvest.com"}

    @app.after_request
    def _opti_cors(resp):
        try:
            origin = request.headers.get("Origin", "")
            if origin in _OPTI_ALLOWED:
                resp.headers["Access-Control-Allow-Origin"] = origin
                resp.headers["Access-Control-Allow-Credentials"] = "true"
                resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
                resp.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
                resp.headers["Access-Control-Max-Age"] = "86400"
                # Ensure caches donâ€™t mix origins
                vary = resp.headers.get("Vary")
                resp.headers["Vary"] = ("Origin" if not vary else (vary + ", Origin") if "Origin" not in vary else vary)
        except Exception:
            pass
        return resp

    # Preflight for any API path (no secrets, no body)
    def _opti_preflight(path=""):
        from flask import Response
        r = Response("", status=204)
        return r
    # Register once (safe if duplicate)
    _reg = getattr(app, "_opti_preflight_registered", False)
    if not _reg:
        app.add_url_rule("/api/<path:path>", "opti_preflight_api", _opti_preflight, methods=["OPTIONS"])
        app.add_url_rule("/api", "opti_preflight_api_root", _opti_preflight, methods=["OPTIONS"])
        setattr(app, "_opti_preflight_registered", True)
except Exception:
    pass
# ==== /OPTI CORS ====

# ==== OPTI CORS v20250831 (strict, idempotent) ====
from flask import request, Response
_OPTI_ALLOWED = {"https://optilovesinvest.com","https://www.optilovesinvest.com"}

@app.after_request
def _opti_cors(resp):
    try:
        origin = request.headers.get("Origin", "")
        if origin in _OPTI_ALLOWED:
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Access-Control-Allow-Credentials"] = "true"
            resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
            resp.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
            resp.headers["Access-Control-Max-Age"] = "86400"
            vary = resp.headers.get("Vary")
            resp.headers["Vary"] = ("Origin" if not vary else (vary + ", Origin") if "Origin" not in vary else vary)
    except Exception:
        pass
    return resp

def _opti_preflight(path=""):
    return Response("", status=204)

if not getattr(app, "_opti_preflight_registered", False):
    app.add_url_rule("/api/<path:path>", "opti_preflight_api", _opti_preflight, methods=["OPTIONS"])
    app.add_url_rule("/api", "opti_preflight_api_root", _opti_preflight, methods=["OPTIONS"])
    setattr(app, "_opti_preflight_registered", True)
# ==== /OPTI CORS ====
# ==== OPTI GET shim for /api/portfolio/<owner> (temporary, reversible) ====
import os
from flask import request, Response, jsonify

def _opti_try_forward_post(owner):
    try:
        import requests
    except Exception:
        # requests not available
        return jsonify({"owner": owner, "items": [], "error": "requests not installed; POST-only route"}), 501
    base = os.environ.get("EXTERNAL_BASE_URL", "https://optiloves-backend.onrender.com")
    try:
        r = requests.post(f"{base}/api/portfolio", json={"owner": owner}, timeout=8)
        # mirror POST response transparently
        ct = r.headers.get("Content-Type", "application/json")
        return Response(response=r.content, status=r.status_code, content_type=ct)
    except Exception as e:
        return jsonify({"owner": owner, "items": [], "error": str(e)}), 502

@app.route("/api/portfolio/<owner>", methods=["GET","OPTIONS"])
def _opti_portfolio_get(owner):
    if request.method == "OPTIONS":
        return Response("", status=204)
    return _opti_try_forward_post(owner)
# ==== /GET shim ====