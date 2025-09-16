from app import app as application
app = application

# --- debug + portfolio routes defined at entrypoint (bulletproof) ---
from flask import request, jsonify, current_app as _ca

@app.get("/api/routes")
def _routes():
    rules=[{"rule":str(r),"endpoint":r.endpoint,"methods":sorted(list(r.methods))} for r in _ca.url_map.iter_rules()]
    return {"ok": True, "routes": rules}, 200

@app.get("/api/portfolio/<owner>")
def _wm_portfolio_owner(owner):
    owner=(owner or "").strip()
    if not owner:
        return jsonify({"owner":"", "items":[], "total":0, "source":"wsgi_main"}), 200
    return jsonify({"owner":owner, "items":[], "total":0, "source":"wsgi_main"}), 200

@app.get("/api/portfolio")
def _wm_portfolio_query():
    owner=(request.args.get("owner","") or "").strip()
    if not owner:
        return jsonify({"error":"missing owner"}), 400
    return jsonify({"owner":owner, "items":[], "total":0, "source":"wsgi_main"}), 200
