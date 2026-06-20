import uuid
from datetime import datetime

from app.extensions import db


class Service(db.Model):
    __tablename__ = 'services'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider_id = db.Column(db.String(36), db.ForeignKey('providers.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    name_hindi = db.Column(db.String(100))
    category = db.Column(db.String(30))  # HAIR|BEARD|SKIN|NAIL|WAXING|THREADING|FACIAL
    price = db.Column(db.Float, nullable=False)
    duration_min = db.Column(db.Integer, nullable=False)
    image_url = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    provider = db.relationship('Provider', back_populates='services')
    booking_services = db.relationship('BookingService', back_populates='service')

    def to_dict(self):
        return {
            'id': self.id,
            'provider_id': self.provider_id,
            'name': self.name,
            'name_hindi': self.name_hindi,
            'category': self.category,
            'price': self.price,
            'duration_min': self.duration_min,
            'image_url': self.image_url,
            'is_active': self.is_active,
        }
