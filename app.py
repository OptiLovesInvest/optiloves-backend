from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)

# Enable CORS for your production domains + localhost
CORS(
    app,
    resources={r"/*": {"origins": [
        "https://optilovesinvest.com",
        "https://www.optilovesinvest.com",
        "https://app.optilovesinvest.com",
        "http://localhost:3000"
    ]}},
    supports_credentials=False,
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "OPTIONS"],
    max_age=86400
)

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
