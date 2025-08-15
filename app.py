# backend/app.py
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from supabase import create_client
import os, uuid, time

# (Optional) Sentry monitoring — only used if SENTRY_DSN is set
try:
    import sentry_sdk
    if os.environ.get("SENTRY_DSN"):
        sentry_sdk.init(dsn=os.environ["SENTRY_DSN"], traces_sample_rate=0.2)
except Exception:
    pass  # Sentry is optional

app = Flask(__name__)
CORS(app)

# -------- Rate limiting --------
# Default: 60 requests/min per IP. Route-specific limits can override.
limiter = Limiter(get_remote_address, app=app, default_limits=["60 per minute"])

# -------- Optional Supabase client (orders logging) --------
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY) if SUPABASE_URL and SUPABASE_SERVICE_KEY else None

# -------- In-memory inventory (demo) --------
# Keep the exact field names your frontend consumes:
#   id, title, price, availableTokens
PROPERTIES = [
    {"id": "kin-001", "title": "Kinshasa — Gombe Apartments", "price": 120_000, "availableTokens": 4995},
    {"id": "lua-001", "title": "Luanda — Ilha Offices",        "price": 250_000, "availableTokens": 2999},
]

def find_property(prop_id: str):
    return next((p for p in PROPERTIES if p["id"] == prop_id), None)

# -------- Endpoints --------

@app.get("/health")
def health():
    return jsonify({"ok": True})

@app.get("/properties")
def properties():
    """
    Returns the public catalog with the exact keys used by the frontend:
      [{ id, title, price, availableTokens }]
    """
    out = [
        {
            "id": p["id"],
            "title": p["title"],
            "price": int(p["price"]),
            "availableTokens": int(p["availableTokens"]),
        }
        for p in PROPERTIES
    ]
    return jsonify(out)

@app.get("/price/<prop_id>")
def price(prop_id: str):
    """
    Optional detail endpoint; frontend uses it if available.
    Returns { ok, price, available }
    """
    p = find_property(prop_id)
    if not p:
        return jsonify({"ok": False, "error": "not_found"}), 404
    return jsonify({"ok": True, "price": int(p["price"]), "available": int(p["availableTokens"])})

@app.post("/buy")
@limiter.limit("10 per minute")  # per-IP limiter for purchases
def buy():
    """
    Body: { property_id, quantity, wallet }
    Returns:
      { ok, property_id, quantity, price, total_usd, tx_signature, wallet }
    Also decrements in-memory inventory and (optionally) logs to Supabase.
    """
    try:
        data = request.get_json(force=True) or {}
    except Exception:
        return jsonify({"ok": False, "error": "bad_json"}), 400

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

    # Decrement availability (demo in-memory)
    p["availableTokens"] = int(p["availableTokens"]) - qty

    # Demo tx signature
    tx_sig = f"demo-{uuid.uuid4().hex[:16]}"

    # Best-effort persistence to Supabase (optional)
    if sb:
        try:
            sb.table("orders").insert({
                "id": tx_sig,
                "property_id": prop_id,
                "wallet": wallet,
                "quantity": qty,
                "unit_price_usd": unit_price,
                "total_usd": total,
                "status": "PENDING_PAYMENT",
                "ts": int(time.time()),
            }).execute()
        except Exception as e:
            # Don't fail purchase if logging fails
            print("Supabase insert error:", e)

    return jsonify({
        "ok": True,
        "property_id": prop_id,
        "quantity": qty,
        "price": unit_price,
        "total_usd": total,
        "tx_signature": tx_sig,
        "wallet": wallet,
    })

@app.post("/airdrop")
def airdrop():
    """
    Devnet helper stub; frontend also requests Solana devnet airdrop directly.
    """
    data = request.get_json(force=True) or {}
    wallet = str(data.get("wallet") or "")[:128]
    return jsonify({"ok": True, "requested": "1 SOL (devnet)", "wallet": wallet})

# -------- Entrypoint --------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
