from app import app as application
app = application


# === OPTI GLOBAL PREFLIGHT (WSGI-level) ===
ALLOWED_ORIGINS = {"https://optilovesinvest.com", "https://www.optilovesinvest.com"}

class OptiPreflightMiddleware:
    def __init__(self, app):
        self.app = app
    def __call__(self, environ, start_response):
        if environ.get("REQUEST_METHOD") == "OPTIONS":
            origin = environ.get("HTTP_ORIGIN", "")
            headers = [
                ("Vary", "Origin"),
                ("Access-Control-Allow-Methods", "GET,POST,OPTIONS"),
                ("Access-Control-Allow-Headers", "x-api-key, content-type"),
                ("Content-Length", "0"),
            ]
            if origin in ALLOWED_ORIGINS:
                headers.append(("Access-Control-Allow-Origin", origin))
            start_response("204 No Content", headers)
            return [b""]
        return self.app(environ, start_response)
# === END OPTI GLOBAL PREFLIGHT ===


app = OptiPreflightMiddleware(app)


# === OPTI WSGI BUY INTENT (public) ===
import json

class OptiBuyIntentWSGI:
    def __init__(self, app):
        self.app = app
    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO","")
        method = environ.get("REQUEST_METHOD","GET")
        if path == "/buy/intent":
            # Defensive preflight (global preflight also handles)
            if method == "OPTIONS":
                headers = [
                    ("Vary","Origin"),
                    ("Access-Control-Allow-Methods","GET,POST,OPTIONS"),
                    ("Access-Control-Allow-Headers","x-api-key, content-type"),
                    ("Content-Length","0"),
                ]
                # echo origin if present and allowed (middleware may add too)
                origin = environ.get("HTTP_ORIGIN","")
                if origin:
                    headers.append(("Access-Control-Allow-Origin", origin))
                start_response("204 No Content", headers)
                return [b""]
            try:
                size = int(environ.get("CONTENT_LENGTH") or 0)
            except:
                size = 0
            body = environ["wsgi.input"].read(size) if size>0 else b""
            try:
                data = json.loads((body or b"{}").decode("utf-8"))
            except:
                data = {}
            prop  = (data.get("property_id") or "").strip()
            owner = (data.get("owner") or "").strip()
            try:
                qty = int(data.get("quantity") or 0)
            except:
                qty = 0
            missing = [k for k,v in [("property_id",prop),("quantity",qty),("owner",owner)] if not v]
            if missing or qty<=0:
                out = json.dumps({"ok": False, "error": "bad_request", "missing": missing}).encode("utf-8")
                start_response("400 Bad Request", [("Content-Type","application/json"),("Content-Length",str(len(out)))])
                return [out]
            unit_price_usd = 1.50
            amount_usd = round(unit_price_usd*qty, 2)
            out = json.dumps({"ok": True, "intent": {
                "property_id": prop, "quantity": qty, "owner": owner,
                "unit_price_usd": unit_price_usd, "amount_usd": amount_usd, "currency": "USD"
            }}).encode("utf-8")
            start_response("200 OK", [("Content-Type","application/json"),("Content-Length",str(len(out)))])
            return [out]
        return self.app(environ, start_response)
# === END OPTI WSGI BUY INTENT ===
app = OptiBuyIntentWSGI(app)
