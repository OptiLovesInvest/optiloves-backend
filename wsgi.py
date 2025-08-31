from app import app as flask_app  # Flask instance

_ALLOWED = {"https://optilovesinvest.com","https://www.optilovesinvest.com"}

def _opti_edge(app):
    def _wrapped(environ, start_response):
        origin = environ.get("HTTP_ORIGIN")
        is_options = environ.get("REQUEST_METHOD") == "OPTIONS"

        def _sr(status, headers, exc_info=None):
            # Always set CSP; tighten as needed
            headers.append((
                "Content-Security-Policy",
                "default-src 'none'; connect-src 'self' https://optilovesinvest.com https://www.optilovesinvest.com; "
                "img-src 'self' data: https:; script-src 'self'; style-src 'self'; font-src 'self' data:; "
                "frame-ancestors 'none'; base-uri 'none'; form-action 'none'; object-src 'none'"
            ))
            # Strict CORS for our two origins only
            if origin in _ALLOWED:
                headers.extend([
                    ("Access-Control-Allow-Origin", origin),
                    ("Vary", "Origin"),
                    ("Access-Control-Allow-Methods", "GET,POST,OPTIONS"),
                    ("Access-Control-Allow-Headers", "Content-Type,Authorization,ComplyCube-Signature"),
                    ("Access-Control-Max-Age", "600"),
                ])
            return start_response(status, headers, exc_info)

        # Short-circuit preflight to 204 with headers
        if is_options:
            hdrs = []
            _sr("204 No Content", hdrs)
            return [b""]

        return app(environ, _sr)
    return _wrapped

# Gunicorn entrypoint
app = _opti_edge(flask_app)