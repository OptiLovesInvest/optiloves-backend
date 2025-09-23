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

