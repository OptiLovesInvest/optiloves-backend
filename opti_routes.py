from flask import Blueprint, request, jsonify
import os, psycopg2

bp = Blueprint('opti_routes', __name__)

@bp.route('/api/routes', methods=['GET'])
def api_routes():
    try:
        app = bp._app_ctx_stack.top.app  # access app to list routes
        rules = [{'rule': str(r), 'methods': sorted(list(r.methods))} for r in app.url_map.iter_rules()]
        return jsonify({'ok': True, 'routes': rules}), 200
    except Exception as ex:
        return jsonify({'ok': False, 'error': str(ex)}), 500

@bp.route('/api/webhook-test', methods=['POST'])
def api_webhook_test():
    try:
        if request.headers.get('X-Opti-ApiKey') != os.environ.get('API_KEY'):
            return jsonify({'error':'forbidden'}), 403
        data        = request.get_json(force=True, silent=False) or {}
        order_id    = (data.get('order_id') or '').strip()
        property_id = (data.get('property_id') or '').strip()
        wallet      = (data.get('wallet') or '').strip()
        quantity    = int(data.get('quantity') or 0)
        status_in   = (data.get('status') or '').lower()
        if not (order_id and property_id and wallet and quantity > 0):
            return jsonify({'error':'bad_request'}), 400
        unit_price  = float(os.environ.get('UNIT_PRICE_USD') or 50.0)
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
        return jsonify({'ok': False, 'error': str(ex)}), 500

@bp.route('/webhooks/payment2', methods=['POST'])
def payment_webhook2():
    try:
        data        = request.get_json(force=True, silent=False) or {}
        order_id    = (data.get('order_id') or '').strip()
        property_id = (data.get('property_id') or '').strip()
        wallet      = (data.get('wallet') or '').strip()
        quantity    = int(data.get('quantity') or 0)
        status_in   = (data.get('status') or '').lower()
        if not (order_id and property_id and wallet and quantity > 0):
            return jsonify({'error':'bad_request'}), 400
        unit_price  = float(os.environ.get('UNIT_PRICE_USD') or 50.0)
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
        # reveal error when asked
        if request.headers.get('X-Opti-Debug') == '1':
            return jsonify({'error': str(ex)}), 500
        return jsonify({'error':'internal'}), 500

# == BEGIN: portfolio+routes (opti_routes) ==
from flask import request, jsonify, current_app as _ca

@opti_routes.get('/portfolio/<owner>')
def _opti_portfolio_owner(owner):
    owner=(owner or '').strip()
    if not owner: return jsonify({'owner':'','items':[],'total':0,'source':'opti'}),200
    return jsonify({'owner':owner,'items':[],'total':0,'source':'opti'}),200

@opti_routes.get('/portfolio')
def _opti_portfolio_q():
    owner=(request.args.get('owner','') or '').strip()
    if not owner: return jsonify({'error':'missing owner'}),400
    return jsonify({'owner':owner,'items':[],'total':0,'source':'opti'}),200

@opti_routes.get('/routes')
def _opti_routes_list():
    rules=[{'rule':str(r),'endpoint':r.endpoint,'methods':sorted(list(r.methods))} for r in _ca.url_map.iter_rules()]
    return {'ok':True,'routes':rules},200
# == END: portfolio+routes (opti_routes) ==
