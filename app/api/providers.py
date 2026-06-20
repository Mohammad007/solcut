from datetime import datetime

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity

from app.extensions import db
from app.models.provider import Provider
from app.models.barber import Barber
from app.models.service import Service
from app.models.review import Review
from app.models.queue_token import QueueToken
from app.services.upload_service import save_image
from app.utils.decorators import provider_required
from app.utils.helpers import ok, err, haversine_km, paginate_query, is_valid_indian_phone

providers_bp = Blueprint('providers', __name__)


def _current_provider():
    return Provider.query.get(get_jwt_identity())


def _queue_count(provider_id):
    return QueueToken.query.filter(
        QueueToken.provider_id == provider_id,
        QueueToken.status.in_(['WAITING', 'CALLED', 'SERVING']),
    ).count()


# ──────────────────────────── PUBLIC ────────────────────────────

@providers_bp.get('/nearby')
def nearby():
    try:
        lat = float(request.args['lat'])
        lng = float(request.args['lng'])
    except (KeyError, ValueError):
        return err('lat and lng query params are required')
    radius = float(request.args.get('radius', 5))
    shop_type = request.args.get('type')
    open_only = request.args.get('open_only', '').lower() == 'true'

    q = Provider.query.filter(Provider.profile_complete.is_(True))
    if shop_type:
        q = q.filter(Provider.shop_type == shop_type.upper())
    if open_only:
        q = q.filter(Provider.is_open.is_(True))

    results = []
    for p in q.all():
        d = haversine_km(lat, lng, p.latitude, p.longitude)
        if d is None or d > radius:
            continue
        item = p.to_dict(distance_km=d)
        item['queue_count'] = _queue_count(p.id)
        results.append(item)

    results.sort(key=lambda x: x['distance_km'])
    page = max(1, int(request.args.get('page', 1)))
    limit = min(50, int(request.args.get('limit', 20)))
    start = (page - 1) * limit
    sliced = results[start:start + limit]
    return ok(sliced, pagination={
        'page': page, 'limit': limit, 'total': len(results),
    })


@providers_bp.get('/search')
def search():
    q = Provider.query.filter(Provider.profile_complete.is_(True))
    term = request.args.get('q', '').strip()
    if term:
        like = f'%{term}%'
        q = q.filter(db.or_(
            Provider.shop_name.ilike(like),
            Provider.owner_name.ilike(like),
            Provider.mohalla.ilike(like),
            Provider.city.ilike(like),
        ))
    if request.args.get('city'):
        q = q.filter(Provider.city.ilike(f"%{request.args['city']}%"))
    if request.args.get('mohalla'):
        q = q.filter(Provider.mohalla.ilike(f"%{request.args['mohalla']}%"))
    if request.args.get('type'):
        q = q.filter(Provider.shop_type == request.args['type'].upper())

    q = q.order_by(Provider.is_premium.desc(), Provider.rating.desc())
    items, meta = paginate_query(q, request.args.get('page'), request.args.get('limit'))
    out = []
    for p in items:
        d = p.to_dict()
        d['queue_count'] = _queue_count(p.id)
        out.append(d)
    return ok(out, pagination=meta)


@providers_bp.get('/<provider_id>')
def detail(provider_id):
    p = Provider.query.get(provider_id)
    if not p:
        return err('Provider not found', 404)
    data = p.to_dict()
    data['queue_count'] = _queue_count(p.id)
    data['services_count'] = p.services.filter_by(is_active=True).count()
    return ok(data)


@providers_bp.get('/<provider_id>/services')
def provider_services(provider_id):
    items = Service.query.filter_by(provider_id=provider_id, is_active=True).all()
    return ok([s.to_dict() for s in items])


@providers_bp.get('/<provider_id>/barbers')
def provider_barbers(provider_id):
    items = Barber.query.filter_by(provider_id=provider_id, is_active=True).all()
    return ok([b.to_dict() for b in items])


@providers_bp.get('/<provider_id>/reviews')
def provider_reviews(provider_id):
    q = Review.query.filter_by(provider_id=provider_id).order_by(Review.created_at.desc())
    items, meta = paginate_query(q, request.args.get('page'), request.args.get('limit'))
    return ok([r.to_dict() for r in items], pagination=meta)


@providers_bp.get('/<provider_id>/queue-status')
def queue_status(provider_id):
    from app.api.queue import build_queue_status  # reuse
    return ok(build_queue_status(provider_id))


# ──────────────────────────── PROVIDER AUTH ────────────────────────────

@providers_bp.post('/register')
@provider_required
def register():
    p = _current_provider()
    if not p:
        return err('Provider not found', 404)
    body = request.get_json(silent=True) or {}

    required = ['owner_name', 'shop_name', 'shop_type', 'address_line',
                'city', 'state', 'latitude', 'longitude']
    missing = [f for f in required if not body.get(f) and body.get(f) != 0]
    if missing:
        return err(f'Missing required fields: {", ".join(missing)}')

    if body['shop_type'].upper() not in ('SALOON', 'PARLOUR'):
        return err('shop_type must be SALOON or PARLOUR')

    for field in ('owner_name', 'shop_name', 'description', 'address_line', 'mohalla',
                  'city', 'district', 'state', 'pincode', 'open_time', 'close_time'):
        if field in body:
            setattr(p, field, body[field])
    p.shop_type = body['shop_type'].upper()
    p.latitude = float(body['latitude'])
    p.longitude = float(body['longitude'])
    if 'weekly_off' in body:
        p.weekly_off_list = body['weekly_off']
    p.profile_complete = True
    db.session.commit()
    return ok(p.to_dict(include_private=True), message='Registration complete')


@providers_bp.get('/me')
@provider_required
def get_me():
    p = _current_provider()
    if not p:
        return err('Provider not found', 404)
    return ok(p.to_dict(include_private=True))


@providers_bp.put('/me')
@provider_required
def update_me():
    p = _current_provider()
    body = request.get_json(silent=True) or {}
    editable = ['owner_name', 'shop_name', 'description', 'address_line', 'mohalla',
                'city', 'district', 'state', 'pincode']
    for field in editable:
        if field in body:
            setattr(p, field, body[field])
    if 'shop_type' in body:
        p.shop_type = body['shop_type'].upper()
    for coord in ('latitude', 'longitude'):
        if coord in body:
            setattr(p, coord, float(body[coord]))
    db.session.commit()
    return ok(p.to_dict(include_private=True), message='Updated')


@providers_bp.put('/me/status')
@provider_required
def toggle_status():
    p = _current_provider()
    body = request.get_json(silent=True) or {}
    p.is_open = bool(body.get('is_open'))
    db.session.commit()
    from app.socket_events.queue_events import emit_shop_status
    emit_shop_status(p.id, p.is_open)
    return ok({'is_open': p.is_open})


@providers_bp.put('/me/cover-image')
@provider_required
def cover_image():
    p = _current_provider()
    if 'image' not in request.files:
        return err('No image file (field: image)')
    try:
        p.cover_image_url = save_image(request.files['image'], 'covers')
    except ValueError as e:
        return err(str(e))
    db.session.commit()
    return ok({'cover_image_url': p.cover_image_url})


@providers_bp.put('/me/avatar')
@provider_required
def avatar():
    p = _current_provider()
    if 'image' not in request.files:
        return err('No image file (field: image)')
    try:
        p.avatar_url = save_image(request.files['image'], 'avatars')
    except ValueError as e:
        return err(str(e))
    db.session.commit()
    return ok({'avatar_url': p.avatar_url})


@providers_bp.post('/me/portfolio')
@provider_required
def add_portfolio():
    p = _current_provider()
    if 'image' not in request.files:
        return err('No image file (field: image)')
    try:
        url = save_image(request.files['image'], 'portfolios')
    except ValueError as e:
        return err(str(e))
    images = p.portfolio_list
    images.append(url)
    p.portfolio_list = images
    db.session.commit()
    return ok({'portfolio_images': images})


@providers_bp.delete('/me/portfolio/<int:index>')
@provider_required
def remove_portfolio(index):
    p = _current_provider()
    images = p.portfolio_list
    if index < 0 or index >= len(images):
        return err('Invalid portfolio index', 404)
    images.pop(index)
    p.portfolio_list = images
    db.session.commit()
    return ok({'portfolio_images': images})


@providers_bp.put('/me/fcm-token')
@provider_required
def update_fcm():
    p = _current_provider()
    body = request.get_json(silent=True) or {}
    p.fcm_token = body.get('fcm_token')
    db.session.commit()
    return ok(message='FCM token updated')


@providers_bp.put('/me/home-visit')
@provider_required
def home_visit():
    p = _current_provider()
    body = request.get_json(silent=True) or {}
    p.is_home_visit = bool(body.get('is_home_visit'))
    if 'home_visit_charge' in body:
        p.home_visit_charge = float(body['home_visit_charge'])
    db.session.commit()
    return ok({'is_home_visit': p.is_home_visit, 'home_visit_charge': p.home_visit_charge})


@providers_bp.put('/me/hours')
@provider_required
def hours():
    p = _current_provider()
    body = request.get_json(silent=True) or {}
    if 'open_time' in body:
        p.open_time = body['open_time']
    if 'close_time' in body:
        p.close_time = body['close_time']
    if 'weekly_off' in body:
        p.weekly_off_list = body['weekly_off']
    db.session.commit()
    return ok({
        'open_time': p.open_time, 'close_time': p.close_time,
        'weekly_off': p.weekly_off_list,
    })
