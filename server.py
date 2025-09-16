from flask import Flask, jsonify
from routes.admin_sql import bp as admin_sql_bp

app = Flask(__name__)
app.register_blueprint(admin_sql_bp)

@app.get("/ping")
def ping():
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)# ==== BEGIN PORTFOLIO (stable shim) ====
from flask import request, jsonify

@app app app app app app app app kyc app.get('/portfolio/<owner>')
def _portfolio_owner(owner):
    owner = (owner or '').strip()
    if not owner:
        return jsonify({'owner':'', 'items':[], 'total':0, 'source':'shim'}), 200
    return jsonify({'owner': owner, 'items': [], 'total': 0, 'source': 'shim'}), 200

@app app app app app app app app kyc app.get('/portfolio')
def _portfolio_query():
    owner = request.args.get('owner','').strip()
    if not owner:
        return jsonify({'error':'missing owner'}), 400
    return jsonify({'owner': owner, 'items': [], 'total': 0, 'source': 'shim'}), 200
# ==== END PORTFOLIO (stable shim) ====
# ==== BEGIN PORTFOLIO (stable shim) ====
from flask import request, jsonify

@app app app app app app app app kyc app.get('/portfolio/<owner>')
def _portfolio_owner(owner):
    owner = (owner or '').strip()
    if not owner:
        return jsonify({'owner':'', 'items':[], 'total':0, 'source':'shim'}), 200
    return jsonify({'owner': owner, 'items': [], 'total': 0, 'source': 'shim'}), 200

@app app app app app app app app kyc app.get('/portfolio')
def _portfolio_query():
    owner = request.args.get('owner','').strip()
    if not owner:
        return jsonify({'error':'missing owner'}), 400
    return jsonify({'owner': owner, 'items': [], 'total': 0, 'source': 'shim'}), 200
# ==== END PORTFOLIO (stable shim) ====
