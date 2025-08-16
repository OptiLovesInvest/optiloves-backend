# app.py
import os
import time
import uuid
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# ---------- Optional Sentry ----------
try:
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration
    SENTRY_DSN = os.environ.get("SENTRY_DSN", "").strip()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN, integrations=[FlaskIntegration()])
except Exception:
    pass

app = Flask(__name__)
CORS(app)

# ---------- Rate limiting ----------
limiter = Limiter(get_remote_address, app=app, default_limits=["200 per hour"])

# ---------- In-memory demo catalog ----------
PROPERTIES = [
    {"id": "kin-001", "title": "Kinshasa — Gombe Apartments", "price": 120000, "availableTokens": 4995},
    {"id": "lua-001", "title": "Luanda — Ilha Offices",       "price": 250000, "availableTokens": 2999},
]
def find_property(pid: str):
    for p in PROPERTIES:
        if p["id"] == pid:
            return p
    return None

# ---------- Supabase (SDK or REST fallback) ----------
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "").strip()
SUPABASE_MODE = os.environ.get("SUPABASE_MODE", "auto").lower()

sb = None
def _use_sdk_with_key(key: str) -> bool:
    return "." in key and not key.startswith("sb_")

if SUPABASE_URL and SUPABASE_SERVICE_KEY and SUPABASE_MODE != "rest" and _use_sdk_with_key(SUPABASE_SERVICE_KEY):
    try:
        from supabase import create_client  # type: ignore
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        print("Supabase SDK enabled")
    except Exception as e:
        print("Supabase SDK init failed, falling back to REST:", e)
        sb = None
else:
    print("Supabase SDK disabled (using REST)")

def insert_order_row(row: dict):
    """Insert into public.orders; use SDK if available, else REST (works with sb_secret_*)."""
    if sb:
        return sb.table("orders").insert(row).execute()

    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise RuntimeError("Supabase config missing")

    url = f"{SUPABASE_URL}/rest/v1/orders"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    r = requests.post(url, headers=headers, json=row, timeout=10)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"REST insert failed: {r.status_code} {r.text}")
    return r.json()

# ---------- Stripe ----------
import stripe
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "").strip()
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "https://app.optilovesinvest.com").rstrip("/")

# Safety: small test charge so you don’t accidentally set huge ticket sizes during tests.
# Feel free to set TEST_UNIT_AMOUNT_CENTS=None to charge real property price * 100.
TEST_UNIT_AMOUNT_CENTS = 100  # $1.00 in Test mode

@app.post("/checkout")
@limiter.limit("20 per minute")
def checkout():
    """
    Create a Stripe Checkout Session.
    Body: { property_id: string, quantity: int, wallet?: string }
    Returns: { url }
    """
    data = request.get_json(force=True) or {}
    prop_id = str(data.get("property_id") or "").strip()
    wallet  = str(data.get("wallet") or "web").strip()[:128]
    try:
        qty = int(data.get("quantity", 1))
    except Exception:
        qty = 1
    if qty <= 0:
        qty = 1

    p = find_property(prop_id)
    if not p:
        return jsonify({"ok": False, "error": "not_found"}), 404

    # Amount
    if TEST_UNIT_AMOUNT_CENTS is not None:
        unit_cents = int(TEST_UNIT_AMOUNT_CENTS)
    else:
        # Use your real property price (USD) -> cents
        unit_cents = int(p["price"]) * 100

    success_url = f"{FRONTEND_ORIGIN}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url  = f"{FRONTEND_ORIGIN}/property/{prop_id}"

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": p["title"]},
                    "unit_amount": unit_cents,
                },
                "quantity": qty,
            }],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "property_id": prop_id,
                "quantity": str(qty),
                "wallet": wallet,
            },
        )
        return jsonify({"ok": True, "url": session.url})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400

@app.post("/stripe/webhook")
def stripe_webhook():
    """
    Handles: checkout.session.completed
    Inserts a PAID order row and decrements in-memory availability.
    """
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")
    wh_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()

    # Verify signature if we have a secret
    try:
        if wh_secret:
            event = stripe.Webhook.construct_event(payload, sig_header, wh_secret)
        else:
            event = request.get_json(force=True)
    except Exception as e:
        return jsonify({"ok": False, "error": f"sig_error: {e}"}), 400

    if event and event.get("type") == "checkout.session.completed":
        session = event["data"]["object"]
        md = session.get("metadata", {}) or {}
        prop_id = str(md.get("property_id") or "").strip()
        wallet  = str(md.get("wallet") or "stripe").strip()[:128]
        try:
            qty = int(md.get("quantity", "1"))
        except Exception:
            qty = 1

        # Compute prices from Stripe amounts (cents)
        total_usd = int((session.get("amount_total") or 0) // 100)
        unit_price_usd = int(total_usd // max(qty, 1))
        tx_sig = str(session.get("id") or f"stripe-{uuid.uuid4().hex[:16]}")

        # Decrement in-memory stock (best-effort)
        prop = find_property(prop_id)
        if prop:
            prop["availableTokens"] = max(0, int(prop["availableTokens"]) - qty)

        # Insert order
        try:
            insert_order_row({
                "id": tx_sig,
                "property_id": prop_id,
                "wallet": wallet,
                "quantity": qty,
                "unit_price_usd": unit_price_usd,
                "total_usd": total_usd,
                "status": "PAID",
                "ts": int(time.time()),
            })
        except Exception as e:
            # swallow duplicate insert retries, log others
            print("Order logging on webhook failed:", e)

    return jsonify({"ok": True})

# ---------- Existing routes ----------
@app.get("/health")
def health():
    return {"ok": True, "ts": int(time.time())}

@app.get("/properties")
def properties():
    return jsonify(PROPERTIES)

@app.post("/buy")
@limiter.limit("10 per minute")
def buy():
    data = request.get_json(force=True) or {}
    prop_id = str(data.get("property_id") or "").strip()
    wallet  = str(data.get("wallet") or "unknown")[:128]
    try:
        qty = int(data.get("quantity", 0))
    except Exception:
        qty = 0

    p = find_property(prop_id)
    if not p:
        return jsonify({"ok": False, "error": "not_found"}), 404
    if qty <= 0:
        return jsonify({"ok": False, "error": "bad_qty"}), 400
    if qty > int(p["availableTokens"]):
        return jsonify({"ok": False, "error": "insufficient"}), 400

    unit_price = int(p["price"])
    total = unit_price * qty
    p["availableTokens"] = int(p["availableTokens"]) - qty
    tx_sig = f"demo-{uuid.uuid4().hex[:16]}"

    logged = False
    try:
        insert_order_row({
            "id": tx_sig,
            "property_id": prop_id,
            "wallet": wallet,
            "quantity": qty,
            "unit_price_usd": unit_price,
            "total_usd": total,
            "status": "PENDING_PAYMENT",
            "ts": int(time.time()),
        })
        logged = True
    except Exception as e:
        print("Order logging failed:", e)

    return jsonify({
        "ok": True,
        "property_id": prop_id,
        "quantity": qty,
        "price": unit_price,
        "total_usd": total,
        "tx_signature": tx_sig,
        "wallet": wallet,
        "logged": logged,
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
