from flask import Flask, jsonify, request, current_app as _ca

app = Flask(__name__)

# --- core health/ping ---
@app.get("/_health")
def _health():
    return {"ok": True, "service": "optiloves-backend"}, 200

@app.get("/api/ping")
def _ping():
    return {"ok": True}, 200

# --- always-on portfolio + routes (no deps) ---
@app.get("/api/routes")
def _routes():
    rules=[{"rule":str(r),"endpoint":r.endpoint,"methods":sorted(list(r.methods))} for r in _ca.url_map.iter_rules()]
    return {"ok": True, "routes": rules}, 200

@app.get("/api/portfolio/<owner>")
def _pf_owner(owner):
    owner=(owner or "").strip()
    if not owner:
        return jsonify({"owner":"", "items":[], "total":0, "source":"wsgi_final"}), 200
    return jsonify({"owner":owner, "items":[], "total":0, "source":"wsgi_final"}), 200

@app.get("/api/portfolio")
def _pf_q():
    owner=(request.args.get("owner","") or "").strip()
    if not owner:
        return jsonify({"error":"missing owner"}), 400
    return jsonify({"owner":owner, "items":[], "total":0, "source":"wsgi_final"}), 200

# --- best-effort: mount your existing blueprints if available ---
def _mount_optional_blueprints():
    try:
        from routes_shim import shim
        try: app.register_blueprint(shim, url_prefix="/api")
        except Exception: pass
    except Exception: pass
    try:
        from opti_routes import opti_routes
        try: app.register_blueprint(opti_routes, url_prefix="/api")
        except Exception: pass
    except Exception: pass

_mount_optional_blueprints()
