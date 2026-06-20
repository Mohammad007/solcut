import uuid
from datetime import datetime

from app.extensions import db


class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    booking_id = db.Column(db.String(36), db.ForeignKey('bookings.id'), unique=True)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='PENDING')  # PENDING|SUCCESS|FAILED|REFUNDED
    razorpay_order_id = db.Column(db.String(100))
    razorpay_payment_id = db.Column(db.String(100))
    method = db.Column(db.String(30))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    booking = db.relationship('Booking', back_populates='payment')

    def to_dict(self):
        return {
            'id': self.id,
            'booking_id': self.booking_id,
            'amount': self.amount,
            'status': self.status,
            'razorpay_order_id': self.razorpay_order_id,
            'razorpay_payment_id': self.razorpay_payment_id,
            'method': self.method,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
