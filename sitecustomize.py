import importlib
try:
    m = importlib.import_module("app")
    app = getattr(m, "app", None) or getattr(m, "application", None)
    if app:
        from app_kyc import kyc
        if "kyc" not in app.blueprints:
            app.register_blueprint(kyc, url_prefix="/api/kyc")

        @app.get("/_health")
        def _health():
            return {"ok": True, "service": "backend"}
except Exception:
    pass