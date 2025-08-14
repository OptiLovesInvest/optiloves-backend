from flask import Flask, request
from flask_cors import CORS
import json, os
from datetime import datetime

app = Flask(__name__)
CORS(app)

PROPERTIES = [
    {"id": "kin-001", "title": "Kinshasa — Gombe Apartments", "price": 120000},
    {"id": "lua-001", "title": "Luanda — Ilha Offices", "price": 250000},
]

ORDERS_FILE = "orders.json"
orders = json.load(open(ORDERS_FILE)) if os.path.exists(ORDERS_FILE) else []

@app.route("/properties")
def list_properties():
    return PROPERTIES

@app.route("/properties/<property_id>")
def get_property_by_id(property_id):
    p = next((p for p in PROPERTIES if p["id"] == property_id), None)
    return (p, 200) if p else ({"error": "Not found"}, 404)

@app.route("/orders", methods=["GET", "POST"])
def orders_route():
    if request.method == "GET":
        return orders
    data = request.get_json(force=True) or {}
    pid = data.get("id")
    qty = int(data.get("quantity", 1))
    prop = next((p for p in PROPERTIES if p["id"] == pid), None)
    if not prop:
        return {"error": "Invalid property id"}, 400
    total = (prop.get("price") or 0) * qty
    order = {"id": pid, "quantity": qty, "total": total, "ts": datetime.utcnow().isoformat() + "Z"}
    orders.append(order)
    with open(ORDERS_FILE, "w") as f:
        json.dump(orders, f)
    return order, 201

if __name__ == "__main__":
    app.run(debug=True)
