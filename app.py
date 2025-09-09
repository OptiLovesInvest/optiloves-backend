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
                    INSERT INTO orders (id, property_id, wallet, quantity, unit_price_usd, total_usd, status, created_at)
                    VALUES (%s,%s,%s,%s,%s,%s,'settled',NOW())
                    ON CONFLICT (id) DO UPDATE
                    SET unit_price_usd=EXCLUDED.unit_price_usd,
                        total_usd     =EXCLUDED.total_usd,
                        quantity      =EXCLUDED.quantity,
                        property_id   =EXCLUDED.property_id,
                        wallet        =EXCLUDED.wallet,
                        status        ='settled',
                        updated_at    =NOW();
                """, (order_id, property_id, wallet, quantity, float(unit_price), total_usd))

        return jsonify({'ok': True, 'order_id': order_id, 'unit_price_usd': float(unit_price), 'total_usd': total_usd}), 200
    except Exception:
        app.logger.exception('payment_webhook failed')
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
