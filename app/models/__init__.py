"""Import all models here so Alembic/`create_all` can discover them."""
from app.models.user import User
from app.models.provider import Provider
from app.models.barber import Barber
from app.models.service import Service
from app.models.booking import Booking, BookingService
from app.models.queue_token import QueueToken
from app.models.review import Review
from app.models.payment import Payment
from app.models.loyalty_card import LoyaltyCard
from app.models.auth import OtpSession, OtpLog, TokenBlocklist

__all__ = [
    'User', 'Provider', 'Barber', 'Service', 'Booking', 'BookingService',
    'QueueToken', 'Review', 'Payment', 'LoyaltyCard',
    'OtpSession', 'OtpLog', 'TokenBlocklist',
]
