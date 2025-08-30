# Minimal WSGI entrypoint with strict CORS + CSP
from app import app as flask_app  # your Flask app instance

def _opti_cors_csp(app):
    allowed = {"https://optilovesinvest.com", "https://www.optilovesinvest.com"}
    def _wrapped(environ, start_response):
        origin = environ.get("HTTP_ORIGIN")
        # Handle CORS preflight quickly
        if environ.get("REQUEST_METHOD") == "OPTIONS":
            hdr = []
            if origin in allowed:
                hdr += [
                    ("Access-Control-Allow-Origin", origin),
                    ("Vary", "Origin"),
                    ("Access-Control-Allow-Methods", "GET,POST,OPTIONS"),
                    ("Access-Control-Allow-Headers", "Content-Type,Authorization,ComplyCube-Signature"),
                    ("Access-Control-Max-Age", "600"),
                ]
            start_response("204 No Content", hdr + [("Content-Length","0")])
            return [b""]

        def _sr(status, headers, exc_info=None):
            if origin in allowed:
                headers += [
                    ("Access-Control-Allow-Origin", origin),
                    ("Vary", "Origin"),
                    ("Access-Control-Allow-Methods", "GET,POST,OPTIONS"),
                    ("Access-Control-Allow-Headers", "Content-Type,Authorization,ComplyCube-Signature"),
                    ("Access-Control-Max-Age", "600"),
                ]
            # Always set CSP
            headers.append((
                "Content-Security-Policy",
                "default-src 'none'; connect-src 'self' https://optilovesinvest.com https://www.optilovesinvest.com; img-src 'self' data: https:; script-src 'self'; style-src 'self'; font-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'none'; object-src 'none'"
            ))
            return start_response(status, headers, exc_info)
        return app(environ, _sr)
    return _wrapped

# Gunicorn expects `app` symbol
app = _opti_cors_csp(flask_app)