from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity

from app.extensions import db
from app.models.barber import Barber
from app.services.upload_service import save_image
from app.utils.decorators import provider_required
from app.utils.helpers import ok, err

barbers_bp = Blueprint('barbers', __name__)


def _owned(barber_id):
    return Barber.query.filter_by(
        id=barber_id, provider_id=get_jwt_identity()
    ).first()


@barbers_bp.get('/')
@provider_required
def list_barbers():
    items = Barber.query.filter_by(provider_id=get_jwt_identity()).all()
    return ok([b.to_dict() for b in items])


@barbers_bp.post('/')
@provider_required
def create_barber():
    body = request.get_json(silent=True) or {}
    if not body.get('name'):
        return err('name is required')
    b = Barber(
        provider_id=get_jwt_identity(),
        name=body['name'],
        speciality=body.get('speciality'),
    )
    db.session.add(b)
    db.session.commit()
    return ok(b.to_dict(), message='Barber added', status=201)


@barbers_bp.put('/<barber_id>')
@provider_required
def update_barber(barber_id):
    b = _owned(barber_id)
    if not b:
        return err('Barber not found', 404)
    body = request.get_json(silent=True) or {}
    for field in ('name', 'speciality', 'is_active'):
        if field in body:
            setattr(b, field, body[field])
    db.session.commit()
    return ok(b.to_dict(), message='Updated')


@barbers_bp.delete('/<barber_id>')
@provider_required
def delete_barber(barber_id):
    b = _owned(barber_id)
    if not b:
        return err('Barber not found', 404)
    b.is_active = False
    db.session.commit()
    return ok(message='Barber deactivated')


@barbers_bp.post('/<barber_id>/photo')
@provider_required
def barber_photo(barber_id):
    b = _owned(barber_id)
    if not b:
        return err('Barber not found', 404)
    if 'image' not in request.files:
        return err('No image file (field: image)')
    try:
        b.photo_url = save_image(request.files['image'], 'barbers')
    except ValueError as e:
        return err(str(e))
    db.session.commit()
    return ok({'photo_url': b.photo_url})
