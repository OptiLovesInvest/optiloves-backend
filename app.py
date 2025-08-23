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
# --- BEGIN: wrap /properties to add UI fields ---
try:
    import json
    from functools import wraps
    from flask import jsonify

    def _wrap_properties_payload(fn):
        @wraps(fn)
        def inner(*args, **kwargs):
            rv = fn(*args, **kwargs)

            # Unpack common return types
            status = headers = None
            data = rv
            if isinstance(rv, tuple):
                data = rv[0]
                status = rv[1] if len(rv) > 1 else None
                headers = rv[2] if len(rv) > 2 else None

            # If it's a Flask Response, modify its JSON body
            if hasattr(data, "get_data"):
                try:
                    raw = data.get_data(as_text=True)
                    payload = json.loads(raw)
                    if isinstance(payload, list):
                        out = []
                        for item in payload:
                            if isinstance(item, dict):
                                out.append({
                                    "id": item.get("id"),
                                    "title": item.get("title"),
                                    "price": item.get("price", 50),
                                    "availableTokens": item.get("availableTokens", item.get("available_tokens", 3000)),
                                })
                            else:
                                out.append(item)
                        data.set_data(json.dumps(out))
                        data.headers["Content-Type"] = "application/json"
                        return data
                except Exception:
                    pass

            # If it's a plain Python list, jsonify with defaults
            try:
                if isinstance(data, list):
                    out = []
                    for item in data:
                        if isinstance(item, dict):
                            out.append({
                                "id": item.get("id"),
                                "title": item.get("title"),
                                "price": item.get("price", 50),
                                "availableTokens": item.get("availableTokens", item.get("available_tokens", 3000)),
                            })
                        else:
                            out.append(item)
                    if headers:
                        return jsonify(out), status or 200, headers
                    return jsonify(out), status or 200
            except Exception:
                pass

            return rv
        return inner

    # Find and wrap the existing /properties endpoint
    for rule in list(app.url_map.iter_rules()):
        if rule.rule == "/properties":
            ep = rule.endpoint
            app.view_functions[ep] = _wrap_properties_payload(app.view_functions[ep])
            break
except Exception:
    pass
# --- END: wrap /properties to add UI fields ---
# --- BEGIN: WSGI middleware to enrich /properties for UI ---
try:
    import json

    class _PropertiesNormalizerMiddleware:
        def __init__(self, app):
            self.app = app

        def __call__(self, environ, start_response):
            path = environ.get("PATH_INFO", "")
            captured = {}

            def _sr(status, headers, exc_info=None):
                captured["status"] = status
                captured["headers"] = headers
                return lambda x: None  # rarely used write()

            result = self.app(environ, _sr)
            try:
                body = b"".join(result)
            finally:
                # close generator if needed
                try:
                    result.close()
                except Exception:
                    pass

            try:
                if path == "/properties" and any(h[0].lower()=="content-type" and "application/json" in h[1] for h in captured.get("headers", [])):
                    data = json.loads(body.decode("utf-8"))
                    if isinstance(data, list):
                        out = []
                        for item in data:
                            if isinstance(item, dict):
                                out.append({
                                    "id": item.get("id"),
                                    "title": item.get("title"),
                                    "price": item.get("price", 50),
                                    "availableTokens": item.get("availableTokens", item.get("available_tokens", 3000)),
                                })
                            else:
                                out.append(item)
                        body = json.dumps(out).encode("utf-8")
                        # update headers (content-length + content-type)
                        headers = [(k, v) for (k, v) in captured["headers"] if k.lower() != "content-length"]
                        # ensure content-type stays json
                        if not any(k.lower()=="content-type" for k,_ in headers):
                            headers.append(("Content-Type","application/json"))
                        headers.append(("Content-Length", str(len(body))))
                        captured["headers"] = headers
            except Exception:
                pass

            start_response(captured["status"], captured["headers"])
            return [body]

    # Attach middleware (chain-friendly)
    app.wsgi_app = _PropertiesNormalizerMiddleware(app.wsgi_app)
except Exception:
    pass
# --- END: WSGI middleware to enrich /properties for UI ---
# --- BEGIN: robust /properties normalizer ---
try:
    import json
    from flask import request

    @app.after_request
    def _ui_properties_patch(resp):
        try:
            # Normalize both "/properties" and "/properties/"
            if request.path.rstrip("/") == "/properties":
                txt = resp.get_data(as_text=True)
                data = json.loads(txt)
                if isinstance(data, list):
                    out = []
                    for item in data:
                        if isinstance(item, dict):
                            out.append({
                                "id": item.get("id"),
                                "title": item.get("title"),
                                "price": item.get("price", 50),
                                "availableTokens": item.get("availableTokens", item.get("available_tokens", 3000)),
                            })
                        else:
                            out.append(item)
                    resp.set_data(json.dumps(out))
                    resp.headers["Content-Type"] = "application/json"
                    resp.headers["X-Props-Normalized"] = "1"
        except Exception:
            # don't break the response if anything goes wrong
            pass
        return resp
except Exception:
    pass
# --- END: robust /properties normalizer ---
# --- BEGIN: properties-ui endpoint (simple, UI-ready) ---
try:
    from flask import jsonify

    @app.get("/properties-ui")
    def properties_ui():
        # Minimal, stable payload the frontend expects
        return jsonify([
            {"id":"kin-001","title":"Kinshasa — Gombe Apartments","price":50,"availableTokens":4997},
            {"id":"lua-001","title":"Luanda — Ilha Offices","price":50,"availableTokens":3000}
        ])
except Exception:
    pass
# --- END: properties-ui endpoint ---
# --- FORCE REGISTER: ping + properties-ui ---
try:
    from flask import jsonify

    # simple health
    def __ping_ui():
        return "ok-ui", 200, {"Content-Type":"text/plain"}
    try:
        # add only if missing
        if "/ping-ui" not in [r.rule for r in app.url_map.iter_rules()]:
            app.add_url_rule("/ping-ui", endpoint="ping_ui", view_func=__ping_ui, methods=["GET"])
    except Exception:
        pass

    # ui-ready properties
    def __properties_ui_fixed():
        return jsonify([
            {"id":"kin-001","title":"Kinshasa — Gombe Apartments","price":50,"availableTokens":4997},
            {"id":"lua-001","title":"Luanda — Ilha Offices","price":50,"availableTokens":3000}
        ])

    try:
        rules = [r.rule for r in app.url_map.iter_rules()]
        if "/properties-ui" not in rules:
            app.add_url_rule("/properties-ui", endpoint="properties_ui", view_func=__properties_ui_fixed, methods=["GET"])
    except Exception:
        pass
except Exception:
    pass
# --- END FORCE REGISTER ---
