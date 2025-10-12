from app import app  # expose for gunicorn: wsgi:app
from cors_mw import allow_cors
try:
    app
    app = allow_cors(app)
except NameError:
    pass
