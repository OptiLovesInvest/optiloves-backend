# entry.py — single source of truth for Gunicorn
# Tries to import your Flask app object no matter its name/location,
# then ensures the KYC blueprint is registered, plus a health check.

try:
    import app as m
except Exception as e:
    raise RuntimeError("Cannot import app module") from e

# Support app named either `app` or `application`
app = getattr(m, "app", None) or getattr(m, "application", None)
if app is None:
    raise RuntimeError("No Flask app object found in app module")

from app_kyc import kyc
if "kyc" not in app.blueprints:
    app.register_blueprint(kyc, url_prefix="/api/kyc")

@app.get("/_health")
def _health():
    return {"ok": True, "service": "backend"}