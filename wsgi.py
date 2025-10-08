# === Optiloves WSGI entry ===
from app import app  # import the Flask app object that /_health uses

# Explicit /buy/quick route (no decorators elsewhere required)
from flask import request, redirect
import uuid

@app.route("/buy/quick", methods=["GET"])
def buy_quick():
    # accept params but ignore for stub
    _ = request.args.get("property_id","kin-001"); _ = request.args.get("quantity","1"); _ = request.args.get("owner","")
    oid = uuid.uuid4().hex
    return redirect(f"https://optilovesinvest.com/thank-you?oid={oid}", code=302)
