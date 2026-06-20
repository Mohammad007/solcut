"""Firebase Cloud Messaging. Falls back to console logging when not configured."""
import os

from flask import current_app

_initialized = False
_enabled = False


def init_firebase(app):
    global _initialized, _enabled
    if _initialized:
        return
    _initialized = True
    path = app.config.get('FIREBASE_CREDENTIALS_PATH')
    if not path or not os.path.exists(path):
        app.logger.warning('[FCM] credentials not found — running in MOCK mode (console only)')
        _enabled = False
        return
    try:
        import firebase_admin
        from firebase_admin import credentials
        firebase_admin.initialize_app(credentials.Certificate(path))
        _enabled = True
        app.logger.info('[FCM] Firebase initialised')
    except Exception as e:  # pragma: no cover
        app.logger.error(f'[FCM] init failed, falling back to mock: {e}')
        _enabled = False


def send_notification(fcm_token, title, body, data=None):
    if not fcm_token:
        return
    if not _enabled:
        current_app.logger.info(f'[MOCK FCM] -> {fcm_token[:12]}… | {title} | {body}')
        return
    try:
        from firebase_admin import messaging
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            token=fcm_token,
            android=messaging.AndroidConfig(priority='high'),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(aps=messaging.Aps(sound='default'))
            ),
        )
        messaging.send(message)
    except Exception as e:  # pragma: no cover
        current_app.logger.error(f'[FCM] send error: {e}')


# ── Templates ──

def notify_token_called(fcm_token, token_no, shop_name):
    send_notification(
        fcm_token,
        '🔔 Aapka number aa gaya!',
        f'Token #{token_no} — {shop_name} mein aapki baari aa rahi hai',
        {'type': 'token_called', 'token_no': str(token_no)},
    )


def notify_booking_confirmed(fcm_token, shop_name, scheduled_time):
    send_notification(
        fcm_token, '✅ Booking Confirmed!', f'{shop_name} — {scheduled_time}',
        {'type': 'booking_confirmed'},
    )


def notify_new_booking_to_provider(fcm_token, customer_name, scheduled_time):
    send_notification(
        fcm_token, '📅 Nayi Booking!',
        f'{customer_name} ne {scheduled_time} ke liye book kiya',
        {'type': 'new_booking'},
    )


def notify_review_received(fcm_token, rating, shop_name):
    send_notification(
        fcm_token, '⭐ Naya Review!', f'{shop_name} ko {rating}/5 stars mila',
        {'type': 'new_review'},
    )
