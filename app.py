# app.py — OptiLoves backend (Flask + CORS + endpoints + AI propose-only via Chat Completions)

import os
import json
from uuid import uuid4
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI

# -----------------------------------------------------------------------------
# App + CORS
# -----------------------------------------------------------------------------
app = Flask(__name__)
origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
CORS(app, resources={r"/*": {"origins": origins}})

# -----------------------------------------------------------------------------
# Simple in-memory state (demo)
# -----------------------------------------------------------------------------
STATE = {
    "token_price": 50,        # USD per token (used by /price)
    "available_tokens": 4999  # global demo pool for /buy (legacy/demo)
}

# -----------------------------------------------------------------------------
# JSON storage for demo persistence
# -----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROPS_FILE  = os.path.join(BASE_DIR, "properties.json")
ORDERS_FILE = os.path.join(BASE_DIR, "orders.json")

default_props = [
    {"id": "kin-001", "title": "Kinshasa — Gombe Apartments", "price": 120000, "availableTokens": 5000},
    {"id": "lua-001", "title": "Luanda — Ilha Offices",       "price": 250000, "availableTokens": 3000},
]

# Load/init properties
if os.path.exists(PROPS_FILE):
    with open(PROPS_FILE, "r", encoding="utf-8") as f:
        properties = json.load(f)
else:
    properties = default_props
    with open(PROPS_FILE, "w", encoding="utf-8") as f:
        json.dump(properties, f)

# Load/init orders
if os.path.exists(ORDERS_FILE):
    with open(ORDERS_FILE, "r", encoding="utf-8") as f:
        orders = json.load(f)
else:
    orders = []

# -----------------------------------------------------------------------------
# Health
# -----------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"ok": True, "service": "backend", "version": "0.1.0"}

# -----------------------------------------------------------------------------
# Price + demo buy/airdrop
# -----------------------------------------------------------------------------
@app.get("/price")
def get_price():
    # Return both "price" and "token_price" for frontend compatibility
    return {
        "price": STATE["token_price"],
        "token_price": STATE["token_price"],
        "available_tokens": STATE["available_tokens"]
    }

@app.post("/buy")  # legacy/demo: uses global STATE pool
def buy_tokens():
    data = request.get_json(force=True) or {}
    prop_id = data.get("property_id")
    wallet = data.get("wallet")
    try:
        qty = int(data.get("quantity") or 0)
    except Exception:
        qty = 0

    if not prop_id or not wallet or qty <= 0:
        return {"error": "property_id, wallet, quantity are required"}, 400

    if qty > STATE["available_tokens"]:
        return {"error": "insufficient tokens", "available": STATE["available_tokens"]}, 400

    STATE["available_tokens"] -= qty
    total_usd = qty * STATE["token_price"]

    return {
        "ok": True,
        "property_id": prop_id,
        "wallet": wallet,
        "quantity": qty,
        "price": STATE["token_price"],
        "total_usd": total_usd,
        "tx_signature": f"demo-{uuid4().hex[:16]}"
    }

@app.post("/airdrop")
def airdrop():
    data = request.get_json(force=True) or {}
    wallet = data.get("wallet")
    if not wallet:
        return {"error": "wallet is required"}, 400
    # Stubbed devnet airdrop response
    return {"ok": True, "wallet": wallet, "network": "devnet", "lamports": 1_000_000_000}

# -----------------------------------------------------------------------------
# Properties
# -----------------------------------------------------------------------------
@app.get("/properties")
def list_properties():
    return jsonify(properties)

@app.get("/properties/<property_id>")
def get_property_by_id(property_id):
    p = next((p for p in properties if p["id"] == property_id), None)
    if not p:
        return {"error": "Not found"}, 404
    return jsonify(p)

# Alias if some clients call singular form
@app.get("/property/<property_id>")
def get_property_by_id_alias(property_id):
    return get_property_by_id(property_id)

# -----------------------------------------------------------------------------
# Orders (property-aware purchases with inventory updates)
# -----------------------------------------------------------------------------
@app.route("/orders", methods=["GET", "POST"])
def orders_route():
    global properties, orders
    if request.method == "GET":
        return jsonify(orders)

    data = request.get_json(force=True) or {}
    pid = data.get("id")
    try:
        qty = max(1, int(data.get("quantity", 1)))
    except Exception:
        qty = 1

    prop = next((p for p in properties if p["id"] == pid), None)
    if not prop:
        return {"error": "Invalid property id"}, 400

    available = int(prop.get("availableTokens", 0))
    if qty > available:
        return {"error": f"Only {available} token(s) available"}, 400

    # For consistency with earlier UI: property price is unit price
    # AFTER (token price — correct for per-token purchases)
    unit_price = STATE["token_price"]

    total = unit_price * qty
    order = {"id": pid, "quantity": qty, "total": total, "ts": datetime.utcnow().isoformat() + "Z"}
    orders.append(order)

    # persist orders + updated inventory
    prop["availableTokens"] = available - qty
    with open(ORDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(orders, f)
    with open(PROPS_FILE, "w", encoding="utf-8") as f:
        json.dump(properties, f)

    return order, 201

@app.post("/orders/clear")
def clear_orders():
    global orders
    orders = []
    if os.path.exists(ORDERS_FILE):
        os.remove(ORDERS_FILE)
    return {"ok": True}

# -----------------------------------------------------------------------------
# AI Agent (propose-only — never auto-buys) using Chat Completions
# -----------------------------------------------------------------------------
def get_openai_client():
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    return OpenAI(api_key=key)

AI_SYSTEM = """You are OptiLoves Assistant.
Reply ONLY with a compact JSON object.
Schema: {"action":"list"|"price"|"propose_buy", "property_id":string?, "quantity":number?}
If the user asks to buy, ALWAYS return action="propose_buy" (never execute purchases).
Examples:
- "What can I buy?" -> {"action":"list"}
- "price for kin-001" -> {"action":"price","property_id":"kin-001"}
- "buy 2 of kin-001" -> {"action":"propose_buy","property_id":"kin-001","quantity":2}
Never add text outside JSON.
"""

@app.get("/__env_ok")
def env_ok():
    # Quick check (does NOT leak the key)
    return {"openai_key_set": bool(os.getenv("OPENAI_API_KEY"))}

def ai_exec(cmd: dict):
    act = (cmd.get("action") or "").lower()
    if act == "list":
        return {"properties": properties}
    if act == "price":
        pid = (cmd.get("property_id") or "").strip()
        found = next((p for p in properties if p["id"] == pid), None)
        return {
            "property_id": pid,
            "token_price": STATE["token_price"],
            "property_found": bool(found),
        }
    if act == "propose_buy":
        pid = (cmd.get("property_id") or "").strip()
        qty = max(1, int(cmd.get("quantity") or 1))
        prop = next((p for p in properties if p["id"] == pid), None)
        if not prop:
            return {"ok": False, "error": "Invalid property id"}
        available = int(prop.get("availableTokens", 0))
        if qty > available:
            return {"ok": False, "error": f"Only {available} token(s) available", "available": available}
        unit_price = prop.get("price") or STATE["token_price"]
        total = unit_price * qty
        return {
            "ok": True,
            "proposal": {
                "property_id": pid,
                "quantity": qty,
                "unit_price": unit_price,
                "total": total,
                "available": available,
                "title": prop.get("title"),
            },
        }
    return {"ok": False, "error": "Unknown action"}

@app.post("/ai/chat")
def ai_chat():
    client = get_openai_client()
    if client is None:
        return {"error": "OPENAI_API_KEY not set on server"}, 500

    data = request.get_json(silent=True) or {}
    user = (data.get("message") or "").strip()
    if not user:
        return {"error": "message is required"}, 400

    # Use Chat Completions (simple + stable) and force JSON output
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": AI_SYSTEM},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content or "{}"
    except Exception as e:
        return {"error": "openai_call_failed", "detail": str(e)}, 502

    try:
        cmd = json.loads(raw)
    except Exception:
        return {"error": "AI did not return valid JSON", "raw": raw}, 502

    return {"command": cmd, "result": ai_exec(cmd)}

# -----------------------------------------------------------------------------
# Local dev entrypoint (Render uses Gunicorn via Procfile)
# -----------------------------------------------------------------------------

# ---- Stripe Checkout (test mode) ----
import stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://example.com")  # set on Render

@app.post("/checkout/create")
def checkout_create():
    data = request.get_json(force=True) or {}
    pid = (data.get("property_id") or "").strip()
    qty = max(1, int(data.get("quantity") or 1))

    prop = next((p for p in properties if p["id"] == pid), None)
    if not prop:
        return {"error": "Invalid property id"}, 400

    available = int(prop.get("availableTokens", 0))
    if qty > available:
        return {"error": f"Only {available} token(s) available"}, 400

    unit_price = STATE["token_price"]          # $ per token
    unit_amount = int(unit_price * 100)        # cents

    if not stripe.api_key:
        return {"error": "Stripe not configured"}, 500
    if not FRONTEND_URL or "http" not in FRONTEND_URL:
        return {"error": "FRONTEND_URL not set"}, 500

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": f"{prop.get('title')} — {pid} (token)"},
                    "unit_amount": unit_amount,
                },
                "quantity": qty,
            }],
            success_url=f"{FRONTEND_URL}/ai?paid=1&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/ai?canceled=1",
            metadata={"property_id": pid, "quantity": str(qty)},
            client_reference_id=pid,
        )
        return {"checkout_url": session.url}
    except Exception as e:
        return {"error": "stripe_create_failed", "detail": str(e)}, 502

WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

@app.post("/stripe/webhook")
def stripe_webhook():
    payload = request.data
    sig = request.headers.get("Stripe-Signature", "")
    if not WEBHOOK_SECRET:
        return {"error": "webhook not configured"}, 500

    try:
        event = stripe.Webhook.construct_event(payload, sig, WEBHOOK_SECRET)
    except Exception as e:
        return {"error": "invalid_signature", "detail": str(e)}, 400

    # Handle successful payment
    if event.get("type") == "checkout.session.completed":
        sess = event["data"]["object"]
        meta = sess.get("metadata") or {}
        pid = (meta.get("property_id") or "").strip()
        qty = int(meta.get("quantity") or "1")

        prop = next((p for p in properties if p["id"] == pid), None)
        if prop:
            available = int(prop.get("availableTokens", 0))
            if qty <= available:
                unit_price = STATE["token_price"]
                total = unit_price * qty
                order = {"id": pid, "quantity": qty, "total": total, "ts": datetime.utcnow().isoformat() + "Z"}
                orders.append(order)
                prop["availableTokens"] = available - qty
                with open(ORDERS_FILE, "w", encoding="utf-8") as f: json.dump(orders, f)
                with open(PROPS_FILE, "w", encoding="utf-8") as f: json.dump(properties, f)

    return {"ok": True}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
