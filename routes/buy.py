from flask import Blueprint, request, jsonify

buy_bp = Blueprint('buy', __name__)

@buy_bp.route('/checkout', methods=['POST'])
def checkout():
    data = request.get_json(silent=True) or {}
    for k in ('property_id','quantity','owner'):
        if k not in data:
            return jsonify(ok=False, error=f"missing {k}"), 400
    # TEMP: return a deterministic success URL (replace with Stripe later)
    return jsonify(ok=True, url="https://optilovesinvest.com/thank-you")
