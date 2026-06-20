from datetime import datetime

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity

from app.extensions import db
from app.models.booking import Booking, BookingService
from app.models.service import Service
from app.models.provider import Provider
from app.models.loyalty_card import LoyaltyCard
from app.services.upload_service import save_image
from app.services import fcm_service
from app.utils.decorators import customer_required, provider_required
from app.utils.helpers import ok, err, generate_booking_no, paginate_query

bookings_bp = Blueprint('bookings', __name__)

CANCELLABLE = {'PENDING', 'CONFIRMED'}
VALID_STATUS = {'CONFIRMED', 'IN_PROGRESS', 'COMPLETED', 'NO_SHOW', 'CANCELLED'}


@bookings_bp.post('/')
@customer_required
def create_booking():
    body = request.get_json(silent=True) or {}
    provider_id = body.get('provider_id')
    service_ids = body.get('service_ids') or []
    if not provider_id or not service_ids:
        return err('provider_id and service_ids are required')

    provider = Provider.query.get(provider_id)
    if not provider:
        return err('Provider not found', 404)

    services = Service.query.filter(
        Service.id.in_(service_ids),
        Service.provider_id == provider_id,
        Service.is_active.is_(True),
    ).all()
    if len(services) != len(set(service_ids)):
        return err('One or more services are invalid for this provider')

    total = sum(s.price for s in services)
    is_home = bool(body.get('is_home_visit'))
    if is_home and provider.home_visit_charge:
        total += provider.home_visit_charge

    scheduled_at = None
    if body.get('scheduled_at'):
        try:
            scheduled_at = datetime.fromisoformat(body['scheduled_at'])
        except ValueError:
            return err('scheduled_at must be ISO 8601 format')

    booking = Booking(
        booking_no=generate_booking_no(provider_id),
        user_id=get_jwt_identity(),
        provider_id=provider_id,
        barber_id=body.get('barber_id'),
        booking_type=body.get('booking_type', 'APPOINTMENT'),
        status='PENDING',
        scheduled_at=scheduled_at,
        is_home_visit=is_home,
        home_address=body.get('home_address'),
        total_amount=total,
        style_image_url=body.get('style_image_url'),
        notes=body.get('notes'),
    )
    db.session.add(booking)
    db.session.flush()
    for s in services:
        db.session.add(BookingService(booking_id=booking.id, service_id=s.id, price=s.price))
    db.session.commit()

    if provider.fcm_token:
        when = scheduled_at.strftime('%d %b %I:%M %p') if scheduled_at else 'Walk-in'
        fcm_service.notify_new_booking_to_provider(provider.fcm_token, 'Customer', when)

    return ok(booking.to_dict(), message='Booking created', status=201)


@bookings_bp.get('/')
@customer_required
def my_bookings():
    q = Booking.query.filter_by(user_id=get_jwt_identity())
    status = request.args.get('status')
    if status == 'UPCOMING':
        q = q.filter(Booking.status.in_(['PENDING', 'CONFIRMED', 'IN_PROGRESS']))
    elif status:
        q = q.filter_by(status=status.upper())
    q = q.order_by(Booking.created_at.desc())
    items, meta = paginate_query(q, request.args.get('page'), request.args.get('limit'))
    return ok([b.to_dict() for b in items], pagination=meta)


@bookings_bp.get('/provider')
@provider_required
def provider_bookings():
    """All bookings for the provider, filterable by scope/status.

    scope=open    -> PENDING, CONFIRMED, IN_PROGRESS
    scope=history -> COMPLETED, CANCELLED, NO_SHOW
    """
    q = Booking.query.filter_by(provider_id=get_jwt_identity())
    scope = request.args.get('scope')
    if scope == 'open':
        q = q.filter(Booking.status.in_(['PENDING', 'CONFIRMED', 'IN_PROGRESS']))
    elif scope == 'history':
        q = q.filter(Booking.status.in_(['COMPLETED', 'CANCELLED', 'NO_SHOW']))
    status = request.args.get('status')
    if status:
        q = q.filter_by(status=status.upper())
    q = q.order_by(Booking.created_at.desc())
    items, meta = paginate_query(q, request.args.get('page'), request.args.get('limit'))
    return ok([b.to_dict() for b in items], pagination=meta)


@bookings_bp.get('/provider/today')
@provider_required
def provider_today():
    start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    end = start.replace(hour=23, minute=59, second=59)
    items = Booking.query.filter(
        Booking.provider_id == get_jwt_identity(),
        Booking.scheduled_at >= start,
        Booking.scheduled_at <= end,
    ).order_by(Booking.scheduled_at.asc()).all()
    return ok([b.to_dict() for b in items])


@bookings_bp.get('/provider/upcoming')
@provider_required
def provider_upcoming():
    now = datetime.utcnow()
    items = Booking.query.filter(
        Booking.provider_id == get_jwt_identity(),
        Booking.scheduled_at > now,
        Booking.status.in_(['PENDING', 'CONFIRMED']),
    ).order_by(Booking.scheduled_at.asc()).all()
    return ok([b.to_dict() for b in items])


@bookings_bp.get('/<booking_id>')
def booking_detail(booking_id):
    b = Booking.query.get(booking_id)
    if not b:
        return err('Booking not found', 404)
    return ok(b.to_dict())


@bookings_bp.post('/<booking_id>/cancel')
@customer_required
def cancel_booking(booking_id):
    b = Booking.query.filter_by(id=booking_id, user_id=get_jwt_identity()).first()
    if not b:
        return err('Booking not found', 404)
    if b.status not in CANCELLABLE:
        return err(f'Cannot cancel a {b.status} booking', 409)
    b.status = 'CANCELLED'
    db.session.commit()
    return ok(b.to_dict(), message='Booking cancelled')


@bookings_bp.post('/<booking_id>/style-image')
@customer_required
def style_image(booking_id):
    b = Booking.query.filter_by(id=booking_id, user_id=get_jwt_identity()).first()
    if not b:
        return err('Booking not found', 404)
    if 'image' not in request.files:
        return err('No image file (field: image)')
    try:
        b.style_image_url = save_image(request.files['image'], 'style_boards')
    except ValueError as e:
        return err(str(e))
    db.session.commit()
    return ok({'style_image_url': b.style_image_url})


@bookings_bp.put('/<booking_id>/status')
@provider_required
def update_status(booking_id):
    b = Booking.query.filter_by(id=booking_id, provider_id=get_jwt_identity()).first()
    if not b:
        return err('Booking not found', 404)
    body = request.get_json(silent=True) or {}
    new_status = (body.get('status') or '').upper()
    if new_status not in VALID_STATUS:
        return err(f'status must be one of {sorted(VALID_STATUS)}')

    b.status = new_status
    if new_status == 'COMPLETED':
        _on_completed(b)
    db.session.commit()
    return ok(b.to_dict(), message='Status updated')


def _on_completed(booking):
    provider = booking.provider
    provider.total_bookings = (provider.total_bookings or 0) + 1

    # Add loyalty stamp
    card = LoyaltyCard.query.filter_by(
        user_id=booking.user_id, provider_id=booking.provider_id
    ).first()
    if not card:
        card = LoyaltyCard(
            user_id=booking.user_id, provider_id=booking.provider_id, stamps=0
        )
        db.session.add(card)
    card.stamps = (card.stamps or 0) + 1

    # Ask the customer for a review
    user = booking.user
    if user and user.fcm_token:
        fcm_service.send_notification(
            user.fcm_token, '✂️ Service complete!',
            f'{provider.shop_name} — review dekar batao kaisa raha?',
            {'type': 'request_review', 'booking_id': booking.id},
        )
