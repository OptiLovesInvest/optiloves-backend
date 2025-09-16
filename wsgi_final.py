from flask import Flask, jsonify, request, current_app as _ca
app = Flask(__name__)

@app.get("/_health")
def _health():
    return {"ok": True, "service": "optiloves-backend", "entry": "wsgi_final"}, 200

@app.get("/api/ping")
def _ping(): return {"ok": True}, 200

@app.get("/api/routes")
def _routes():
    rules=[{"rule":str(r),"endpoint":r.endpoint,"methods":sorted(list(r.methods))} for r in _ca.url_map.iter_rules()]
    return {"ok": True, "routes": rules, "entry": "wsgi_final"}, 200

@app.get("/api/portfolio/<owner>")
def _pf_owner(owner):
    owner=(owner or "").strip()
    return jsonify({"owner":owner, "items":[], "total":0, "source":"wsgi_final"}), 200

@app.get("/api/portfolio")
def _pf_q():
    owner=(request.args.get("owner","") or "").strip()
    if not owner: return jsonify({"error":"missing owner"}), 400
    return jsonify({"owner":owner, "items":[], "total":0, "source":"wsgi_final"}), 200
