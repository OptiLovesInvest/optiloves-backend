from flask import Flask, make_response
app = Flask(__name__)

@app.route("/_health")
def _health():
    return make_response("  ok\n  --\nTrue\n\n", 200)

@app.route("/")
def index():
    return make_response("", 204)
# --- OPTI: begin minimal diagnostics (safe, reversible) ---
import os, json
import urllib.request
from collections import defaultdict
from flask import request, jsonify, abort

def _opti_require_api_key():
    expected = os.environ.get("OPTI_API_KEY","").strip()
    got = request.headers.get("x-api-key","").strip()
    if not expected or got != expected:
        abort(404)

@app.route("/api/ping", methods=["GET"])
def opti_ping():
    _opti_require_api_key()
    return jsonify(ok=True, service="optiloves-backend", ts=int(__import__("time").time()*1000))

    if not owner: return jsonify(ok=False, error="missing owner"), 400
    return jsonify(ok=True, owner=owner, items=[])
# --- OPTI: end minimal diagnostics ---

# --- BUY CHECKOUT (temporary stub to unblock investor flow) ---
# Frontend expects: GET /buy/checkout?qty=1  ->  { ok:true, url:"https://optilovesinvest.com/thank-you" }
from flask import request, jsonify
import os

@app.get("/buy/checkout")
def buy_checkout():
    """
    Creates a Stripe Checkout Session and returns { ok:true, url }.
    Safe fallback: if Stripe is not configured, return thank-you URL.
    """
    import os
    from flask import request, jsonify

    # qty from querystring
    raw = request.args.get("qty", "1")
    try:
        qty = int(raw)
    except Exception:
        qty = 1
    if qty < 1:
        qty = 1
    if qty > 100:
        qty = 100

    # Required env vars
    stripe_secret = os.getenv("STRIPE_SECRET_KEY", "").strip()
    price_id = os.getenv("STRIPE_PRICE_ID", "").strip()
    success_url = os.getenv("STRIPE_SUCCESS_URL", "https://optilovesinvest.com/thank-you").strip()
    cancel_url = os.getenv("STRIPE_CANCEL_URL", "https://optilovesinvest.com/buy").strip()

    # If Stripe not configured, do not break the site
    if not stripe_secret or not price_id:
        return jsonify(ok=True, qty=qty, url=success_url, mode="fallback")

    try:
        import stripe
        stripe.api_key = stripe_secret

        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[{"price": price_id, "quantity": qty}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"propertyId": "kin-001", "quantity": str(qty)},
        )

        return jsonify(ok=True, qty=qty, url=session.url, sessionId=session.id, mode="stripe")

    except Exception as e:
        # Safety: never expose secrets; return minimal error
        return jsonify(ok=False, error="checkout_failed", detail=str(e)[:200]), 500


# --- Optiloves Invest: Apply endpoint (api-key guarded) ---
from flask import request, jsonify
import os

def _opti_expected_api_key():
    return os.getenv("OPTI_API_KEY") or os.getenv("API_KEY") or os.getenv("OPTILOVES_API_KEY")

def _opti_require_api_key():
    expected = _opti_expected_api_key()
    if not expected:
        return jsonify({"ok": False, "error": "Server missing OPTI_API_KEY"}), 500
    got = request.headers.get("x-api-key", "")
    if (not got) or (got != expected):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401
    return None

@app.post("/api/apply")
def api_apply():
    gate = _opti_require_api_key()
    if gate: return gate

    body = request.get_json(silent=True) or {}
    amt_raw = body.get("amount", body.get("allocation", body.get("amount_usd", 0)))

    try:
        amount = float(amt_raw)
    except Exception:
        return jsonify({"ok": False, "error": "Invalid amount"}), 400

    if amount < 100 or amount > 1000:
        return jsonify({"ok": False, "error": "Amount must be between 100 and 1000"}), 400

    return jsonify({"ok": True})


# === OPTILOVES PORTFOLIO FIX ===
RPC = os.environ.get("SOLANA_RPC", "https://api.mainnet-beta.solana.com")
MINTS = [m.strip() for m in os.environ.get("OPTILOVES_MINTS","").split(",") if m.strip()]
TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"

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
                        info = it["account"]["data"]["parsed"]["info"]
                        amt = info["tokenAmount"]["uiAmount"] or 0
                        bal += float(amt)
                    except Exception:
                        pass

                if bal > 0:
                    items.append({
                        "mint": mint,
                        "balance": bal,
                        "price": 50,
                        "estValue": bal * 50
                    })
            except Exception:
                pass

    total = sum(i["balance"] for i in items)
    return {"owner": owner, "items": items, "total": total}
# === END OPTILOVES PORTFOLIO FIX ===



# === OPTILOVES PORTFOLIO ROUTES ===
import urllib.request
from collections import defaultdict

RPC = os.environ.get("SOLANA_RPC", "https://api.mainnet-beta.solana.com")
MINTS = [m.strip() for m in os.environ.get("OPTILOVES_MINTS","").split(",") if m.strip()]
TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"

def _rpc(method, params):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req = urllib.request.Request(RPC, data=body, headers={"Content-Type":"application/json"})
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
                        info = it["account"]["data"]["parsed"]["info"]
                        amt = info["tokenAmount"]["uiAmount"] or 0
                        bal += float(amt)
                    except Exception:
                        pass
                if bal > 0:
                    items.append({
                        "mint": mint,
                        "balance": bal,
                        "price": 50,
                        "estValue": bal * 50
                    })
            except Exception as e:
                items.append({
                    "mint": mint,
                    "balance": 0.0,
                    "price": 50,
                    "estValue": 0.0,
                    "error": str(e)[:140]
                })
    else:
        try:
            res = _rpc("getTokenAccountsByOwner", [owner, {"programId": TOKEN_PROGRAM}, {"encoding":"jsonParsed"}])
            by_mint = defaultdict(float)
            for it in res.get("result", {}).get("value", []):
                try:
                    info = it["account"]["data"]["parsed"]["info"]
                    mint = info.get("mint")
                    amt = info["tokenAmount"]["uiAmount"] or 0
                    by_mint[mint] += float(amt)
                except Exception:
                    pass
            items = [{
                "mint": m,
                "balance": a,
                "price": 50,
                "estValue": a * 50
            } for m, a in by_mint.items() if a > 0]
        except Exception as e:
            items = [{
                "mint": "unknown",
                "balance": 0.0,
                "price": 50,
                "estValue": 0.0,
                "error": str(e)[:160]
            }]

    total = sum(i.get("balance", 0.0) for i in items)
    return {"ok": True, "owner": owner, "items": items, "total": total, "source": "app_portfolio_v1"}

@app.route("/api/portfolio/<owner>", methods=["GET"])
def portfolio_owner(owner):
    _opti_require_api_key()
    owner = (owner or "").strip()
    if not owner:
        return jsonify({"ok": False, "error": "missing owner"}), 400
    return jsonify(_portfolio(owner)), 200

@app.route("/api/portfolio", methods=["GET"])
def portfolio_query():
    _opti_require_api_key()
    owner = (request.args.get("owner","") or "").strip()
    if not owner:
        return jsonify({"ok": False, "error": "missing owner"}), 400
    return jsonify(_portfolio(owner)), 200
# === END OPTILOVES PORTFOLIO ROUTES ===

