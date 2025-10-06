from flask import Flask, request, jsonify, make_response, redirect
from uuid import uuid4

app = Flask(__name__)

@app.route("/_health", methods=["GET"])
def _health():
    return jsonify(ok=True), 200

@app.before_request
def _handle_options():
    if request.method == "OPTIONS":
        return make_response("", 204)

@app.after_request
def _cors(resp):
    origin = request.headers.get("Origin", "")
    allowed = {"https://optilovesinvest.com", "https://www.optilovesinvest.com", "http://localhost:3000"}
    if origin in allowed:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Vary"] = "Origin"
        resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "content-type,x-api-key"
    return resp

@app.route("/_routes", methods=["GET"])
def _routes():
    routes = sorted([str(r) for r in app.url_map.iter_rules()])
    return jsonify(ok=True, routes=routes), 200

@app.route("/buy/quick", methods=["GET","POST"])
def buy_quick():
    try:
        pid = (request.values.get("property_id") or request.values.get("property") or "kin-001").strip()
        qty = int((request.values.get("quantity") or request.values.get("qty") or 1))
    except Exception:
        pid, qty = "kin-001", 1
    oid = str(uuid4())
    url = f"https://optilovesinvest.com/thank-you?oid={oid}&property_id={pid}&quantity={qty}"
    return redirect(url, code=302)
