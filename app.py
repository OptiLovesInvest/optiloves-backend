import time, uuid, sqlite3, os
from datetime import datetime, timezone
from flask import Flask, request, jsonify, make_response, redirect

ALLOWED_ORIGINS = {"https://optilovesinvest.com", "https://www.optilovesinvest.com"}
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "orders.db")

app = Flask(__name__)

# -- DB bootstrap -------------------------------------------------------------
def _db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY,
        property_id TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        owner TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""")
    return conn

DB = _db()

def create_order(property_id:str, quantity:int, owner:str, status:str="created") -> str:
    oid = str(uuid.uuid4())
    ts = datetime.now(timezone.utc).isoformat()
    DB.execute("INSERT INTO orders(id,property_id,quantity,owner,status,created_at) VALUES(?,?,?,?,?,?)",
               (oid, property_id, quantity, owner, status, ts))
    DB.commit()
    return oid

# -- CORS ---------------------------------------------------------------------
@app.after_request
def _cors(resp):
    origin = request.headers.get("Origin", "")
    if origin in ALLOWED_ORIGINS:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Vary"] = "Origin"
        resp.headers["Access-Control-Allow-Headers"] = "content-type, x-api-key"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp

# -- Health & Ping ------------------------------------------------------------
@app.route("/_health", methods=["GET"])
def health():
    return jsonify(ok=True), 200

@app.route("/api/ping", methods=["GET","HEAD"])
@app.route("/api/ping/", methods=["GET","HEAD"])
def ping():
    return jsonify(ok=True, ts=int(time.time()*1000)), 200

# -- STABLE BUY: works from a static <a href="..."> ---------------------------
# Example: https://optiloves-backend.onrender.com/buy/quick?property_id=kin-001&quantity=1&owner=69C...XF6B
@app.route("/buy/quick", methods=["GET"])
def buy_quick():
    pid = (request.args.get("property_id") or "").strip()
    qty = int(request.args.get("quantity") or 1)
    owner = (request.args.get("owner") or "").strip()
    if not pid or qty < 1 or not owner:
        return jsonify(ok=False, error="missing property_id/quantity/owner"), 400
    oid = create_order(pid, qty, owner)
    # Redirect back to FE thank-you with the order id for reference
    thank_you = f"https://optilovesinvest.com/thank-you?oid={oid}"
    return redirect(thank_you, code=302)

# Existing stubbed checkout (kept)
@app.route("/buy/checkout", methods=["POST","OPTIONS"])
def buy_checkout():
    if request.method == "OPTIONS":
        return make_response("", 204)
    _ = request.get_json(silent=True) or {}
    return jsonify(ok=True, url="https://optilovesinvest.com/thank-you"), 200

# -- Orders API (verification) ------------------------------------------------
@app.route("/api/orders", methods=["GET"])
def list_orders():
    cur = DB.execute("SELECT id,property_id,quantity,owner,status,created_at FROM orders ORDER BY created_at DESC LIMIT 50")
    rows = [dict(zip(["id","property_id","quantity","owner","status","created_at"], r)) for r in cur.fetchall()]
    return jsonify(ok=True, orders=rows), 200

@app.route("/api/orders/<oid>", methods=["GET"])
def get_order(oid):
    cur = DB.execute("SELECT id,property_id,quantity,owner,status,created_at FROM orders WHERE id=?", (oid,))
    r = cur.fetchone()
    if not r: return jsonify(ok=False, error="not found"), 404
    return jsonify(ok=True, order=dict(zip(["id","property_id","quantity","owner","status","created_at"], r))), 200

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=False)
# ---[opti quick-buy]---
from uuid import uuid4
from flask import request, redirect

@app.route("/buy/quick", methods=["GET","POST"])
def buy_quick():
    pid = (request.values.get("property_id") or request.values.get("property") or "kin-001").strip()
    qty = int((request.values.get("quantity") or request.values.get("qty") or 1))
    oid = str(uuid4())
    thank = f"https://optilovesinvest.com/thank-you?oid={oid}&property_id={pid}&quantity={qty}"
    return redirect(thank, code=302)
# ---[/opti quick-buy]---
# ---[OptiLoves permanent quick buy]---
from flask import request, redirect
from uuid import uuid4

@app.route("/buy/quick", methods=["GET","POST"])
def buy_quick():
    try:
        pid = (request.values.get("property_id") or request.values.get("property") or "kin-001").strip()
        qty = int((request.values.get("quantity") or 1))
    except Exception:
        pid, qty = "kin-001", 1
    oid = str(uuid4())
    url = f"https://optilovesinvest.com/thank-you?oid={oid}&property_id={pid}&quantity={qty}"
    return redirect(url, code=302)
# ---[/OptiLoves permanent quick buy]---
