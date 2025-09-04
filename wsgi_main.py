import os, sys
from flask import jsonify, request
from app import app as app   # <-- imports your existing Flask app object

@app.after_request
def _opti_ver(resp):
    resp.headers['X-Opti-Version'] = 'opti-wsgi-main-20250902-052502'
    resp.headers['X-Opti-Entrypoint'] = __file__
    return resp

@app.get('/_whoami')
def _whoami():
    st = os.stat(__file__)
    return jsonify(file=__file__, mtime=st.st_mtime, pid=os.getpid(), argv=sys.argv)

# ---- optional: keep the WSGI agent-header block (pre-routing) ----
class _OptiBlockAgentsMiddleware:
    def __init__(self, app): self.app = app
    def __call__(self, environ, start_response):
        if os.environ.get('DISABLE_AGENTS','1') != '0':
            for k in environ:
                if k.startswith('HTTP_') and k.lower().startswith('http_x_agent_'):
                    start_response('403 FORBIDDEN',[('Content-Length','0')]); return [b'']
            acrh = environ.get('HTTP_ACCESS_CONTROL_REQUEST_HEADERS','').lower()
            if 'x-agent-' in acrh:
                start_response('403 FORBIDDEN',[('Content-Length','0')]); return [b'']
        return self.app(environ, start_response)

app.wsgi_app = _OptiBlockAgentsMiddleware(app.wsgi_app)
# ==== TEMP PORTFOLIO SHIM (remove after wiring real impl) ====
try:
    from flask import jsonify
    _a = app if 'app' in globals() else __import__('app').app
    @_a.get("/api/portfolio/<owner>")
    def _opti_portfolio_temp(owner):
        return jsonify({"owner": owner, "items": [], "source": "shim"}), 200
except Exception as _e:
    pass
# ==== /TEMP SHIM ====