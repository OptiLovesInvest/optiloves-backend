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

@app.route("/api/portfolio", methods=["GET"])
def opti_portfolio_qs():
    _opti_require_api_key()
    owner = request.args.get("owner","").strip()
    if not owner: return jsonify(ok=False, error="missing owner"), 400
    # If your real handler exists, call it here instead:
    # return real_portfolio_handler(owner)
    return jsonify(ok=True, owner=owner, items=[])

@app.route("/api/portfolio/<owner>", methods=["GET"])
def opti_portfolio_path(owner):
    _opti_require_api_key()
    owner = (owner or "").strip()
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