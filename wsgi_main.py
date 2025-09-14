from routes_shim import shim as _opti_shim
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
# Opti shim routes (stable)
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
# Opti shim routes (stable)
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

@app.after_request
def _opti_marker_after_request(resp):
    resp.headers['X-Opti-Marker'] = 'wsgi_main.py-marker'
    return resp



# --- Opti shim (stable attach) ---
try:
    app  # is there already an 'app' here?
except NameError:
    # common pattern: from app import app
    try:
        from app import app as _app
        _app.register_blueprint(_opti_shim)
        app = _app  # ensure Gunicorn sees 'app'
    except Exception as _e:
        # last resort: if a factory is used, expose a wrapped app
        def _wrap():
            from app import app as __app
            __app.register_blueprint(_opti_shim)
            return __app
        app = _wrap()
# --- end Opti shim ---

# === Opti inline routes (stable) ===
import os, json
from flask import request, jsonify
try:
    import psycopg2
except Exception:
    psycopg2 = None

API_KEY = os.getenv("OPTI_API_KEY","")
PG_DSN  = os.getenv("PG_DSN","")

@app.get("/api/ping")
def _opti_ping():
    return jsonify({"ok": True})

@app.get("/api/diag")
def _opti_diag():
    ok=False; err=None
    if psycopg2 and PG_DSN:
        try:
            c=psycopg2.connect(PG_DSN); c.close(); ok=True
        except Exception as e:
            err=str(e)
    return jsonify({"pg_dsn_set": bool(PG_DSN), "db_ok": ok, "error": err})

@app.post("/webhooks/payment")
def _opti_payment():
    if not API_KEY or request.headers.get("x-api-key","") != API_KEY:
        return jsonify({"error":"forbidden"}), 403
    data = request.get_json(silent=True) or {}
    order_id    = data.get("order_id")
    property_id = data.get("property_id")
    owner = data.get("owner") or data.get("wallet") or data.get("investor_wallet")
    try:    qty = int(data.get("quantity") or data.get("qty_tokens") or 0)
    except: qty = 0
    try:    price = float(data.get("unit_price_usd") or data.get("unit_price") or 50.0)
    except: price = 50.0
    status = (data.get("status") or "completed").lower()
    if not order_id or not property_id or not owner or qty <= 0:
        return jsonify({"error":"invalid payload","need":["order_id","property_id","owner","quantity>0"]}), 400
    if not psycopg2 or not PG_DSN:
        return jsonify({"error":"server db not configured"}), 500
    sql = """
    insert into public.orders (order_id,property_id,owner,quantity,unit_price_usd,status,created_at)
    values (%s,%s,%s,%s,%s,%s, now())
    on conflict (order_id) do update set
      property_id=excluded.property_id,
      owner=excluded.owner,
      quantity=excluded.quantity,
      unit_price_usd=excluded.unit_price_usd,
      status=excluded.status;
    """
    try:
        conn=psycopg2.connect(PG_DSN)
        with conn, conn.cursor() as cur:
            cur.execute(sql,(order_id,property_id,owner,qty,price,status))
        conn.close()
        return jsonify({"ok":True,"order_id":order_id})
    except Exception as e:
        return jsonify({"ok":False,"error":str(e)}), 500
# === end Opti inline routes ===
# === portfolio fallback (idempotent) ===
try:
    from opti_portfolio_fallback import bp as _opti_pf
    app.register_blueprint(_opti_pf)
except Exception as _e:
    pass
# === /api/portfolio inline fallback (idempotent) ===
try:
    import os, json, time, urllib.request
    from flask import jsonify, request
    _have_pf = any(str(r.rule).startswith('/api/portfolio') for r in app.url_map.iter_rules())
    if not _have_pf:
        def _rpc(url, method, params):
            data=json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode()
            req=urllib.request.Request(url, data=data, headers={'Content-Type':'application/json'})
            with urllib.request.urlopen(req, timeout=10) as r: return json.loads(r.read().decode())

        def _rpc_url(): return os.getenv('SOLANA_RPC','https://api.mainnet-beta.solana.com')
        def _mints():
            ms=[m.strip() for m in os.getenv('OPTILOVES_MINTS','').split(',') if m.strip()]
            return ms or ['5ihsE55yaFFZXoizZKv5xsd6YjEuvaXiiMr2FLjQztN9']

        def _items(owner):
            out=[]; rpc=_rpc_url()
            for m in _mints():
                resp=_rpc(rpc,'getTokenAccountsByOwner',[owner,{'mint':m},{'encoding':'jsonParsed'}])
                total=0.0
                for v in resp.get('result',{}).get('value',[]):
                    ui=v['account']['data']['parsed']['info']['tokenAmount'].get('uiAmount',0) or 0
                    try: total+=float(ui)
                    except: pass
                price=float(os.getenv('OPTILOVES_BASE_PRICE_USD','50'))
                out.append({'mint':m,'balance':total,'price':price,'estValue':round(total*price,2)})
            return out

        def _pf_owner(owner):
            return jsonify({'owner':owner,'items':_items(owner),'ts':int(time.time()*1000)})
        def _pf_query():
            owner=(request.args.get('owner','') or '').strip()
            return jsonify({'owner':owner,'items':_items(owner),'ts':int(time.time()*1000)})

        app.add_url_rule('/api/portfolio/<owner>','opti_pf_owner',_pf_owner,methods=['GET'])
        app.add_url_rule('/api/portfolio','opti_pf_query',_pf_query,methods=['GET'])
        try: app.logger.warning('opti_portfolio_inline_fallback_loaded')
        except: pass
except Exception as _e:
    try: app.logger.warning(f'opti_portfolio_inline_fallback_error: {_e}')
    except: pass
# === end /api/portfolio inline fallback ===
# === /api/portfolio inline fallback (idempotent) ===
try:
    import os, json, time, urllib.request
    from flask import jsonify, request
    def _rpc(u,m,p):
        d=json.dumps({'jsonrpc':'2.0','id':1,'method':m,'params':p}).encode()
        r=urllib.request.Request(u,data=d,headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(r,timeout=10) as x: return json.loads(x.read().decode())
    def _rpc_url(): return os.getenv('SOLANA_RPC','https://api.mainnet-beta.solana.com')
    def _mints():
        ms=[m.strip() for m in os.getenv('OPTILOVES_MINTS','').split(',') if m.strip()]
        return ms or ['5ihsE55yaFFZXoizZKv5xsd6YjEuvaXiiMr2FLjQztN9']
    def _items(owner):
        out=[]; rpc=_rpc_url()
        for m in _mints():
            resp=_rpc(rpc,'getTokenAccountsByOwner',[owner,{'mint':m},{'encoding':'jsonParsed'}])
            total=0.0
            for v in resp.get('result',{}).get('value',[]):
                ui=v['account']['data']['parsed']['info']['tokenAmount'].get('uiAmount',0) or 0
                try: total+=float(ui)
                except: pass
            price=float(os.getenv('OPTILOVES_BASE_PRICE_USD','50'))
            out.append({'mint':m,'balance':total,'price':price,'estValue':round(total*price,2)})
        return out
    def _pf_owner(owner): return jsonify({'owner':owner,'items':_items(owner),'ts':int(time.time()*1000)})
    def _pf_query(): 
        owner=(request.args.get('owner','') or '').strip()
        return jsonify({'owner':owner,'items':_items(owner),'ts':int(time.time()*1000)})
    app.add_url_rule('/api/portfolio/<owner>','opti_pf_owner',_pf_owner,methods=['GET'])
    app.add_url_rule('/api/portfolio','opti_pf_query',_pf_query,methods=['GET'])
except Exception as _e:
    pass
