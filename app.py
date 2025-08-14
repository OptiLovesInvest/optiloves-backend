# app.py — cleaned up with locked-down CORS at the very top

import os
import json
from uuid import uuid4
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

# ---- App + CORS (keep ONLY this app = Flask(...) in the file) ----------------
app = Flask(__name__)
origins = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]
CORS(app, resources={r"/*": {"origins": origins}})

# ---- Simple in-memory price/state --------------------------------------------
STATE = {
    "token_price": 50,       # USD per token
    "available_tokens": 4999 # global demo pool (used by /buy)
}

# ---- Files for demo persistence ----------------------------------------------
PROPS_FILE  = "properties.json"
ORDERS_FILE = "orders.json"

# Default properties (used if properties.json doesn't exist yet)
default_props = [
    {"id": "kin-001", "title": "Kinshasa — Gombe Apartments", "price": 120000, "availableTokens": 5000},
    {"id": "lua-001", "title": "Luanda — Ilha Offices",       "price": 250000, "availableTokens": 3000},
]

# Load / init properties
if os.path.exists(PROPS_FILE):
    with open(PROPS_FILE, "r", encoding="utf-8") as f:
        properties = json.load(f)
else:
    properties = default_props
    with open(PROPS_FILE, "w", encoding="utf-8") as f:
        json.dump(properties, f)

# Load / init orders
if os.path.exists(ORDERS_FILE):
    with open(ORDERS_FILE, "r", encoding="utf-8") as f:
        orders = json.load(f)
else:
    orders = []

# ---- Health ------------------------------------------------------------------
@app.get("/health")
def health():
    return {"ok": True, "service": "backend", "version": "0.1.0"}

# ---- Price + demo buy/airdrop ------------------------------------------------
@app.get("/price")
def get_price():
    # Return both keys for compatibility with different frontends
    return {
        "price": STATE["token_price"],
        "token_price": STATE["token_price"],
        "available_tokens": STATE["available_tokens"]
    }

@app.post("/buy")
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

# ---- Properties --------------------------------------------------------------
@app.get("/properties")
def list_properties():
    return jsonify(properties)

@app.get("/properties/<property_id>")
def get_property_by_id(property_id):
    p = next((p for p in properties if p["id"] == property_id), None)
    if not p:
        return {"error": "Not found"}, 404
    return jsonify(p)

# (Optional convenience if some frontends call /property/:id)
@app.get("/property/<property_id>")
def get_property_by_id_alias(property_id):
    return get_property_by_id(property_id)

# ---- Orders (property-aware purchase that updates inventory) -----------------
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

    total = (prop.get("price") or 0) * qty
    order = {"id": pid, "quantity": qty, "total": total, "ts": datetime.utcnow().isoformat() + "Z"}
    orders.append(order)

    # persist orders + updated inventory
    prop["availableTokens"] = available - qty
    with open(ORDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(orders, f)
    with open(PROPS_FILE, "w", encoding="utf-8") as f:
        json.dump(properties, f)

    return order, 201

# Quick reset of order list (for local testing)
@app.post("/orders/clear")
def clear_orders():
    global orders
    orders = []
    if os.path.exists(ORDERS_FILE):
        os.remove(ORDERS_FILE)
    return {"ok": True}

# ---- Local dev entrypoint ----------------------------------------------------
if __name__ == "__main__":
    # For local testing; in production use gunicorn per Procfile
    app.run(host="0.0.0.0", port=5000, debug=True)
