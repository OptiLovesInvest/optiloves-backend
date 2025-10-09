from flask import Flask, make_response

app = Flask(__name__)

@app.route("/_health")
def _health():
    # keep the existing health output format
    return make_response("  ok\n  --\nTrue\n\n", 200)

@app.route("/")
def index():
    # minimal root
    return make_response("", 204)
