from flask import Blueprint, request, jsonify
import os, hmac, hashlib

kyc = Blueprint("kyc", __name__)
WH_SECRET = os.getenv("KYC_WEBHOOK_SECRET","")

@kyc.get("/ping")
def ping():
    return jsonify({"ok": True, "service": "kyc"})

@kyc.post("/webhook")
def webhook():
    raw = request.get_data()
    sig = request.headers.get("ComplyCube-Signature") or request.headers.get("complycube-signature")
    if not sig:
        return jsonify({"ok": False, "error": "no signature"}), 400

    digest = hmac.new(WH_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, digest):
        return jsonify({"ok": False, "error": "bad signature"}), 401

    data    = request.get_json(silent=True) or {}
    payload = data.get("payload") or {}
    client  = payload.get("client") or data.get("client") or {}
    meta    = client.get("metadata") or {}
    wallet  = meta.get("wallet")
    outcome = (payload.get("outcome") or data.get("outcome") or "").lower()
    status  = "approved" if outcome in ("clear","approved","passed","pass") else "review"

    print("KYC EVENT:", {"wallet": wallet, "outcome": outcome, "status": status})
    return jsonify({"ok": True})