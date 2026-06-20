import uuid
from datetime import datetime

from app.extensions import db


class OtpSession(db.Model):
    """Stores an issued OTP (mock/MSG91) until verified or expired."""
    __tablename__ = 'otp_sessions'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    phone = db.Column(db.String(15), nullable=False, index=True)
    user_type = db.Column(db.String(20), nullable=False)  # customer|provider
    otp_code = db.Column(db.String(10))  # null when provider verifies server-side (Twilio)
    expires_at = db.Column(db.DateTime, nullable=False)
    verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class OtpLog(db.Model):
    """One row per OTP send attempt — used for rate limiting per phone."""
    __tablename__ = 'otp_logs'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    phone = db.Column(db.String(15), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class TokenBlocklist(db.Model):
    """Revoked JWTs (logout)."""
    __tablename__ = 'token_blocklist'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    jti = db.Column(db.String(36), nullable=False, unique=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
