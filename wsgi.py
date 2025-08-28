# Minimal, robust WSGI entry for Gunicorn
# Prefer importing from app.py; fall back to entry.py if needed.
try:
    from app import app as app
except Exception:
    from entry import app as app
