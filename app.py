from flask import Flask, jsonify, request
from flask_cors import CORS
from uuid import uuid4
import json, os
from datetime import datetime

app = Flask(__name__)
CORS(app)  # allow all origins for MVP

# ---- Simple config/state (token price in USD)
STATE = {"price": 50}

# ---- Data files (persist across restarts on your machine)
DATA_DIR = os.path.dirname(__file__)
PROPS_FILE  = os.path.join(DATA_DIR, "properties.json")
ORDERS_FILE = os.path.join(DATA_DIR, "orders.json")

# ---- Load or init properties (use snake_case 'available_tokens' to match UI)
default_props = [
    {"id": "kin-001", "title": "Kinshasa — Gombe Apartments", "available_tokens": 5000},
    {"id": "lua-001", "title": "Luanda — Ilha Offices",       "available_tokens": 3000},
]
if os.path.exists(PROPS_FILE):
    with open(PROPS_FILE, "r", encoding="utf-8") as f:
        properties = json.load(f)
else:
    properties = default_props
    with open(PROPS_FILE, "w", encoding="utf-8") as f:
        json.dump(properties, f)

orders = []
if os.path.exists(ORDERS_FILE):
    with open(ORDERS_FILE, "r", encoding="utf-8") as f:
        try:
            orders = json.load(f)
        except Exception:
            orders = []

# ---- Health check (handy for Railway testing)
@app.get("/health")
def health():
    return jsonify({"ok": True, "service": "backend", "version": "0.1.0"})

# ---- Properties
@app.get("/properties")
def list_properties():
    return jsonify(properties)

@app.get("/property/<property_id>")
def get_property_by_id(property_id):
    p = next((p for p in properties if p["id"] == property_id), None)
    if not p:
        return jsonify({"error": "Not found"}), 404
    return jsonify(p)

# ---- Price (UI expects {"price": 50})
@app.get("/price")
def get_price():
    # property_id is optional; same token price for all in MVP
    _ = request.args.get("property_id")
    return jsonify({"price": STATE["price"]})

# ---- Available tokens helper (UI tries this if not found elsewhere)
@app.get("/available")
def get_available():
    pid = request.args.get("property_id")
    if not pid:
        return jsonify({"error": "property_id required"}), 400
    p = next((p for p in properties if p["id"] == pid), None)
    if not p:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"available": int(p.get("available_tokens", 0))})

# ---- Airdrop (devnet stub)
@app.post("/airdrop")
def airdrop():
    data = request.get_json(force=True) or {}
    wallet = data.get("wallet")
    if not wallet:
        return jsonify({"error": "wallet is required"}), 400
    return jsonify({
        "ok": True,
        "wallet": wallet,
        "network": "devnet",
        "lamports": 1_000_000_000
    })

# ---- Buy tokens (simulated)
@app.post("/buy")
def buy_tokens():
    data = request.get_json(force=True) or {}
    pid    = data.get("property_id")
    wallet = data.get("wallet")
    try:
        qty = int(data.get("quantity") or 0)
    except Exception:
        qty = 0

    if not pid or not wallet or qty <= 0:
        return jsonify({"error": "property_id, wallet, quantity are required"}), 400

    prop = next((p for p in properties if p["id"] == pid), None)
    if not prop:
        return jsonify({"error": "invalid property_id"}), 400

    available = int(prop.get("available_tokens", 0))
    if qty > available:
        return jsonify({"error": "insufficient tokens", "available": available}), 400

    # update inventory
    prop["available_tokens"] = available - qty

    total_usd = qty * STATE["price"]
    receipt = {
        "ok": True,
        "property_id": pid,
        "wallet": wallet,
        "quantity": qty,
        "price": STATE["price"],
        "total_usd": total_usd,
        "tx_signature": f"demo-{uuid4().hex[:16]}",
        "ts": datetime.utcnow().isoformat() + "Z"
    }

    # persist orders + properties
    orders.append(receipt)
    with open(ORDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(orders, f)
    with open(PROPS_FILE, "w", encoding="utf-8") as f:
        json.dump(properties, f)

    return jsonify(receipt)

# ---- Quick reset for testing
@app.post("/orders/clear")
def clear_orders():
    global orders
    orders = []
    if os.path.exists(ORDERS_FILE):
        os.remove(ORDERS_FILE)
    return jsonify({"ok": True})

if __name__ == "__main__":
    # Local dev
    app.run(host="127.0.0.1", port=5000, debug=True)
