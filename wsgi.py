# Robust WSGI entry for Render/Gunicorn
try:
    from app import app as app
except Exception:
    from entry import app as app  # fallback

# Force-register KYC + health in prod
try:
    from app_kyc import kyc
    if "kyc" not in app.blueprints:
        app.register_blueprint(kyc, url_prefix="/api/kyc")

    @app.get("/_health")
    def _health():
        return {"ok": True, "service": "backend"}
except Exception:
    pass
