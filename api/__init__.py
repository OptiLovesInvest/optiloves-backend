from flask import Blueprint, request, jsonify, abort
import os

api_bp = Blueprint("opti_api", __name__)

def _key_ok():
    want = (os.environ.get("OPTI_API_KEY") or "").strip()
    got  = (request.headers.get("x-api-key") or "").strip()
    return bool(want) and got == want

@api_bp.get("/ping")
def ping():
    return {"ok": True, "route": "api/ping"}

@api_bp.get("/portfolio/<owner>")
def portfolio(owner: str):
    if not _key_ok():
        abort(404)
    # TODO: replace with real data
    return jsonify({"owner": owner, "items": []})

@api_bp.post("/checkout")
def checkout():
    if not _key_ok():
        abort(404)
    data = request.get_json(silent=True) or {}
    # TODO: integrate real checkout; stub returns thank-you
    return jsonify({"ok": True, "url": "https://optilovesinvest.com/thank-you", "echo": data})