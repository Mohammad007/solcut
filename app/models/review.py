import json
import uuid
from datetime import datetime

from app.extensions import db


class Review(db.Model):
    __tablename__ = 'reviews'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    provider_id = db.Column(db.String(36), db.ForeignKey('providers.id'), nullable=False)
    booking_id = db.Column(
        db.String(36), db.ForeignKey('bookings.id'), unique=True, nullable=False
    )
    barber_id = db.Column(db.String(36), db.ForeignKey('barbers.id'))
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.Text)
    photos = db.Column(db.Text)  # JSON list of urls
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='reviews')
    provider = db.relationship('Provider', back_populates='reviews')
    booking = db.relationship('Booking', back_populates='review')

    @property
    def photo_list(self):
        try:
            return json.loads(self.photos) if self.photos else []
        except (ValueError, TypeError):
            return []

    @photo_list.setter
    def photo_list(self, value):
        self.photos = json.dumps(value or [])

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'provider_id': self.provider_id,
            'booking_id': self.booking_id,
            'rating': self.rating,
            'comment': self.comment,
            'photos': self.photo_list,
            'user_name': self.user.name if self.user else 'Anonymous',
            'user_avatar': self.user.avatar_url if self.user else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
