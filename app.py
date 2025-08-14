# app.py — OptiLoves backend (Flask + CORS + endpoints + AI propose-only via Chat Completions)

import os
import json
from uuid import uuid4
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI

# -----------------------------------------------------------------------------
# App + CORS (keep ONLY this Flask app definition)
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
PROPS_FILE  = "properties.json"
ORDERS_FILE = "orders.json"

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
    unit_price = prop.get("price") or 0
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

AI_SYSTEM = (
    "You are OptiLoves Assistant. "
    "Reply ONLY with a compact JSON object.\n"
    'Schema: {"action":"list"|"price"|"propose_buy", "property_id":string?, "quantity":number?}\n'
    "If the user asks to buy, ALWAYS return action=\"propose_buy\" (never execute purchases).\n"
    'Examples:\n'
    '- \"What can I buy?\" -> {\"action\":\"list\"}\n'
    '- \"price for kin-001\" -> {\"action\":\"price\",\"property_id\":\"kin-001\"}\n'
    '- \"buy 2 of kin-001\" -> {\"action\":\"propose_buy\",\"property_id\":\"kin-001\",\"quantity\":2}\n'
    "Never add text outside JSON."
)

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
   
::contentReference[oaicite:0]{index=0}
