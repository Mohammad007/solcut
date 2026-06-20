from flask import Blueprint, request, current_app
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required,
    get_jwt_identity, get_jwt,
)

from app.extensions import db, limiter
from app.models.user import User
from app.models.provider import Provider
from app.models.auth import TokenBlocklist
from app.services import otp_service
from app.utils.helpers import ok, err, is_valid_indian_phone

auth_bp = Blueprint('auth', __name__)


def _tokens_for(identity, role):
    claims = {'role': role}
    return (
        create_access_token(identity=identity, additional_claims=claims),
        create_refresh_token(identity=identity, additional_claims=claims),
    )


@auth_bp.post('/send-otp')
@limiter.limit('5 per hour')
def send_otp():
    body = request.get_json(silent=True) or {}
    phone = str(body.get('phone', '')).strip()
    user_type = body.get('user_type', 'customer')

    if not is_valid_indian_phone(phone):
        return err('Invalid phone number. Use a 10-digit Indian mobile number.')
    if user_type not in ('customer', 'provider'):
        return err('user_type must be "customer" or "provider"')
    if not otp_service.can_send(phone):
        return err('Too many OTP requests. Try again later.', 429)

    session, dev_code = otp_service.send_otp(phone, user_type)
    extra = {'session_id': session.id}
    if dev_code is not None:
        extra['dev_otp'] = dev_code  # only present in mock mode
    return ok(message='OTP sent', **extra)


@auth_bp.post('/verify-otp')
def verify_otp():
    body = request.get_json(silent=True) or {}
    phone = str(body.get('phone', '')).strip()
    otp = str(body.get('otp', '')).strip()
    user_type = body.get('user_type', 'customer')

    if not is_valid_indian_phone(phone):
        return err('Invalid phone number')
    if not otp:
        return err('OTP is required')

    if not otp_service.verify_otp(phone, otp, user_type):
        return err('Invalid or expired OTP', 401)

    is_new = False
    if user_type == 'customer':
        entity = User.query.filter_by(phone=phone).first()
        if not entity:
            entity = User(phone=phone)
            db.session.add(entity)
            db.session.commit()
            is_new = True
        access, refresh = _tokens_for(entity.id, 'customer')
        data = entity.to_dict()
    else:
        entity = Provider.query.filter_by(phone=phone).first()
        if not entity:
            # Minimal placeholder; profile completed via providers/register
            entity = Provider(phone=phone, owner_name='', shop_name='', shop_type='BARBER')
            db.session.add(entity)
            db.session.commit()
            is_new = True
        access, refresh = _tokens_for(entity.id, 'provider')
        data = entity.to_dict(include_private=True)

    return ok({
        'access_token': access,
        'refresh_token': refresh,
        'is_new_user': is_new,
        'profile_complete': data.get('profile_complete', True),
        'user': data,
    })


@auth_bp.post('/refresh-token')
@jwt_required(refresh=True)
def refresh_token():
    identity = get_jwt_identity()
    role = get_jwt().get('role', 'customer')
    access = create_access_token(identity=identity, additional_claims={'role': role})
    return ok({'access_token': access})


@auth_bp.post('/logout')
@jwt_required()
def logout():
    jti = get_jwt()['jti']
    db.session.add(TokenBlocklist(jti=jti))
    db.session.commit()
    return ok(message='Logged out')
