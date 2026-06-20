from datetime import datetime

from flask import Blueprint, request, current_app
from flask_jwt_extended import get_jwt_identity

from app.extensions import db
from app.models.provider import Provider
from app.models.queue_token import QueueToken
from app.models.user import User
from app.utils.decorators import provider_required
from app.utils.helpers import ok, err

queue_bp = Blueprint('queue', __name__)


def _today_start():
    now = datetime.utcnow()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _avg_service_minutes(provider):
    """Average duration (min) of the provider's active services.

    Falls back to the configured default when the provider has no services.
    """
    default = current_app.config.get('DEFAULT_AVG_SERVICE_MINUTES', 8)
    if provider is None:
        return default
    durations = [
        s.duration_min
        for s in provider.services.filter_by(is_active=True).all()
        if s.duration_min
    ]
    if not durations:
        return default
    return max(1, round(sum(durations) / len(durations)))


def build_queue_status(provider_id):
    """Shared status payload used by both this blueprint and providers blueprint."""
    today = _today_start()
    base = QueueToken.query.filter(
        QueueToken.provider_id == provider_id,
        QueueToken.created_at >= today,
    )
    serving = base.filter(QueueToken.status.in_(['CALLED', 'SERVING'])).order_by(
        QueueToken.token_no.asc()
    ).first()
    waiting = base.filter(QueueToken.status == 'WAITING').order_by(
        QueueToken.token_no.asc()
    ).all()
    provider = Provider.query.get(provider_id)
    avg = _avg_service_minutes(provider)
    last = base.order_by(QueueToken.token_no.desc()).first()
    next_token_no = (last.token_no + 1) if last else 1
    return {
        'current_serving': serving.to_dict() if serving else None,
        'waiting_list': [t.to_dict() for t in waiting],
        'waiting_count': len(waiting),
        'avg_service_min': avg,
        'estimated_wait': len(waiting) * avg,
        'next_token_no': next_token_no,
    }


def _emit(provider_id):
    from app.socket_events.queue_events import emit_queue_updated
    emit_queue_updated(provider_id, build_queue_status(provider_id))


@queue_bp.post('/join')
def join():
    body = request.get_json(silent=True) or {}
    provider_id = body.get('provider_id')
    name = (body.get('customer_name') or '').strip()
    phone = (body.get('phone') or '').strip() or None
    if not provider_id or not name:
        return err('provider_id and customer_name are required')

    provider = Provider.query.get(provider_id)
    if not provider:
        return err('Provider not found', 404)
    if not provider.is_open:
        return err('Shop is currently closed', 409)

    today = _today_start()
    last = QueueToken.query.filter(
        QueueToken.provider_id == provider_id,
        QueueToken.created_at >= today,
    ).order_by(QueueToken.token_no.desc()).first()
    next_no = (last.token_no + 1) if last else 1

    waiting_before = QueueToken.query.filter(
        QueueToken.provider_id == provider_id,
        QueueToken.created_at >= today,
        QueueToken.status.in_(['WAITING', 'CALLED', 'SERVING']),
    ).count()

    avg = _avg_service_minutes(provider)
    token = QueueToken(
        provider_id=provider_id,
        user_id=get_jwt_identity() if _maybe_user() else None,
        token_no=next_no,
        customer_name=name,
        phone=phone,
        status='WAITING',
        estimated_wait=waiting_before * avg,
    )
    db.session.add(token)
    db.session.commit()
    _emit(provider_id)

    return ok({
        'token_id': token.id,
        'token_no': next_no,
        'waiting_before_you': waiting_before,
        'estimated_wait': waiting_before * avg,
    }, message='Joined queue', status=201)


def _maybe_user():
    """Return True if a valid customer JWT is present (optional auth)."""
    try:
        from flask_jwt_extended import verify_jwt_in_request, get_jwt
        verify_jwt_in_request(optional=True)
        return get_jwt().get('role') == 'customer'
    except Exception:
        return False


@queue_bp.get('/<provider_id>')
def status(provider_id):
    return ok(build_queue_status(provider_id))


@queue_bp.post('/<provider_id>/next')
@provider_required
def next_token(provider_id):
    if provider_id != get_jwt_identity():
        return err('Forbidden', 403)
    today = _today_start()

    # Finish whoever is currently being served/called
    current = QueueToken.query.filter(
        QueueToken.provider_id == provider_id,
        QueueToken.created_at >= today,
        QueueToken.status.in_(['CALLED', 'SERVING']),
    ).order_by(QueueToken.token_no.asc()).first()
    if current:
        current.status = 'DONE'
        current.completed_at = datetime.utcnow()

    nxt = QueueToken.query.filter(
        QueueToken.provider_id == provider_id,
        QueueToken.created_at >= today,
        QueueToken.status == 'WAITING',
    ).order_by(QueueToken.token_no.asc()).first()
    if nxt:
        nxt.status = 'SERVING'
        nxt.called_at = datetime.utcnow()
    db.session.commit()

    if nxt:
        from app.socket_events.queue_events import emit_token_called
        emit_token_called(provider_id, nxt.to_dict())
        provider = Provider.query.get(provider_id)
        if nxt.user_id:
            u = User.query.get(nxt.user_id)
            if u and u.fcm_token:
                from app.services.fcm_service import notify_token_called
                notify_token_called(u.fcm_token, nxt.token_no, provider.shop_name)
    _emit(provider_id)
    return ok(build_queue_status(provider_id), message='Next called' if nxt else 'Queue empty')


@queue_bp.post('/token/<token_id>/skip')
@provider_required
def skip_token(token_id):
    t = QueueToken.query.filter_by(id=token_id, provider_id=get_jwt_identity()).first()
    if not t:
        return err('Token not found', 404)
    t.status = 'SKIPPED'
    db.session.commit()
    _emit(t.provider_id)
    return ok(message='Token skipped')


@queue_bp.post('/token/<token_id>/complete')
@provider_required
def complete_token(token_id):
    t = QueueToken.query.filter_by(id=token_id, provider_id=get_jwt_identity()).first()
    if not t:
        return err('Token not found', 404)
    t.status = 'DONE'
    t.completed_at = datetime.utcnow()
    db.session.commit()
    _emit(t.provider_id)
    return ok(message='Token completed')


@queue_bp.delete('/token/<token_id>')
def leave_queue(token_id):
    """Customer leaves the queue. No auth required (matches public join)."""
    t = QueueToken.query.get(token_id)
    if not t:
        return err('Token not found', 404)
    t.status = 'SKIPPED'
    db.session.commit()
    _emit(t.provider_id)
    return ok(message='Left queue')


@queue_bp.post('/<provider_id>/reset')
@provider_required
def reset_queue(provider_id):
    if provider_id != get_jwt_identity():
        return err('Forbidden', 403)
    today = _today_start()
    QueueToken.query.filter(
        QueueToken.provider_id == provider_id,
        QueueToken.created_at >= today,
        QueueToken.status.in_(['WAITING', 'CALLED', 'SERVING']),
    ).update({'status': 'DONE', 'completed_at': datetime.utcnow()},
             synchronize_session=False)
    db.session.commit()
    _emit(provider_id)
    return ok(message='Queue reset')
