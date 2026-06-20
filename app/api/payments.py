from flask import Blueprint, request, current_app
from flask_jwt_extended import get_jwt_identity, get_jwt

from app.extensions import db
from app.models.booking import Booking
from app.models.payment import Payment
from app.services import payment_service, fcm_service
from app.utils.decorators import customer_required
from app.utils.helpers import ok, err

payments_bp = Blueprint('payments', __name__)


@payments_bp.post('/create-order')
@customer_required
def create_order():
    body = request.get_json(silent=True) or {}
    booking_id = body.get('booking_id')
    booking = Booking.query.filter_by(id=booking_id, user_id=get_jwt_identity()).first()
    if not booking:
        return err('Booking not found', 404)
    if booking.is_paid:
        return err('Booking already paid', 409)

    order = payment_service.create_order(booking.total_amount, receipt=booking.booking_no)

    payment = booking.payment or Payment(booking_id=booking.id, amount=booking.total_amount)
    payment.razorpay_order_id = order['order_id']
    payment.status = 'PENDING'
    db.session.add(payment)
    db.session.commit()

    return ok({
        'razorpay_order_id': order['order_id'],
        'amount': booking.total_amount,
        'amount_paise': order['amount'],
        'currency': order['currency'],
        'razorpay_key': order['key_id'],
        'mock': order.get('mock', False),
    })


@payments_bp.post('/verify')
@customer_required
def verify():
    body = request.get_json(silent=True) or {}
    order_id = body.get('razorpay_order_id')
    payment_id = body.get('razorpay_payment_id')
    signature = body.get('razorpay_signature')

    payment = Payment.query.filter_by(razorpay_order_id=order_id).first()
    if not payment:
        return err('Order not found', 404)

    if not payment_service.verify_signature(order_id, payment_id, signature):
        payment.status = 'FAILED'
        db.session.commit()
        return err('Payment verification failed', 400)

    payment.status = 'SUCCESS'
    payment.razorpay_payment_id = payment_id
    booking = payment.booking
    booking.is_paid = True
    if booking.status == 'PENDING':
        booking.status = 'CONFIRMED'
    db.session.commit()

    if booking.user and booking.user.fcm_token:
        when = booking.scheduled_at.strftime('%d %b %I:%M %p') if booking.scheduled_at else ''
        fcm_service.notify_booking_confirmed(
            booking.user.fcm_token, booking.provider.shop_name, when
        )
    if booking.provider and booking.provider.fcm_token:
        fcm_service.notify_new_booking_to_provider(
            booking.provider.fcm_token, booking.user.name or 'Customer', '(paid)'
        )

    return ok(payment.to_dict(), message='Payment successful')


@payments_bp.post('/refund/<booking_id>')
@customer_required
def refund(booking_id):
    booking = Booking.query.get(booking_id)
    if not booking:
        return err('Booking not found', 404)
    # Allow the booking's customer (or admin via separate flow) to refund.
    if booking.user_id != get_jwt_identity() and get_jwt().get('role') != 'provider':
        return err('Forbidden', 403)
    payment = booking.payment
    if not payment or payment.status != 'SUCCESS':
        return err('No successful payment to refund', 409)

    payment_service.refund(payment.razorpay_payment_id, payment.amount)
    payment.status = 'REFUNDED'
    booking.is_paid = False
    db.session.commit()
    return ok(payment.to_dict(), message='Refund initiated')
