from app import app

# === OPTILOVES: BUY QUICK STUB (register) ===
try:
    from flask import request, redirect
    # if decorator not hit, ensure rule exists anyway:
    import uuid
    def _buy_quick():
        oid = uuid.uuid4().hex
        # params accepted but ignored in stub
        _ = request.args.get("property_id","kin-001"); _ = request.args.get("quantity","1"); _ = request.args.get("owner","")
        return redirect(f"https://optilovesinvest.com/thank-you?oid={oid}", code=302)
    app.add_url_rule("/buy/quick", "buy_quick", _buy_quick, methods=["GET"])
except Exception as _e:
    pass
# === /OPTILOVES: BUY QUICK STUB ===

