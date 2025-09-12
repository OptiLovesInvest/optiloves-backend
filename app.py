from flask import Flask, request, jsonify
import os

app = Flask(__name__)

# --- Security headers (strict CSP/CORS per policy) ---
ALLOWED = {"https://optilovesinvest.com", "https://www.optilovesinvest.com"}
CSP = "default-src 'none'; connect-src 'self' https://optilovesinvest.com https://www.optilovesinvest.com; img-src 'self' data: https:; script-src 'self'; style-src 'self'; font-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'none'; object-src 'none'"

@app.after_request
def _headers(r):
    origin = request.headers.get('Origin')
    if origin in ALLOWED:
        r.headers['Access-Control-Allow-Origin'] = origin
        r.headers['Vary'] = 'Origin'
    r.headers['Content-Security-Policy'] = CSP
    r.headers['X-Opti-Version'] = '2025-09-09'
    r.headers['X-Opti-Edge'] = 'render'
    return r

@app.get('/_health')
def _health():
    return {'ok': True, 'service': 'optiloves-backend'}

# --- API key guard for /api/* (except KYC + webhooks) ---
_APIKEY = os.environ.get('API_KEY') or os.environ.get('OPTI_API_KEY')

@app.before_request
def _api_guard():
    p = request.path or ''
    if p == '/_health' or p.startswith('/api/kyc/') or p.startswith('/webhooks/'):
        return None
    if p.startswith('/api/'):
        if not _APIKEY:
            app.logger.warning('API_KEY not set; /api/* open')
            return None
        if request.headers.get('X-Opti-ApiKey') != _APIKEY:
            return jsonify({'error': 'forbidden'}), 403
    return None

# --- Optional: mount existing KYC blueprint if available ---
try:
    from kyc import kyc_bp
    app.register_blueprint(kyc_bp, url_prefix='/api/kyc')
except Exception as _e:
    app.logger.info('KYC blueprint not mounted: %s', _e)

# --- Payment webhook: ensures unit_price_usd set & settles order ---
from decimal import Decimal
UNIT_PRICE_USD = {'kin-001': Decimal('50')}

def _price(pid: str) -> Decimal:
    return UNIT_PRICE_USD.get(pid or 'kin-001', Decimal('50'))

@app.post('/webhooks/payment')
def payment_webhook():
    try:
        data = request.get_json(silent=True) or {}
        order_id    = data.get('order_id')
        property_id = (data.get('property_id') or 'kin-001')
        wallet      = data.get('wallet')
        quantity    = int(data.get('quantity') or 0)
        status      = str(data.get('status') or 'succeeded').lower()
        if not order_id or not wallet or quantity <= 0:
            return jsonify({'error':'invalid payload'}), 400

        unit_price = _price(property_id)
        total_usd  = float(unit_price) * quantity

        if status not in ('succeeded','paid','settled'):
            app.logger.warning('Payment not settled for %s: %s', order_id, status)
            return jsonify({'ok': True, 'pending': True}), 202

        dsn = os.environ.get('PG_DSN')
        if not dsn:
            app.logger.error('PG_DSN missing')
            return jsonify({'error':'server misconfig'}), 500

        import psycopg2
        with psycopg2.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("""
\ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ INSERT\ INTO\ orders\ \(id,\ property_id,\ wallet,\ quantity,\ unit_price_usd,\ total_usd,\ status\)\n\ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ VALUES\ \(%s,%s,%s,%s,%s,%s,'settled'\)\n\ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ ON\ CONFLICT\ \(id\)\ DO\ UPDATE\n\ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ SET\ unit_price_usd=EXCLUDED\.unit_price_usd,\n\ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ total_usd\ \ \ \ \ =EXCLUDED\.total_usd,\n\ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ quantity\ \ \ \ \ \ =EXCLUDED\.quantity,\n\ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ property_id\ \ \ =EXCLUDED\.property_id,\n\ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ wallet\ \ \ \ \ \ \ \ =EXCLUDED\.wallet,\n\ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ status\ \ \ \ \ \ \ \ ='settled';
                """, (order_id, property_id, wallet, quantity, unit_cents, total_cents, status_db)

        return jsonify({'ok': True, 'order_id': order_id, 'unit_price_usd': float(unit_price), 'total_usd': total_usd}), 200
    except Exception as ex:
    app.logger.exception('payment_webhook failed')
    # show error only when explicitly requested
    from flask import request
    if request.headers.get('X-Opti-Debug') == '1':
        return jsonify({'error': str(ex)[:300]}), 500
    return jsonify({'error':'internal'}), 500

# WSGI entry
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5050)
# ==== OPTI DIAG START (secure) ====
@app.get('/api/ping')
def api_ping():
    return {'ok': True, 'msg': 'api alive'}

@app.get('/api/diag')
def api_diag():
    # Protected by before_request API key guard
    info = {'pg_dsn_set': bool(os.environ.get('PG_DSN')), 'psycopg2': None, 'db_ok': None, 'error': None}
    try:
        import psycopg2  # noqa
        info['psycopg2'] = True
        dsn = os.environ.get('PG_DSN')
        if not dsn:
            info['db_ok'] = False
            return info, 200
        try:
            with psycopg2.connect(dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT 1;')
                    info['db_ok'] = (cur.fetchone()[0] == 1)
        except Exception as ex:
            info['db_ok'] = False
            info['error'] = str(ex)[:300]
    except Exception as ex:
        info['psycopg2'] = False
        info['error'] = str(ex)[:300]
    return info, 200
# ==== OPTI DIAG END ====

# ==== OPTI DSN SANITIZE START ====
def _clean_dsn(v: str) -> str:
    try:
        # strip whitespace and any accidental wrapping quotes
        return (v or "").strip().strip('"').strip("'")
    except Exception:
        return v or ""

# normalize PG_DSN once, early
try:
    _raw = os.environ.get("PG_DSN") or ""
    os.environ["PG_DSN"] = _clean_dsn(_raw)
    if _raw and _raw != os.environ["PG_DSN"]:
        app.logger.warning("PG_DSN sanitized (leading/trailing quotes/space removed)")
except Exception as _e:
    app.logger.warning("PG_DSN sanitize skipped: %s", _e)
# ==== OPTI DSN SANITIZE END ====

# ==== OPTI PORTFOLIO START ====
import json, urllib.request, urllib.error, time

def _env_csv(name, default=""):
    v = os.environ.get(name) or default
    return [x.strip() for x in v.split(",") if x.strip()]

def _sol_post(rpc_url, method, params):
    payload = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode("utf-8")
    req = urllib.request.Request(rpc_url, data=payload, headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))

def _sum_ui_amount(value_list):
    total = 0.0
    for it in value_list or []:
        try:
            amt = it["account"]["data"]["parsed"]["info"]["tokenAmount"]["uiAmount"] or 0
            total += float(amt)
        except Exception:
            continue
    return total

@app.get('/api/portfolio/<owner>')
def api_portfolio(owner: str):
    try:
        if not owner or len(owner) < 32:
            return jsonify({'ok': False, 'error': 'invalid owner'}), 400

        rpc   = os.environ.get('SOLANA_RPC') or 'https://api.mainnet-beta.solana.com'
        mdefs = _parse_mints_env()
        if not mdefs:
            return jsonify({'ok': False, 'error': 'OPTILOVES_MINTS not set'}), 200

        items = []
        total_tokens = 0.0
        total_usd    = 0.0

        for md in mdefs:
            mint  = md['mint']
            price = float(md.get('price') or 50)
            try:
                rs = _sol_post(rpc, 'getTokenAccountsByOwner', [owner, {'mint': mint}, {'encoding':'jsonParsed'}])
                value = (rs or {}).get('result',{}).get('value',[])
                qty = _sum_ui_amount(value)
                usd = round(qty * price, 6)
                items.append({'id': md['id'], 'mint': mint, 'quantity': qty, 'unit_price_usd': price, 'est_value_usd': usd})
                total_tokens += qty
                total_usd    += usd
                time.sleep(0.05)
            except urllib.error.URLError as e:
                return jsonify({'ok': False, 'error': f'rpc_unreachable: {str(e)[:180]}'}), 200
            except Exception as e:
                items.append({'id': md['id'], 'mint': mint, 'quantity': 0, 'unit_price_usd': price, 'error': str(e)[:120]})

        return jsonify({
            'ok': True,
            'owner': owner,
            'total_tokens': total_tokens,
            'est_value_usd': round(total_usd, 6),
            'items': items
        }), 200
    except Exception:
        app.logger.exception('api_portfolio failed')
        return jsonify({'ok': False, 'error': 'internal'}), 500
# ==== OPTI PORTFOLIO END ====

# ==== OPTI MINT PARSER START ====
def _parse_mints_env():
    raw = os.environ.get("OPTILOVES_MINTS") or ""
    unit_default = float(os.environ.get("UNIT_PRICE_USD") or 50)
    out = []
    try:
        s = raw.strip()
        if s.startswith("[") or s.startswith("{"):
            data = json.loads(s)
            if isinstance(data, dict): data=[data]
            for it in data:
                mint = (it.get("mint") or "").strip()
                if mint:
                    out.append({
                        "id": it.get("id") or mint[:6],
                        "mint": mint,
                        "price": float(it.get("price") or unit_default)
                    })
        else:
            # CSV of mints
            for mint in [x.strip() for x in raw.split(",") if x.strip()]:
                out.append({"id": mint[:6], "mint": mint, "price": unit_default})
    except Exception as _e:
        app.logger.warning("OPTILOVES_MINTS parse failed: %s", _e)
    return out
# ==== OPTI MINT PARSER END ====












# ==== OPTI WEBHOOK REWRITE START ====
@app.route('/webhooks/payment', methods=['POST'])
def payment_webhook():
    try:
        from flask import request, jsonify
        import os, psycopg2

        data        = request.get_json(force=True, silent=False) or {}
        order_id    = (data.get('order_id') or '').strip()
        property_id = (data.get('property_id') or '').strip()
        wallet      = (data.get('wallet') or '').strip()
        quantity    = int(data.get('quantity') or 0)
        status_in   = (data.get('status') or '').lower()
        if not (order_id and property_id and wallet and quantity > 0):
            return jsonify({'error':'bad_request'}), 400

        unit_price  = float(os.environ.get('UNIT_PRICE_USD') or 50)
        unit_cents  = int(round(unit_price * 100))
        total_cents = unit_cents * quantity
        status_db   = 'completed' if status_in in ('succeeded','completed','paid','ok') else 'pending'

        with psycopg2.connect(os.environ['PG_DSN']) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO orders (id, property_id, wallet, quantity, unit_price_usd, total_usd, status) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s) "
                    "ON CONFLICT (id) DO UPDATE SET "
                    "unit_price_usd=EXCLUDED.unit_price_usd, "
                    "total_usd=EXCLUDED.total_usd, "
                    "quantity=EXCLUDED.quantity, "
                    "property_id=EXCLUDED.property_id, "
                    "wallet=EXCLUDED.wallet, "
                    "status=EXCLUDED.status;",
                    (order_id, property_id, wallet, quantity, unit_cents, total_cents, status_db)
                )

        return jsonify({'ok': True, 'order_id': order_id, 'unit_price_usd': unit_price, 'total_usd': total_cents/100.0}), 200
    except Exception as ex:
    app.logger.exception('payment_webhook failed')
    from flask import request
    if request.headers.get('X-Opti-Debug') == '1':
        return jsonify({'error': str(ex)}), 500
    return jsonify({'error':'internal'}), 500
# ==== OPTI WEBHOOK REWRITE END ====


# ==== OPTI TEST WEBHOOK START ====
@app.route('/api/webhook-test', methods=['POST'])
def api_webhook_test():
    try:
        from flask import request, jsonify
        import os, psycopg2
        if request.headers.get('X-Opti-ApiKey') != os.environ.get('API_KEY'):
            return jsonify({'error': 'forbidden'}), 403

        data        = request.get_json(force=True, silent=False) or {}
        order_id    = (data.get('order_id') or '').strip()
        property_id = (data.get('property_id') or '').strip()
        wallet      = (data.get('wallet') or '').strip()
        quantity    = int(data.get('quantity') or 0)
        status_in   = (data.get('status') or '').lower()
        if not (order_id and property_id and wallet and quantity > 0):
            return jsonify({'error':'bad_request'}), 400

        unit_price  = float(os.environ.get('UNIT_PRICE_USD') or 50)
        unit_cents  = int(round(unit_price * 100))
        total_cents = unit_cents * quantity
        status_db   = 'completed' if status_in in ('succeeded','completed','paid','ok') else 'pending'

        with psycopg2.connect(os.environ['PG_DSN']) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO orders (id, property_id, wallet, quantity, unit_price_usd, total_usd, status) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s) "
                    "ON CONFLICT (id) DO UPDATE SET "
                    "unit_price_usd=EXCLUDED.unit_price_usd, "
                    "total_usd=EXCLUDED.total_usd, "
                    "quantity=EXCLUDED.quantity, "
                    "property_id=EXCLUDED.property_id, "
                    "wallet=EXCLUDED.wallet, "
                    "status=EXCLUDED.status;",
                    (order_id, property_id, wallet, quantity, unit_cents, total_cents, status_db)
                )

        return jsonify({'ok': True, 'order_id': order_id, 'unit_price_usd': unit_price, 'total_usd': total_cents/100.0}), 200
    except Exception as ex:
        # Return the real error so we can fix it
        return jsonify({'ok': False, 'error': str(ex)}), 500
# ==== OPTI TEST WEBHOOK END ====
