from flask import Flask, jsonify, request, current_app as _ca
import os, json, urllib.request, time, threading
from collections import defaultdict

app = Flask(__name__)

API_KEY = os.environ.get("OPTI_API_KEY","")
RPC     = os.environ.get("SOLANA_RPC","https://api.mainnet-beta.solana.com")
MINTS   = [m.strip() for m in os.environ.get("OPTILOVES_MINTS","").split(",") if m.strip()]
TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
ORDERS_FILE = os.environ.get("ORDERS_FILE","/tmp/orders.json")
_ORDERS_LOCK = threading.Lock()

@app.before_request
def _api_key_guard():
    if request.path.startswith("/api") or request.path.startswith("/webhooks"):
        if API_KEY and request.headers.get("x-api-key") != API_KEY:
            return jsonify({"ok": False, "error": "unauthorized"}), 401

@app.get("/_health")
def _health():
    return {"ok": True, "service": "optiloves-backend", "entry": "wsgi_final_v3"}, 200

@app.get("/api/ping")
def _ping(): return {"ok": True}, 200

@app.get("/api/routes")
def _routes():
    rules=[{"rule":str(r),"endpoint":r.endpoint,"methods":sorted(list(r.methods))} for r in _ca.url_map.iter_rules()]
    return {"ok": True, "routes": rules, "entry": "wsgi_final_v3"}, 200

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
    return {"owner": owner, "items": items, "total": total, "source": "wsgi_final_v3"}

@app.get("/api/portfolio/<owner>")
def _pf_owner(owner): return jsonify(_portfolio(owner)), 200

@app.get("/api/portfolio")
def _pf_q():
    owner = (request.args.get("owner","") or "").strip()
    if not owner: return jsonify({"error":"missing owner"}), 400
    return jsonify(_portfolio(owner)), 200

# --- simple order store (file) ---
def _load_orders():
    try:
        with open(ORDERS_FILE,"r") as f: return json.load(f)
    except Exception:
        return []

def _save_orders(orders):
    try:
        with open(ORDERS_FILE,"w") as f: json.dump(orders,f)
    except Exception:
        pass

def _parse_order(req):
    data = req.get_json(silent=True) or {}
    reqd = ["order_id","property_id","owner","quantity","unit_price_usd","status"]
    missing = [k for k in reqd if data.get(k) in [None,""]]
    if missing: return None, {"ok":False,"error":"missing fields","missing":missing}, 400
    try:
        q = float(data["quantity"]); p = float(data["unit_price_usd"])
    except Exception:
        return None, {"ok":False,"error":"bad numeric"}, 400
    data["amount_usd"] = round(q*p, 2)
    data["ts"] = int(time.time())
    return data, None, None

@app.post("/webhooks/payment")
@app.post("/api/webhooks/payment")
def _wh_payment():
    data, err, code = _parse_order(request)
    if err: return jsonify(err), code
    with _ORDERS_LOCK:
        orders = _load_orders()
        for i,o in enumerate(orders):
            if o.get("order_id")==data["order_id"]:
                orders[i]=data; break
        else:
            orders.append(data)
        _save_orders(orders)
    return jsonify({"ok":True,"order":data}), 200

@app.get("/api/orders")
def _orders_list():
    return jsonify({"ok":True,"orders": _load_orders()}), 200
@app.get("/public/properties")
def _public_properties():
    return {
        "ok": True,
        "properties": [{
            "id": "nsele-hq",
            "name": "Kinshasa – Nsele HQ",
            "token_price_usd": 50,
            "status": "coming_soon"  # change to "live" when ready
        }]
    }, 200
# Env-driven public data override (no new routes)
def __public_properties_env():
    import os
    try:    price = float(os.environ.get("OPTI_PUBLIC_TOKEN_PRICE_USD","50"))
    except: price = 50.0
    status = os.environ.get("OPTI_PUBLIC_STATUS","coming_soon")  # "live" to enable Buy
    return {
        "ok": True,
        "properties": [{
            "id": "nsele-hq",
            "name": "Kinshasa – Nsele HQ",
            "token_price_usd": price,
            "status": status
        }]
    }, 200

# Safely replace the existing view function without re-registering the route
try:
    app.view_functions["_public_properties"] = __public_properties_env
except Exception:
    pass
