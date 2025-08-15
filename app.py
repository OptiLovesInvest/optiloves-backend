# app.py
import os
import time
import uuid
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# ---------- Optional Sentry (set SENTRY_DSN in env to enable) ----------
try:
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration
    SENTRY_DSN = os.environ.get("SENTRY_DSN", "").strip()
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN, integrations=[FlaskIntegration()])
except Exception:
    # Sentry is optional; ignore if not configured
    pass

app = Flask(__name__)
CORS(app)

# ---------- Rate limiting ----------
# Note: default storage is in-memory (okay for MVP). For production, configure a shared store.
limiter = Limiter(get_remote_address, app=app, default_limits=["200 per hour"])

# ---------- In-memory demo catalog (resets on deploy) ----------
PROPERTIES = [
    {"id": "kin-001", "title": "Kinshasa — Gombe Apartments", "price": 120000, "availableTokens": 4995},
    {"id": "lua-001", "title": "Luanda — Ilha Offices",       "price": 250000, "availableTokens": 2999},
]

def find_property(pid: str):
    for p in PROPERTIES:
        if p["id"] == pid:
            return p
    return None

# ---------- Supabase setup (supports legacy service_role AND new sb_secret_* keys) ----------
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "").strip()
# auto|rest|sdk — use "rest" to force REST (recommended while stabilizing keys)
SUPABASE_MODE = os.environ.get("SUPABASE_MODE", "auto").lower()

sb = None

def _use_sdk_with_key(key: str) -> bool:
    """SDK works reliably with legacy JWT-like keys (contain dots, and not starting with sb_)."""
    return "." in key and not key.startswith("sb_")

if SUPABASE_URL and SUPABASE_SERVICE_KEY and SUPABASE_MODE != "rest" and _use_sdk_with_key(SUPABASE_SERVICE_KEY):
    try:
        from supabase import create_client, Client  # type: ignore
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        print("Supabase SDK enabled")
    except Exception as e:
        print("Supabase SDK init failed, falling back to REST:", e)
        sb = None
else:
    print("Supabase SDK disabled (using REST)")

def insert_order_row(row: dict):
    """
    Insert into public.orders using SDK if available; otherwise via REST.
    REST works with both legacy service_role and new sb_secret_* keys.
    """
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

# ---------- Routes ----------
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
        "logged": logged,  # useful signal for debugging
    })

if __name__ == "__main__":
    # Render sets PORT; default to 5000 locally
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
