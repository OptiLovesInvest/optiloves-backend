 from flask import Flask
from flask_cors import CORS
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["https://optilovesinvest.com","https://www.optilovesinvest.com","http://localhost:3000"], "methods": ["GET","POST","OPTIONS"], "allow_headers": ["Content-Type","Authorization"]}})
# Enable CORS for your production domains + localhost
# Example route
@app.route("/properties", methods=["GET"])
def get_properties():
    data = [
        {"id": "kin-001", "title": "Kinshasa — Gombe Apartments"},
        {"id": "lua-001", "title": "Luanda — Ilha Offices"}
    ]
    return jsonify(data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)



 + "from flask_cors import CORS`r`n" app = Flask(__name__)
# Enable CORS for your production domains + localhost
# Example route
@app.route("/properties", methods=["GET"])
def get_properties():
    data = [
        {"id": "kin-001", "title": "Kinshasa — Gombe Apartments"},
        {"id": "lua-001", "title": "Luanda — Ilha Offices"}
    ]
    return jsonify(data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)





# --- BEGIN: normalize /properties payload for UI ---
try:
    import json
    from flask import request
    @app.after_request
    def _normalize_properties_payload(resp):
        try:
            if request.path == "/properties" and resp.content_type and "application/json" in resp.content_type:
                data = json.loads(resp.get_data(as_text=True))
                if isinstance(data, list):
                    out = []
                    for item in data:
                        if isinstance(item, dict):
                            out.append({
                                "id": item.get("id"),
                                "title": item.get("title"),
                                "price": item.get("price", 50),
                                "availableTokens": item.get("availableTokens", item.get("available_tokens", 3000))
                            })
                        else:
                            out.append(item)
                    resp.set_data(json.dumps(out))
        except Exception:
            pass
        return resp
except Exception:
    pass
# --- END: normalize /properties payload for UI ---
