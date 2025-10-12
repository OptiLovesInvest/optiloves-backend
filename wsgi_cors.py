from cors_mw import allow_cors
from wsgi import app as _app
try:
    app = allow_cors(_app)
except Exception:
    # also try 'application' if your wsgi exposes that
    from wsgi import application as _application  # type: ignore
    app = allow_cors(_application)
