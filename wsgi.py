import os, sys
from flask import jsonify, request

# Import the real Flask app object
# If you use an app factory, change to: from app import create_app; app = create_app()
from app import app as app

# Add a version header to prove this file is active in prod
@app.after_request
def _opti_version_hdr(resp):
    resp.headers['X-Opti-Version'] = 'opti-antiagent-20250902-051410'
    return resp

# ==== OPTI: WSGI middleware to block agent headers (pre-routing) ====
def _opti_dbg(msg):
    try: sys.stderr.write('[OPTI] ' + msg + '\n')
    except: pass

class _OptiBlockAgentsMiddleware:
    def __init__(self, app):
        self.app = app
    def __call__(self, environ, start_response):
        if os.environ.get('DISABLE_AGENTS','1') != '0':
            # Block any X-Agent-* on normal requests
            for k, v in environ.items():
                if k.startswith('HTTP_') and k.lower().startswith('http_x_agent_'):
                    _opti_dbg('blocked direct header: ' + k)
                    start_response('403 FORBIDDEN', [('Content-Length','0')]); return [b'']
            # Block CORS preflight that asks to send X-Agent-*
            acrh = environ.get('HTTP_ACCESS_CONTROL_REQUEST_HEADERS','').lower()
            if 'x-agent-' in acrh:
                _opti_dbg('blocked preflight: ' + acrh)
                start_response('403 FORBIDDEN', [('Content-Length','0')]); return [b'']
        return self.app(environ, start_response)

# Wrap AFTER app is created and blueprints mounted
app.wsgi_app = _OptiBlockAgentsMiddleware(app.wsgi_app)

# Health (kept simple)
@app.get("/_health")
def _health():
    return jsonify(ok=True, service="backend")
from flask import jsonify
@app.after_request
def _opti_ver(resp):
    resp.headers['X-Opti-Version']='opti-proof-20250902-051551'
    resp.headers['X-Opti-WSGI']=__file__
    return resp

@app.get('/_whoami')
def _whoami():
    import os, sys, time
    st=os.stat(__file__)
    return jsonify(file=__file__, mtime=st.st_mtime, pid=os.getpid(), argv=sys.argv)