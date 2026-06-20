from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity

from app.extensions import db
from app.models.user import User
from app.models.booking import Booking
from app.models.loyalty_card import LoyaltyCard
from app.services.upload_service import save_image
from app.utils.decorators import customer_required
from app.utils.helpers import ok, err, paginate_query, is_valid_indian_phone

users_bp = Blueprint('users', __name__)


def _current_user():
    return User.query.get(get_jwt_identity())


@users_bp.get('/me')
@customer_required
def get_me():
    user = _current_user()
    if not user:
        return err('User not found', 404)
    return ok(user.to_dict())


@users_bp.put('/me')
@customer_required
def update_me():
    user = _current_user()
    if not user:
        return err('User not found', 404)
    body = request.get_json(silent=True) or {}

    # Phone is the login identifier — validate format and uniqueness on change.
    if 'phone' in body:
        new_phone = str(body['phone']).strip()
        if new_phone != user.phone:
            if not is_valid_indian_phone(new_phone):
                return err('Enter a valid 10-digit mobile number')
            clash = User.query.filter(
                User.phone == new_phone, User.id != user.id
            ).first()
            if clash:
                return err('This mobile number is already in use', 409)
            user.phone = new_phone

    for field in ('name', 'email', 'city', 'state', 'preferred_lang', 'avatar_url'):
        if field in body:
            setattr(user, field, body[field])
    db.session.commit()
    return ok(user.to_dict(), message='Profile updated')


@users_bp.put('/me/avatar')
@customer_required
def update_avatar():
    user = _current_user()
    if 'image' not in request.files:
        return err('No image file (field name: image)')
    try:
        url = save_image(request.files['image'], 'avatars')
    except ValueError as e:
        return err(str(e))
    user.avatar_url = url
    db.session.commit()
    return ok({'avatar_url': url})


@users_bp.put('/me/fcm-token')
@customer_required
def update_fcm():
    user = _current_user()
    body = request.get_json(silent=True) or {}
    user.fcm_token = body.get('fcm_token')
    db.session.commit()
    return ok(message='FCM token updated')


@users_bp.get('/me/bookings')
@customer_required
def my_bookings():
    user = _current_user()
    q = Booking.query.filter_by(user_id=user.id)
    status = request.args.get('status')
    if status:
        q = q.filter_by(status=status.upper())
    q = q.order_by(Booking.created_at.desc())
    items, meta = paginate_query(q, request.args.get('page'), request.args.get('limit'))
    return ok([b.to_dict() for b in items], pagination=meta)


@users_bp.get('/me/loyalty-cards')
@customer_required
def my_loyalty():
    user = _current_user()
    cards = LoyaltyCard.query.filter_by(user_id=user.id).all()
    return ok([c.to_dict() for c in cards])
