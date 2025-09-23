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
import os
from flask import send_file
_BASE = os.path.dirname(os.path.abspath(__file__))

@app.get("/")
def _site_home():
    return send_file(os.path.join(_BASE, "index.html"))
import os
from flask import send_from_directory
_BASE = os.path.dirname(os.path.abspath(__file__))

def _site_home():
    return send_from_directory(_BASE, "index.html")

# register "/" if missing; also expose "/index.html"
_rules = {str(r) for r in app.url_map.iter_rules()}
if "/" not in _rules:
    app.add_url_rule("/", endpoint="_site_home", view_func=_site_home, methods=["GET"])

def _site_index():
    return send_from_directory(_BASE, "index.html")
if "/index.html" not in _rules:
    app.add_url_rule("/index.html", endpoint="_site_index", view_func=_site_index, methods=["GET"])
@app.get("/buy/nsele-hq")
def _buy_placeholder():
    return {"ok":True,"msg":"Buy flow coming soon"}, 200
def __buy_placeholder():
    return {"ok": True, "msg": "Buy flow coming soon"}, 200

# Ensure route is present even if decorators were skipped in a prior version
try:
    _rules = {str(r) for r in app.url_map.iter_rules()}
    if "/buy/nsele-hq" not in _rules:
        app.add_url_rule("/buy/nsele-hq", endpoint="buy_nsele_hq", view_func=__buy_placeholder, methods=["GET"])
except Exception:
    pass
import uuid, time
from flask import Response, redirect, url_for

def _public_price_status():
    try: price = float(os.environ.get("OPTI_PUBLIC_TOKEN_PRICE_USD","50"))
    except: price = 50.0
    status = os.environ.get("OPTI_PUBLIC_STATUS","coming_soon")
    return price, status

@app.get("/buy/nsele-hq")
def _buy_page():
    price, status = _public_price_status()
    if status != "live":
        return Response(f"<h1>Nsele HQ</h1><p>Price: ${price:.2f}</p><p>Not available yet.</p>", mimetype="text/html")
    html = f"""
<!doctype html><meta charset='utf-8'>
<h1>Buy — Nsele HQ</h1>
<p>Token price: <strong>${price:.2f}</strong></p>
<form method="post" action="/buy/submit">
  <label>Owner (wallet): <input name="owner" required style="width:360px"></label><br><br>
  <label>Quantity: <input name="quantity" type="number" min="1" value="1" required></label><br><br>
  <input type="hidden" name="property_id" value="kin-001">
  <button type="submit">Place order</button>
</form>
"""
    return Response(html, mimetype="text/html")

@app.post("/buy/submit")
def _buy_submit():
    # No gateway here — demo: write order same as webhook
    owner = (request.form.get("owner","") or "").strip()
    qty   = float(request.form.get("quantity","0") or 0)
    pid   = request.form.get("property_id","kin-001")
    price, status = _public_price_status()
    if not owner or qty <= 0:
        return {"ok":False,"error":"owner and quantity required"}, 400
    data = {
        "order_id": "buy-" + uuid.uuid4().hex,
        "property_id": pid,
        "owner": owner,
        "quantity": qty,
        "unit_price_usd": price,
        "status": "completed",
        "amount_usd": round(qty*price,2),
        "ts": int(time.time())
    }
    try:
        # Reuse file store
        orders = _load_orders()
        orders.append(data)
        _save_orders(orders)
    except Exception:
        pass
    return redirect(url_for("_thank_you", order_id=data["order_id"]))

@app.get("/thank-you")
def _thank_you():
    oid = request.args.get("order_id","")
    return Response(f"<h1>Thank you</h1><p>Order: {oid}</p><p>We have recorded your purchase.</p>", mimetype="text/html")
# --- Stripe Checkout + Webhook (public) ---
try:
    import stripe, os
    STRIPE_SECRET = os.environ.get("STRIPE_SECRET_KEY","")
    STRIPE_PRICE  = os.environ.get("STRIPE_PRICE_ID","")         # optional: use a pre-made Price
    STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET","")
    if STRIPE_SECRET:
        stripe.api_key = STRIPE_SECRET

        @app.post("/buy/checkout")   # PUBLIC (no API key)
        def _stripe_checkout_public():
            from flask import request, jsonify
            price, status = _public_price_status()
            # accept form or JSON
            owner = (request.form.get("owner") or (request.get_json(silent=True) or {}).get("owner") or "").strip()
            qty_raw = request.form.get("quantity") or (request.get_json(silent=True) or {}).get("quantity")
            try: qty = int(float(qty_raw or 1))
            except: qty = 1
            if status != "live":
                return jsonify({"ok":False,"error":"not_live"}), 400
            if not owner:
                return jsonify({"ok":False,"error":"owner_required"}), 400

            base = request.host_url.rstrip("/")
            success = f"{base}/thank-you?order_id={{CHECKOUT_SESSION_ID}}"
            cancel  = f"{base}/buy/nsele-hq"

            args = dict(
                mode="payment",
                success_url=success,
                cancel_url=cancel,
                metadata={"owner": owner, "property_id":"kin-001", "quantity": str(qty), "unit_price_usd": str(price)}
            )
            if STRIPE_PRICE:
                args["line_items"] = [{"price": STRIPE_PRICE, "quantity": qty}]
            else:
                args["line_items"] = [{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": "Nsele HQ token"},
                        "unit_amount": int(round(price*100))
                    },
                    "quantity": qty
                }]

            sess = stripe.checkout.Session.create(**args)
            return jsonify({"ok":True, "url": sess.url}), 200

        @app.post("/stripe/webhook")  # PUBLIC (Stripe signs requests)
        def _stripe_webhook_public():
            from flask import request, jsonify
            if not STRIPE_WEBHOOK_SECRET:
                return jsonify({"ok":False,"error":"no_webhook_secret"}), 400
            payload = request.data
            sig = request.headers.get("Stripe-Signature","")
            try:
                event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
            except Exception:
                return jsonify({"ok":False,"error":"bad_signature"}), 400

            if event.get("type") == "checkout.session.completed":
                s = event["data"]["object"]
                if (s.get("payment_status") == "paid") or (s.get("status") == "complete"):
                    md = s.get("metadata") or {}
                    try:
                        q = float(md.get("quantity","1")); p = float(md.get("unit_price_usd","50"))
                    except Exception:
                        q, p = 1, 50.0
                    data = {
                        "order_id": "stripe-" + (s.get("id") or ""),
                        "property_id": md.get("property_id","kin-001"),
                        "owner": md.get("owner",""),
                        "quantity": q,
                        "unit_price_usd": p,
                        "status": "completed",
                        "amount_usd": round(q*p, 2),
                        "ts": int(time.time())
                    }
                    try:
                        orders = _load_orders()
                        for i,o in enumerate(orders):
                            if o.get("order_id")==data["order_id"]:
                                orders[i]=data; break
                        else:
                            orders.append(data)
                        _save_orders(orders)
                    except Exception:
                        pass
            return {"ok":True}, 200
except Exception:
    pass
# --- END Stripe ---

# === OPTI GLOBAL PREFLIGHT (inserted) ===
ALLOWED_ORIGINS = {"https://optilovesinvest.com", "https://www.optilovesinvest.com"}

class OptiPreflightMiddleware:
    def __init__(self, app):
        self.app = app
    def __call__(self, environ, start_response):
        if environ.get("REQUEST_METHOD") == "OPTIONS":
            origin = environ.get("HTTP_ORIGIN", "")
            headers = [
                ("Vary", "Origin"),
                ("Access-Control-Allow-Methods", "GET,POST,OPTIONS"),
                ("Access-Control-Allow-Headers", "x-api-key, content-type"),
                ("Content-Length", "0"),
            ]
            if origin in ALLOWED_ORIGINS:
                headers.append(("Access-Control-Allow-Origin", origin))
            start_response("204 No Content", headers)
            return [b""]
        return self.app(environ, start_response)
# === END OPTI GLOBAL PREFLIGHT ===

app = OptiPreflightMiddleware(app)

