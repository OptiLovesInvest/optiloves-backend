import os, hmac
from app import app as flask_app

class ApiKeyGate(object):
    def __init__(self, app):
        self.app = app
    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "") or ""
        def _start_response(status, headers, exc_info=None):
            headers = list(headers) + [("X-Opti-Gate","wsgi")]
            return start_response(status, headers, exc_info)
        if path.startswith("/api/"):
            supplied = environ.get("HTTP_X_API_KEY", "")
            expected = os.environ.get("OPTI_API_KEY", "")
            if not expected or not hmac.compare_digest(supplied, expected):
                _start_response("403 FORBIDDEN", [("Content-Type","application/json")])
                return [b"{\"error\":\"forbidden\"}"]
        return self.app(environ, _start_response)

app = ApiKeyGate(flask_app)
