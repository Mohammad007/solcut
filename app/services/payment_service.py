"""Razorpay integration. Falls back to a deterministic mock when keys are absent."""
import hashlib
import hmac

from flask import current_app


def _enabled():
    cfg = current_app.config
    return bool(cfg.get('RAZORPAY_KEY_ID') and cfg.get('RAZORPAY_KEY_SECRET'))


def _client():
    import razorpay
    cfg = current_app.config
    return razorpay.Client(auth=(cfg['RAZORPAY_KEY_ID'], cfg['RAZORPAY_KEY_SECRET']))


def create_order(amount_rupees, receipt):
    """Returns dict with order_id, amount (paise), currency, key_id, mock flag."""
    amount_paise = int(round(amount_rupees * 100))
    if not _enabled():
        current_app.logger.info(f'[MOCK PAY] order for ₹{amount_rupees} ({receipt})')
        return {
            'order_id': f'order_mock_{receipt}',
            'amount': amount_paise,
            'currency': 'INR',
            'key_id': 'rzp_test_mock',
            'mock': True,
        }
    order = _client().order.create({
        'amount': amount_paise,
        'currency': 'INR',
        'receipt': receipt,
        'payment_capture': 1,
    })
    return {
        'order_id': order['id'],
        'amount': amount_paise,
        'currency': 'INR',
        'key_id': current_app.config['RAZORPAY_KEY_ID'],
        'mock': False,
    }


def verify_signature(order_id, payment_id, signature):
    if not _enabled():
        # Mock orders always verify in dev.
        return str(order_id).startswith('order_mock_')
    secret = current_app.config['RAZORPAY_KEY_SECRET'].encode()
    expected = hmac.new(
        secret, f'{order_id}|{payment_id}'.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature or '')


def refund(payment_id, amount_rupees=None):
    if not _enabled():
        current_app.logger.info(f'[MOCK PAY] refund {payment_id}')
        return {'id': f'rfnd_mock_{payment_id}', 'status': 'processed', 'mock': True}
    data = {}
    if amount_rupees is not None:
        data['amount'] = int(round(amount_rupees * 100))
    return _client().payment.refund(payment_id, data)
