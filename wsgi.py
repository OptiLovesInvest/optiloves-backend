from app.backup.before-v5 C:.Users.ruben.Documents.optiloves-backend.app.backup C:.Users.ruben.Documents.optiloves-backend.app.before-v10.backup C:.Users.ruben.Documents.optiloves-backend.app.before-v6.backup C:.Users.ruben.Documents.optiloves-backend.app.before-v7.backup C:.Users.ruben.Documents.optiloves-backend.app.before-v8.backup C:.Users.ruben.Documents.optiloves-backend.app.cors-prodonly.backup C:.Users.ruben.Documents.optiloves-backend.app C:.Users.ruben.Documents.optiloves-backend..venv.Lib.site-packages.flask.app C:.Users.ruben.Documents.optiloves-backend..venv.Lib.site-packages.flask.sessions C:.Users.ruben.Documents.optiloves-backend..venv.Lib.site-packages.flask.sansio.app C:.Users.ruben.Documents.optiloves-backend.venv.Lib.site-packages.flask.app C:.Users.ruben.Documents.optiloves-backend.venv.Lib.site-packages.flask.sessions C:.Users.ruben.Documents.optiloves-backend.venv.Lib.site-packages.flask.sansio.app import app  # uses existing Flask app

from routes.admin_sql import bp as admin_sql_bp
app.register_blueprint(admin_sql_bp)

from flask import jsonify
@app.get("/ping")
def _ping():
    return jsonify({"ok": True})