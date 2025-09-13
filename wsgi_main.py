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
# ==== PORTFOLIO ROUTE (real, zero-deps) ====
import os, json, urllib.request
from flask import jsonify
_a = app if 'app' in globals() else __import__('app').app

RPC   = os.environ.get('SOLANA_RPC','https://api.mainnet-beta.solana.com')
MINTS = [m.strip() for m in os.environ.get('OPTILOVES_MINTS','').split(',') if m.strip()]

# Display metadata map (extend as you add more mints)
MINT_META = {
  '5ihsE55yaFFZXoizZKv5xsd6YjEuvaXiiMr2FLjQztN9': {
    'name': 'Opti Nsele',
    'symbol': 'OPTI-NSELE',
    'icon': 'https://optilovesinvest.com/favicon.ico',
  }
}

def _rpc(method, params):
    try:
        payload = json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode('utf-8')
        req = urllib.request.Request(RPC, data=payload, headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return {'error': str(e)}

@_a.get('/api/portfolio/<owner>')
def opti_portfolio(owner):
    items = []
    for mint in MINTS:
        res = _rpc('getTokenAccountsByOwner', [owner, {'mint': mint}, {'encoding':'jsonParsed'}])
        bal = 0
        try:
            for acc in res.get('result', {}).get('value', []):
                amt = acc['account']['data']['parsed']['info']['tokenAmount']['uiAmount']
                if amt: bal += amt
        except Exception:
            pass
        if bal > 0:
            meta = MINT_META.get(mint)
            item = {'mint': mint, 'balance': int(bal)}
            if meta:
                item.update(meta)
            items.append(item)
    return jsonify({'owner': owner, 'items': items, 'source': 'rpc'}), 200
# ==== /PORTFOLIO ROUTE ====@app.route('/routes', methods=['GET'])
def _opti_public_routes():
    from flask import jsonify
    rules = [{'rule': str(r), 'methods': sorted(list(r.methods))} for r in app.url_map.iter_rules()]
    return jsonify({'ok': True, 'routes': rules}), 200
