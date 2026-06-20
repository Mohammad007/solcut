from flask_socketio import join_room, leave_room

from app.extensions import socketio


@socketio.on('connect')
def handle_connect():
    pass


@socketio.on('disconnect')
def handle_disconnect():
    pass


@socketio.on('join_provider_room')
def handle_join(data):
    provider_id = (data or {}).get('provider_id')
    if provider_id:
        join_room(f'provider_{provider_id}')


@socketio.on('leave_provider_room')
def handle_leave(data):
    provider_id = (data or {}).get('provider_id')
    if provider_id:
        leave_room(f'provider_{provider_id}')


# ── Server-side emit helpers (called from REST handlers) ──

def emit_queue_updated(provider_id, queue_data):
    socketio.emit('queue:updated', queue_data, room=f'provider_{provider_id}')


def emit_token_called(provider_id, token_data):
    socketio.emit('token:called', token_data, room=f'provider_{provider_id}')


def emit_shop_status(provider_id, is_open):
    socketio.emit('shop:status', {'is_open': is_open}, room=f'provider_{provider_id}')
