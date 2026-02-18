from flask import Flask, make_response
app = Flask(__name__)

@app.route("/_health")
def _health():
    return make_response("  ok\n  --\nTrue\n\n", 200)

@app.route("/")
def index():
    return make_response("", 204)
# --- OPTI: begin minimal diagnostics (safe, reversible) ---
import os, json
from flask import request, jsonify, abort

def _opti_require_api_key():
    expected = os.environ.get("OPTI_API_KEY","").strip()
    got = request.headers.get("x-api-key","").strip()
    if not expected or got != expected:
        abort(404)

@app.route("/api/ping", methods=["GET"])
def opti_ping():
    _opti_require_api_key()
    return jsonify(ok=True, service="optiloves-backend", ts=int(__import__("time").time()*1000))

@app.route("/api/portfolio", methods=["GET"])
def opti_portfolio_qs():
    _opti_require_api_key()
    owner = request.args.get("owner","").strip()
    if not owner: return jsonify(ok=False, error="missing owner"), 400
    # If your real handler exists, call it here instead:
    # return real_portfolio_handler(owner)
    return jsonify(ok=True, owner=owner, items=[])

@app.route("/api/portfolio/<owner>", methods=["GET"])
def opti_portfolio_path(owner):
    _opti_require_api_key()
    owner = (owner or "").strip()
    if not owner: return jsonify(ok=False, error="missing owner"), 400
    return jsonify(ok=True, owner=owner, items=[])
# --- OPTI: end minimal diagnostics ---

# --- BUY CHECKOUT (temporary stub to unblock investor flow) ---
# Frontend expects: GET /buy/checkout?qty=1  ->  { ok:true, url:"https://optilovesinvest.com/thank-you" }
from flask import request, jsonify
import os

@app.get("/buy/checkout")
def buy_checkout():
    # Optional API key check (only enforced if OPTILOVES_API_KEY is set)
    expected = os.getenv("OPTILOVES_API_KEY")
    if expected:
        got = request.headers.get("x-api-key", "")
        if got != expected:
            return jsonify(ok=False, error="unauthorized"), 401

    raw_qty = request.args.get("qty", "1")
    try:
        qty = int(raw_qty)
    except Exception:
        qty = 1
    if qty < 1:
        qty = 1
    if qty > 100:
        qty = 100

    return jsonify(ok=True, url="https://optilovesinvest.com/thank-you", qty=qty)
# --- END BUY CHECKOUT ---
