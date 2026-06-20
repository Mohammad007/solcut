import uuid
from datetime import datetime

from app.extensions import db


class Barber(db.Model):
    __tablename__ = 'barbers'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider_id = db.Column(db.String(36), db.ForeignKey('providers.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    speciality = db.Column(db.String(200))
    photo_url = db.Column(db.String(500))
    rating = db.Column(db.Float, default=0.0)
    rating_count = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    provider = db.relationship('Provider', back_populates='barbers')
    bookings = db.relationship('Booking', back_populates='barber')

    def to_dict(self):
        return {
            'id': self.id,
            'provider_id': self.provider_id,
            'name': self.name,
            'speciality': self.speciality,
            'photo_url': self.photo_url,
            'rating': round(self.rating or 0.0, 1),
            'rating_count': self.rating_count,
            'is_active': self.is_active,
        }
