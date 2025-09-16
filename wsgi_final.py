from flask import Flask, jsonify, request, current_app as _ca
import os, json, urllib.request
from collections import defaultdict

app = Flask(__name__)

API_KEY = os.environ.get("OPTI_API_KEY","")
RPC     = os.environ.get("SOLANA_RPC","https://api.mainnet-beta.solana.com")
MINTS   = [m.strip() for m in os.environ.get("OPTILOVES_MINTS","").split(",") if m.strip()]
TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"

@app.before_request
def _api_key_guard():
    if request.path.startswith("/api") and API_KEY:
        if request.headers.get("x-api-key") != API_KEY:
            return jsonify({"ok": False, "error": "unauthorized"}), 401

@app.get("/_health")
def _health():
    return {"ok": True, "service": "optiloves-backend", "entry": "wsgi_final_v2"}, 200

@app.get("/api/ping")
def _ping(): return {"ok": True}, 200

def _rpc(method, params):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req  = urllib.request.Request(RPC, data=body, headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())

def _portfolio(owner: str):
    owner = (owner or "").strip()
    items = []
    if MINTS:
        for mint in MINTS:
            try:
                res = _rpc("getTokenAccountsByOwner", [owner, {"mint": mint}, {"encoding":"jsonParsed"}])
                bal = 0.0
                for it in res.get("result", {}).get("value", []):
                    try:
                        amt = it["account"]["data"]["parsed"]["info"]["tokenAmount"]["uiAmount"]
                        bal += float(amt or 0)
                    except Exception: pass
                items.append({"mint": mint, "amount": bal})
            except Exception as e:
                items.append({"mint": mint, "amount": 0.0, "error": str(e)[:140]})
    else:
        try:
            res = _rpc("getTokenAccountsByOwner", [owner, {"programId": TOKEN_PROGRAM}, {"encoding":"jsonParsed"}])
            by_mint = defaultdict(float)
            for it in res.get("result", {}).get("value", []):
                try:
                    info = it["account"]["data"]["parsed"]["info"]
                    mint = info.get("mint"); amt = info["tokenAmount"]["uiAmount"] or 0
                    by_mint[mint] += float(amt)
                except Exception: pass
            items = [{"mint": m, "amount": a} for m, a in by_mint.items()]
        except Exception as e:
            items = [{"mint": "unknown", "amount": 0.0, "error": str(e)[:160]}]
    total = sum(i.get("amount", 0.0) for i in items)
    return {"owner": owner, "items": items, "total": total, "source": "wsgi_final_v2"}

@app.get("/api/portfolio/<owner>")
def _pf_owner(owner): return jsonify(_portfolio(owner)), 200

@app.get("/api/portfolio")
def _pf_q():
    owner = (request.args.get("owner","") or "").strip()
    if not owner: return jsonify({"error":"missing owner"}), 400
    return jsonify(_portfolio(owner)), 200

@app.get("/api/routes")
def _routes():
    rules=[{"rule":str(r),"endpoint":r.endpoint,"methods":sorted(list(r.methods))} for r in _ca.url_map.iter_rules()]
    return {"ok": True, "routes": rules, "entry": "wsgi_final_v2"}, 200

@app.get("/api/debug/env")
def _env():
    return {"ok": True, "MINTS": MINTS, "RPC": (RPC[:40]+"..." if RPC else "")}, 200

# optional: mount your existing blueprints
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
