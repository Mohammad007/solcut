import uuid
from datetime import datetime

from app.extensions import db


class QueueToken(db.Model):
    __tablename__ = 'queue_tokens'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider_id = db.Column(db.String(36), db.ForeignKey('providers.id'), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'))  # nullable: guest joins
    token_no = db.Column(db.Integer, nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15))
    status = db.Column(db.String(15), default='WAITING')
    # WAITING|CALLED|SERVING|DONE|SKIPPED
    estimated_wait = db.Column(db.Integer)  # minutes

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    called_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)

    provider = db.relationship('Provider', back_populates='queue_tokens')

    def to_dict(self):
        return {
            'id': self.id,
            'provider_id': self.provider_id,
            'token_no': self.token_no,
            'customer_name': self.customer_name,
            'phone': self.phone,
            'status': self.status,
            'estimated_wait': self.estimated_wait,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'called_at': self.called_at.isoformat() if self.called_at else None,
        }
