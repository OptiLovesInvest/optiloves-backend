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
                # Ensure caches donÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢t mix origins
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
# ==== OPTI ROUTES DEBUG (guarded) ====
import os
if os.environ.get("OPTI_DEBUG_ROUTES") == "1":
    def _routes():
        data=[]
        for r in app.url_map.iter_rules():
            methods = sorted(list((r.methods or set()) - {"HEAD"}))
            data.append({"rule": str(r), "endpoint": r.endpoint, "methods": methods})
        return {"routes": data}
# ==== /OPTI ROUTES DEBUG ====

# ==== OPTI: Agent headers hard block ====
import os
from flask import request, jsonify

@app.before_request
def _opti_block_agents():
    if os.environ.get('DISABLE_AGENTS', '1') != '0':
        # Block if any X-Agent-* header present
        for k in request.headers.keys():
            if k.lower().startswith('x-agent-'):
                return jsonify({"error":"agent_headers_forbidden","detail":k}), 403
# Also reject CORS preflight that asks to send X-Agent-* headers
@app.route('/_preflight', methods=['OPTIONS'])
def _opti_preflight():
    acrh = request.headers.get('Access-Control-Request-Headers','').lower()
    if 'x-agent-' in acrh:
        return ('', 403)
    return ('', 204)
# ==== /OPTI ====
# ==== OPTI: Block agent headers in CORS preflight ====
@app.before_request
def _opti_block_agent_preflight():
    import os
    from flask import request
    if os.environ.get('DISABLE_AGENTS','1')!='0':
        acrh = request.headers.get('Access-Control-Request-Headers','').lower()
        if 'x-agent-' in acrh:
            return ('',403)
# ==== /OPTI ====
# ==== OPTI: WSGI middleware to block agent headers (pre-routing) ====
class _OptiBlockAgentsMiddleware:
    def __init__(self, app):
        self.app = app
    def __call__(self, environ, start_response):
        import os
        if os.environ.get('DISABLE_AGENTS','1') != '0':
            # Block any custom X-Agent-* header on normal requests
            for k,v in environ.items():
                if k.startswith('HTTP_') and k.lower().startswith('http_x_agent_'):
                    start_response('403 FORBIDDEN',[('Content-Length','0')]); return [b'']
            # Block CORS preflight that asks to send X-Agent-* headers
            acrh = environ.get('HTTP_ACCESS_CONTROL_REQUEST_HEADERS','').lower()
            if 'x-agent-' in acrh:
                start_response('403 FORBIDDEN',[('Content-Length','0')]); return [b'']
        return self.app(environ, start_response)

# Wrap the Flask app (must be after 'app' is defined)
app.wsgi_app = _OptiBlockAgentsMiddleware(app.wsgi_app)
# ==== /OPTI ====