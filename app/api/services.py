from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity

from app.extensions import db
from app.models.service import Service
from app.services.upload_service import save_image
from app.utils.decorators import provider_required
from app.utils.helpers import ok, err

services_bp = Blueprint('services', __name__)


def _owned(service_id):
    return Service.query.filter_by(
        id=service_id, provider_id=get_jwt_identity()
    ).first()


@services_bp.get('/')
@provider_required
def list_services():
    items = Service.query.filter_by(provider_id=get_jwt_identity()).all()
    return ok([s.to_dict() for s in items])


@services_bp.post('/')
@provider_required
def create_service():
    body = request.get_json(silent=True) or {}
    if not body.get('name') or body.get('price') is None or body.get('duration_min') is None:
        return err('name, price and duration_min are required')
    s = Service(
        provider_id=get_jwt_identity(),
        name=body['name'],
        name_hindi=body.get('name_hindi'),
        category=(body.get('category') or '').upper() or None,
        price=float(body['price']),
        duration_min=int(body['duration_min']),
    )
    db.session.add(s)
    db.session.commit()
    return ok(s.to_dict(), message='Service added', status=201)


@services_bp.put('/<service_id>')
@provider_required
def update_service(service_id):
    s = _owned(service_id)
    if not s:
        return err('Service not found', 404)
    body = request.get_json(silent=True) or {}
    for field in ('name', 'name_hindi', 'is_active'):
        if field in body:
            setattr(s, field, body[field])
    if 'category' in body:
        s.category = (body['category'] or '').upper() or None
    if 'price' in body:
        s.price = float(body['price'])
    if 'duration_min' in body:
        s.duration_min = int(body['duration_min'])
    db.session.commit()
    return ok(s.to_dict(), message='Updated')


@services_bp.delete('/<service_id>')
@provider_required
def delete_service(service_id):
    s = _owned(service_id)
    if not s:
        return err('Service not found', 404)
    s.is_active = False
    db.session.commit()
    return ok(message='Service deactivated')


@services_bp.post('/<service_id>/image')
@provider_required
def service_image(service_id):
    s = _owned(service_id)
    if not s:
        return err('Service not found', 404)
    if 'image' not in request.files:
        return err('No image file (field: image)')
    try:
        s.image_url = save_image(request.files['image'], 'services')
    except ValueError as e:
        return err(str(e))
    db.session.commit()
    return ok({'image_url': s.image_url})
