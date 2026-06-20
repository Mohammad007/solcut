import uuid
from datetime import datetime

from app.extensions import db


class LoyaltyCard(db.Model):
    __tablename__ = 'loyalty_cards'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    provider_id = db.Column(db.String(36), db.ForeignKey('providers.id'), nullable=False)
    stamps = db.Column(db.Integer, default=0)
    milestone = db.Column(db.Integer, default=10)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', back_populates='loyalty_cards')
    provider = db.relationship('Provider', back_populates='loyalty_cards')

    __table_args__ = (db.UniqueConstraint('user_id', 'provider_id'),)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'provider_id': self.provider_id,
            'stamps': self.stamps,
            'milestone': self.milestone,
            'remaining': max(0, (self.milestone or 10) - (self.stamps or 0)),
            'provider': {
                'id': self.provider.id,
                'shop_name': self.provider.shop_name,
                'avatar_url': self.provider.avatar_url,
            } if self.provider else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
