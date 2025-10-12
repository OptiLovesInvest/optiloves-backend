from app import app  # expose for gunicorn: wsgi:app
from cors_mw import allow_cors
try:
    app
    app = allow_cors(app)
except NameError:
    pass
from cors_mw import allow_cors
try:
    application  # gunicorn may use this name
    application = allow_cors(application)
except NameError:
    pass
try:
    app
    app = allow_cors(app)
except NameError:
    pass
