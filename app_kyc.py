from flask import Blueprint, request, jsonify
import os, hmac, hashlib, json, time

kyc = Blueprint("kyc", __name__)
WH_SECRET = os.getenv("KYC_WEBHOOK_SECRET","")

@kyc.post("/api/kyc/webhook")
def kyc_webhook():
    raw = request.get_data()
    sig = (request.headers.get("ComplyCube-Signature")
           or request.headers.get("complycube-signature")
           or request.headers.get("X-KYC-Signature",""))
    if not sig:
        return jsonify({"ok": False, "error":"no signature"}), 400

    digest = hmac.new(WH_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, digest):
        return jsonify({"ok": False, "error":"bad signature"}), 401

    data = request.json or {}
    # Best-effort extraction (we'll tighten after first real payload)
    wallet = ((data.get("client") or {}).get("metadata") or {}).get("wallet") \
             or (data.get("metadata") or {}).get("wallet")
    outcome = (data.get("outcome")
               or (data.get("result") or {}).get("outcome")
               or (data.get("check") or {}).get("outcome"))

    status = "approved" if str(outcome).lower() in ("clear","approved","passed","pass") else "review"
    print("KYC EVENT:", {"wallet": wallet, "outcome": outcome, "status": status})

    # TODO: Upsert to Supabase: {wallet, kyc_status: status, updated_at: now}
    return jsonify({"ok": True})