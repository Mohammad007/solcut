from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity

from app.extensions import db
from app.models.review import Review
from app.models.booking import Booking
from app.models.provider import Provider
from app.models.barber import Barber
from app.services.upload_service import save_image
from app.services import fcm_service
from app.utils.decorators import customer_required
from app.utils.helpers import ok, err, paginate_query

reviews_bp = Blueprint('reviews', __name__)


def _recalc(entity):
    """Recompute average rating from that entity's reviews."""
    if isinstance(entity, Provider):
        rows = Review.query.filter_by(provider_id=entity.id).all()
    else:
        rows = Review.query.filter_by(barber_id=entity.id).all()
    if rows:
        entity.rating = sum(r.rating for r in rows) / len(rows)
        entity.rating_count = len(rows)
    else:
        entity.rating = 0.0
        entity.rating_count = 0


@reviews_bp.post('/')
@customer_required
def create_review():
    body = request.get_json(silent=True) or {}
    booking_id = body.get('booking_id')
    rating = body.get('rating')
    if not booking_id or rating is None:
        return err('booking_id and rating are required')
    try:
        rating = int(rating)
    except (TypeError, ValueError):
        return err('rating must be an integer 1-5')
    if not 1 <= rating <= 5:
        return err('rating must be between 1 and 5')

    booking = Booking.query.filter_by(id=booking_id, user_id=get_jwt_identity()).first()
    if not booking:
        return err('Booking not found', 404)
    if booking.status != 'COMPLETED':
        return err('You can only review a completed booking', 409)
    if Review.query.filter_by(booking_id=booking_id).first():
        return err('This booking has already been reviewed', 409)

    review = Review(
        user_id=get_jwt_identity(),
        provider_id=booking.provider_id,
        booking_id=booking_id,
        barber_id=booking.barber_id,
        rating=rating,
        comment=body.get('comment'),
    )
    db.session.add(review)
    db.session.flush()

    provider = booking.provider
    _recalc(provider)
    if booking.barber_id:
        barber = Barber.query.get(booking.barber_id)
        if barber:
            _recalc(barber)
    db.session.commit()

    if provider.fcm_token:
        fcm_service.notify_review_received(provider.fcm_token, rating, provider.shop_name)

    return ok(review.to_dict(), message='Review submitted', status=201)


@reviews_bp.post('/<review_id>/photos')
@customer_required
def add_photos(review_id):
    review = Review.query.filter_by(id=review_id, user_id=get_jwt_identity()).first()
    if not review:
        return err('Review not found', 404)
    files = request.files.getlist('images')
    if not files:
        return err('No images (field: images)')
    photos = review.photo_list
    for f in files:
        try:
            photos.append(save_image(f, 'reviews'))
        except ValueError as e:
            return err(str(e))
    review.photo_list = photos
    db.session.commit()
    return ok({'photos': photos})


@reviews_bp.get('/provider/<provider_id>')
def provider_reviews(provider_id):
    q = Review.query.filter_by(provider_id=provider_id).order_by(Review.created_at.desc())
    items, meta = paginate_query(q, request.args.get('page'), request.args.get('limit'))
    return ok([r.to_dict() for r in items], pagination=meta)
