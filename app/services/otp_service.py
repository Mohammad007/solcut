"""OTP send/verify. Supports a 'mock' provider (dev), Twilio Verify, and MSG91.

In mock mode the code is always Config.OTP_MOCK_CODE (default 123456) and is also
returned so the dev UI/console can show it. No external account needed.
"""
import random
from datetime import datetime, timedelta

from flask import current_app

from app.extensions import db
from app.models.auth import OtpSession, OtpLog


def _provider():
    return (current_app.config.get('OTP_PROVIDER') or 'mock').lower()


def can_send(phone, max_per_hour=5):
    """Rate limit: at most `max_per_hour` sends per phone per rolling hour."""
    since = datetime.utcnow() - timedelta(hours=1)
    count = OtpLog.query.filter(
        OtpLog.phone == phone, OtpLog.created_at >= since
    ).count()
    return count < max_per_hour


def send_otp(phone, user_type):
    """Create an OtpSession and dispatch the code. Returns (session, dev_code)."""
    db.session.add(OtpLog(phone=phone))

    provider = _provider()
    expires_at = datetime.utcnow() + timedelta(
        minutes=current_app.config.get('OTP_EXPIRY_MINUTES', 5)
    )

    # Invalidate older unverified sessions for this phone
    OtpSession.query.filter_by(phone=phone, verified=False).delete()

    dev_code = None
    if provider == 'mock':
        code = current_app.config.get('OTP_MOCK_CODE', '123456')
        dev_code = code
        current_app.logger.info(f'[MOCK OTP] {phone} -> {code}')
        session = OtpSession(
            phone=phone, user_type=user_type, otp_code=code, expires_at=expires_at
        )
    elif provider == 'msg91':
        code = f'{random.randint(100000, 999999)}'
        _send_msg91(phone, code)
        session = OtpSession(
            phone=phone, user_type=user_type, otp_code=code, expires_at=expires_at
        )
    elif provider == 'twilio':
        _send_twilio(phone)  # Twilio Verify stores the code server-side
        session = OtpSession(
            phone=phone, user_type=user_type, otp_code=None, expires_at=expires_at
        )
    else:
        raise ValueError(f'Unknown OTP provider: {provider}')

    db.session.add(session)
    db.session.commit()
    return session, dev_code


def verify_otp(phone, otp, user_type):
    """Return True if the OTP is valid for this phone/user_type."""
    provider = _provider()

    if provider == 'twilio':
        if not _verify_twilio(phone, otp):
            return False
        session = (
            OtpSession.query.filter_by(phone=phone, user_type=user_type, verified=False)
            .order_by(OtpSession.created_at.desc())
            .first()
        )
        if session:
            session.verified = True
            db.session.commit()
        return True

    # mock / msg91 — compare stored code
    session = (
        OtpSession.query.filter_by(phone=phone, user_type=user_type, verified=False)
        .order_by(OtpSession.created_at.desc())
        .first()
    )
    if not session or session.expires_at < datetime.utcnow():
        return False
    if session.otp_code != str(otp).strip():
        return False
    session.verified = True
    db.session.commit()
    return True


# ── Provider integrations (only reached when configured) ──

def _send_twilio(phone):
    from twilio.rest import Client  # imported lazily
    cfg = current_app.config
    client = Client(cfg['TWILIO_ACCOUNT_SID'], cfg['TWILIO_AUTH_TOKEN'])
    client.verify.v2.services(cfg['TWILIO_VERIFY_SID']).verifications.create(
        to=f'+91{phone}', channel='sms'
    )


def _verify_twilio(phone, otp):
    from twilio.rest import Client
    cfg = current_app.config
    client = Client(cfg['TWILIO_ACCOUNT_SID'], cfg['TWILIO_AUTH_TOKEN'])
    check = client.verify.v2.services(cfg['TWILIO_VERIFY_SID']).verification_checks.create(
        to=f'+91{phone}', code=str(otp)
    )
    return check.status == 'approved'


def _send_msg91(phone, code):
    import requests
    cfg = current_app.config
    requests.post(
        'https://control.msg91.com/api/v5/otp',
        params={
            'template_id': cfg.get('MSG91_TEMPLATE_ID'),
            'mobile': f'91{phone}',
            'authkey': cfg.get('MSG91_AUTH_KEY'),
            'otp': code,
        },
        timeout=10,
    )
