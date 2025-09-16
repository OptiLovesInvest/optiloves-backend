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
# ---- add just below the existing imports in wsgi_final.py ----
import os, json, urllib.request

API_KEY = os.environ.get("OPTI_API_KEY","")
RPC     = os.environ.get("SOLANA_RPC","https://api.mainnet-beta.solana.com")
MINTS   = [m.strip() for m in os.environ.get("OPTILOVES_MINTS","").split(",") if m.strip()]

@app.before_request
def _api_key_guard():
    from flask import request, jsonify
    if request.path.startswith("/api") and API_KEY:
        if request.headers.get("x-api-key") != API_KEY:
            return jsonify({"ok": False, "error": "unauthorized"}), 401

def _rpc(method, params):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req  = urllib.request.Request(RPC, data=body, headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())

def _portfolio(owner: str):
    owner = (owner or "").strip()
    items = []
    for mint in MINTS:
        try:
            res = _rpc("getTokenAccountsByOwner", [owner, {"mint": mint}, {"encoding":"jsonParsed"}])
            bal = 0.0
            for it in res.get("result", {}).get("value", []):
                try:
                    amt = it["account"]["data"]["parsed"]["info"]["tokenAmount"]["uiAmount"]
                    bal += float(amt or 0)
                except Exception:
                    pass
            items.append({"mint": mint, "amount": bal})
        except Exception as e:
            items.append({"mint": mint, "amount": 0.0, "error": str(e)[:120]})
    total = sum(i["amount"] for i in items)
    return {"owner": owner, "items": items, "total": total, "source": "wsgi_final+rpc"}

# replace the two portfolio handlers' bodies with calls into _portfolio:
# (Safe to paste even if they already exist; you’re redefining them below.)
@app.get("/api/portfolio/<owner>")
def _pf_owner(owner):
    from flask import jsonify
    return jsonify(_portfolio(owner)), 200

@app.get("/api/portfolio")
def _pf_q():
    from flask import request, jsonify
    owner = (request.args.get("owner","") or "").strip()
    if not owner: return jsonify({"error":"missing owner"}), 400
    return jsonify(_portfolio(owner)), 200
# === RPC portfolio + API key guard (stable) ===
import os, json, urllib.request
from collections import defaultdict

API_KEY = os.environ.get("OPTI_API_KEY","")
RPC     = os.environ.get("SOLANA_RPC","https://api.mainnet-beta.solana.com")
MINTS   = [m.strip() for m in os.environ.get("OPTILOVES_MINTS","").split(",") if m.strip()]
TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"

@app.before_request
def _api_key_guard():
    from flask import request, jsonify
    if request.path.startswith("/api") and API_KEY:
        if request.headers.get("x-api-key") != API_KEY:
            return jsonify({"ok": False, "error": "unauthorized"}), 401

def _rpc(method, params):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req  = urllib.request.Request(RPC, data=body, headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())

def _portfolio(owner: str):
    owner = (owner or "").strip()
    items = []
    if MINTS:
        # explicit mint list
        for mint in MINTS:
            try:
                res = _rpc("getTokenAccountsByOwner", [owner, {"mint": mint}, {"encoding":"jsonParsed"}])
                bal = 0.0
                for it in res.get("result", {}).get("value", []):
                    try:
                        amt = it["account"]["data"]["parsed"]["info"]["tokenAmount"]["uiAmount"]
                        bal += float(amt or 0)
                    except Exception:
                        pass
                items.append({"mint": mint, "amount": bal})
            except Exception as e:
                items.append({"mint": mint, "amount": 0.0, "error": str(e)[:140]})
    else:
        # auto-discover all SPL token balances
        try:
            res = _rpc("getTokenAccountsByOwner", [owner, {"programId": TOKEN_PROGRAM}, {"encoding":"jsonParsed"}])
            by_mint = defaultdict(float)
            for it in res.get("result", {}).get("value", []):
                try:
                    info = it["account"]["data"]["parsed"]["info"]
                    mint = info.get("mint")
                    amt  = info["tokenAmount"]["uiAmount"] or 0
                    by_mint[mint] += float(amt)
                except Exception:
                    pass
            items = [{"mint": m, "amount": a}] + [] if False else [{"mint": m, "amount": a} for m, a in by_mint.items()]
        except Exception as e:
            items = [{"mint": "unknown", "amount": 0.0, "error": str(e)[:160]}]
    total = sum(i.get("amount", 0.0) for i in items)
    return {"owner": owner, "items": items, "total": total, "source": "wsgi_final+rpc"}

# SAFE override of existing handlers without re-adding routes
def __pf_owner_rpc(owner):
    from flask import jsonify
    return jsonify(_portfolio(owner)), 200

def __pf_q_rpc():
    from flask import request, jsonify
    owner = (request.args.get("owner","") or "").strip()
    if not owner: return jsonify({"error":"missing owner"}), 400
    return jsonify(_portfolio(owner)), 200

# Prefer replacing existing endpoints; if missing, add rules
try:
    app.view_functions['_pf_owner'] = __pf_owner_rpc
    app.view_functions['_pf_q']     = __pf_q_rpc
except KeyError:
    try:
        app.add_url_rule("/api/portfolio/<owner>", endpoint="_pf_owner", view_func=__pf_owner_rpc, methods=["GET"])
        app.add_url_rule("/api/portfolio",        endpoint="_pf_q",     view_func=__pf_q_rpc,     methods=["GET"])
    except Exception:
        pass

# tiny env inspector (debug): /api/debug/env
@app.get("/api/debug/env")
def _env():
    return {"ok": True, "MINTS": MINTS, "RPC": RPC[:40]+"..." if RPC else ""}, 200
# === END RPC patch ===
