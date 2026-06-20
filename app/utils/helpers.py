import math
import re
from datetime import datetime

from flask import jsonify

from app.extensions import db


def ok(data=None, message=None, status=200, **extra):
    payload = {'success': True}
    if message is not None:
        payload['message'] = message
    if data is not None:
        payload['data'] = data
    payload.update(extra)
    return jsonify(payload), status


def err(message, status=400, **extra):
    payload = {'success': False, 'message': message}
    payload.update(extra)
    return jsonify(payload), status


def haversine_km(lat1, lng1, lat2, lng2):
    """Great-circle distance in kilometres."""
    if None in (lat1, lng1, lat2, lng2):
        return None
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = (math.sin(dphi / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2)
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


_PHONE_RE = re.compile(r'^[6-9]\d{9}$')


def is_valid_indian_phone(phone):
    return bool(phone and _PHONE_RE.match(str(phone).strip()))


def generate_booking_no(provider_id=None):
    """SC-YYYYMMDD-XXXX — sequential per day across all bookings."""
    from app.models.booking import Booking
    today = datetime.utcnow().strftime('%Y%m%d')
    prefix = f'SC-{today}-'
    count = (
        db.session.query(Booking)
        .filter(Booking.booking_no.like(f'{prefix}%'))
        .count()
    )
    return f'{prefix}{count + 1:04d}'


def allowed_file(filename, allowed_extensions):
    return (
        '.' in filename
        and filename.rsplit('.', 1)[1].lower() in allowed_extensions
    )


def paginate_query(query, page, limit):
    page = max(1, int(page or 1))
    limit = min(100, max(1, int(limit or 10)))
    total = query.count()
    items = query.offset((page - 1) * limit).limit(limit).all()
    return items, {
        'page': page,
        'limit': limit,
        'total': total,
        'pages': math.ceil(total / limit) if limit else 1,
    }
