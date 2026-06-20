import uuid
from datetime import datetime

from app.extensions import db


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    phone = db.Column(db.String(15), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True)
    avatar_url = db.Column(db.String(500))
    fcm_token = db.Column(db.String(500))
    preferred_lang = db.Column(db.String(5), default='hi')
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    bookings = db.relationship('Booking', back_populates='user', lazy='dynamic')
    reviews = db.relationship('Review', back_populates='user', lazy='dynamic')
    loyalty_cards = db.relationship('LoyaltyCard', back_populates='user', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'phone': self.phone,
            'name': self.name,
            'email': self.email,
            'avatar_url': self.avatar_url,
            'preferred_lang': self.preferred_lang,
            'city': self.city,
            'state': self.state,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
