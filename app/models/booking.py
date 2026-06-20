import uuid
from datetime import datetime

from app.extensions import db


class Booking(db.Model):
    __tablename__ = 'bookings'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    booking_no = db.Column(db.String(30), unique=True, index=True)  # SC-YYYYMMDD-0001
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    provider_id = db.Column(db.String(36), db.ForeignKey('providers.id'), nullable=False)
    barber_id = db.Column(db.String(36), db.ForeignKey('barbers.id'))

    booking_type = db.Column(db.String(20))  # APPOINTMENT|QUEUE_TOKEN|HOME_VISIT
    status = db.Column(db.String(20), default='PENDING')
    # PENDING|CONFIRMED|IN_PROGRESS|COMPLETED|CANCELLED|NO_SHOW

    scheduled_at = db.Column(db.DateTime)
    is_home_visit = db.Column(db.Boolean, default=False)
    home_address = db.Column(db.Text)

    total_amount = db.Column(db.Float, default=0.0)
    is_paid = db.Column(db.Boolean, default=False)

    style_image_url = db.Column(db.String(500))
    notes = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', back_populates='bookings')
    provider = db.relationship('Provider', back_populates='bookings')
    barber = db.relationship('Barber', back_populates='bookings')
    services = db.relationship(
        'BookingService', back_populates='booking', cascade='all, delete-orphan'
    )
    payment = db.relationship('Payment', back_populates='booking', uselist=False)
    review = db.relationship('Review', back_populates='booking', uselist=False)

    def to_dict(self, include_relations=True):
        data = {
            'id': self.id,
            'booking_no': self.booking_no,
            'user_id': self.user_id,
            'provider_id': self.provider_id,
            'barber_id': self.barber_id,
            'booking_type': self.booking_type,
            'status': self.status,
            'scheduled_at': self.scheduled_at.isoformat() if self.scheduled_at else None,
            'is_home_visit': self.is_home_visit,
            'home_address': self.home_address,
            'total_amount': self.total_amount,
            'is_paid': self.is_paid,
            'style_image_url': self.style_image_url,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        if include_relations:
            data['services'] = [bs.to_dict() for bs in self.services]
            data['provider'] = {
                'id': self.provider.id,
                'shop_name': self.provider.shop_name,
                'shop_type': self.provider.shop_type,
                'avatar_url': self.provider.avatar_url,
                'phone': self.provider.phone,
            } if self.provider else None
            data['barber'] = self.barber.to_dict() if self.barber else None
            data['user'] = {
                'id': self.user.id,
                'name': self.user.name,
                'phone': self.user.phone,
            } if self.user else None
            data['has_review'] = self.review is not None
        return data


class BookingService(db.Model):
    __tablename__ = 'booking_services'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    booking_id = db.Column(db.String(36), db.ForeignKey('bookings.id'), nullable=False)
    service_id = db.Column(db.String(36), db.ForeignKey('services.id'), nullable=False)
    price = db.Column(db.Float, nullable=False)

    booking = db.relationship('Booking', back_populates='services')
    service = db.relationship('Service', back_populates='booking_services')

    def to_dict(self):
        return {
            'id': self.id,
            'service_id': self.service_id,
            'price': self.price,
            'name': self.service.name if self.service else None,
            'name_hindi': self.service.name_hindi if self.service else None,
            'duration_min': self.service.duration_min if self.service else None,
        }
