import json
import uuid
from datetime import datetime

from app.extensions import db


class Provider(db.Model):
    __tablename__ = 'providers'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    phone = db.Column(db.String(15), unique=True, nullable=False, index=True)
    owner_name = db.Column(db.String(100), nullable=False)
    shop_name = db.Column(db.String(200), nullable=False)
    shop_type = db.Column(db.String(20), nullable=False)  # BARBER|SALOON|PARLOUR|UNISEX
    description = db.Column(db.Text)
    avatar_url = db.Column(db.String(500))
    cover_image_url = db.Column(db.String(500))
    portfolio_images = db.Column(db.Text)  # JSON list of urls

    # Location
    address_line = db.Column(db.String(300))
    mohalla = db.Column(db.String(100))
    city = db.Column(db.String(100), index=True)
    district = db.Column(db.String(100))
    state = db.Column(db.String(100))
    pincode = db.Column(db.String(10))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

    # Settings
    is_open = db.Column(db.Boolean, default=False)
    is_home_visit = db.Column(db.Boolean, default=False)
    home_visit_charge = db.Column(db.Float)
    is_verified = db.Column(db.Boolean, default=False)
    is_premium = db.Column(db.Boolean, default=False)
    premium_expiry = db.Column(db.DateTime)
    fcm_token = db.Column(db.String(500))

    # Business hours
    open_time = db.Column(db.String(5), default='09:00')
    close_time = db.Column(db.String(5), default='20:00')
    weekly_off = db.Column(db.String(50))  # JSON list e.g. ["SUN"]

    # Denormalised stats
    total_bookings = db.Column(db.Integer, default=0)
    rating = db.Column(db.Float, default=0.0)
    rating_count = db.Column(db.Integer, default=0)

    password_hash = db.Column(db.String(256))
    profile_complete = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    barbers = db.relationship('Barber', back_populates='provider', lazy='dynamic')
    services = db.relationship('Service', back_populates='provider', lazy='dynamic')
    bookings = db.relationship('Booking', back_populates='provider', lazy='dynamic')
    reviews = db.relationship('Review', back_populates='provider', lazy='dynamic')
    queue_tokens = db.relationship('QueueToken', back_populates='provider', lazy='dynamic')
    loyalty_cards = db.relationship('LoyaltyCard', back_populates='provider', lazy='dynamic')

    # ── JSON helpers ──
    @property
    def portfolio_list(self):
        try:
            return json.loads(self.portfolio_images) if self.portfolio_images else []
        except (ValueError, TypeError):
            return []

    @portfolio_list.setter
    def portfolio_list(self, value):
        self.portfolio_images = json.dumps(value or [])

    @property
    def weekly_off_list(self):
        try:
            return json.loads(self.weekly_off) if self.weekly_off else []
        except (ValueError, TypeError):
            return []

    @weekly_off_list.setter
    def weekly_off_list(self, value):
        self.weekly_off = json.dumps(value or [])

    def to_dict(self, distance_km=None, include_private=False):
        data = {
            'id': self.id,
            'shop_name': self.shop_name,
            'owner_name': self.owner_name,
            'shop_type': self.shop_type,
            'description': self.description,
            'avatar_url': self.avatar_url,
            'cover_image_url': self.cover_image_url,
            'portfolio_images': self.portfolio_list,
            'address_line': self.address_line,
            'mohalla': self.mohalla,
            'city': self.city,
            'district': self.district,
            'state': self.state,
            'pincode': self.pincode,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'is_open': self.is_open,
            'is_home_visit': self.is_home_visit,
            'home_visit_charge': self.home_visit_charge,
            'is_verified': self.is_verified,
            'is_premium': self.is_premium,
            'open_time': self.open_time,
            'close_time': self.close_time,
            'weekly_off': self.weekly_off_list,
            'rating': round(self.rating or 0.0, 1),
            'rating_count': self.rating_count,
            'total_bookings': self.total_bookings,
            'profile_complete': self.profile_complete,
        }
        if distance_km is not None:
            data['distance_km'] = round(distance_km, 2)
        if include_private:
            data['phone'] = self.phone
            data['premium_expiry'] = (
                self.premium_expiry.isoformat() if self.premium_expiry else None
            )
        return data
