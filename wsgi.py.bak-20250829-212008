from flask import Flask, jsonify
from routes.admin_sql import bp as admin_sql_bp

app = Flask(__name__)
app.register_blueprint(admin_sql_bp)

@app.get("/ping")
def ping():
    return jsonify({"ok": True})