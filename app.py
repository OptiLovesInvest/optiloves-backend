from flask import Flask
from flask_cors import CORS
app = Flask(__name__)


import os


origins = os.environ.get("ALLOWED_ORIGINS", "https://optilovesinvest.com,https://www.optilovesinvest.com,http://localhost:3000")


CORS(app, resources={r"/*": {


    "origins": [o.strip() for o in origins.split(",") if o.strip()],


    "methods": ["GET","POST","OPTIONS"],


    "allow_headers": ["Content-Type","Authorization"]


}})


# Enable CORS for your production domains + localhost


# Example route


@app.route("/properties", methods=["GET"])


def get_properties():


    data = [


        {"id": "kin-001", "title": "Kinshasa ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â Gombe Apartments"},


        {"id": "lua-001", "title": "Luanda ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â Ilha Offices"}


    ]


    return jsonify(data)





if __name__ == "__main__":


    app.run(host="0.0.0.0", port=5000, debug=True)


    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)
from flask_cors import CORS
app = Flask(__name__)


# Enable CORS for your production domains + localhost


# Example route


@app.route("/properties", methods=["GET"])


def get_properties():


    data = [


        {"id": "kin-001", "title": "Kinshasa ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â Gombe Apartments"},


        {"id": "lua-001", "title": "Luanda ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â Ilha Offices"}


    ]


    return jsonify(data)





if __name__ == "__main__":


    app.run(host="0.0.0.0", port=5000, debug=True)


    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)





from app_kyc import kyc


app.register_blueprint(kyc, url_prefix='/api/kyc')


# === Optiloves KYC (auto-register) ===
from app_kyc import kyc  # noqa
if "kyc" not in app.blueprints:
    app.register_blueprint(kyc, url_prefix="/api/kyc")

@app.get("/_health")
def _health():
    return {"ok": True, "service": "backend"}
# === end KYC ===
