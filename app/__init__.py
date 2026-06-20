import os

from flask import Flask, send_from_directory, jsonify

from app.config import DevConfig
from app.extensions import db, migrate, jwt, socketio, cors, limiter


def create_app(config_class=DevConfig):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

    # ── Extensions ──
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    socketio.init_app(app, async_mode=app.config['SOCKETIO_ASYNC_MODE'])
    cors.init_app(app, resources={r'/api/*': {'origins': '*'}})
    limiter.init_app(app)

    # Ensure models are registered with SQLAlchemy
    from app import models  # noqa: F401

    _register_jwt_hooks(app)
    _register_blueprints(app)
    _register_misc(app)

    # SocketIO handlers
    from app import socket_events  # noqa: F401

    # FCM (mock unless credentials present)
    from app.services.fcm_service import init_firebase
    init_firebase(app)

    return app


def _register_jwt_hooks(app):
    from app.models.auth import TokenBlocklist

    @jwt.token_in_blocklist_loader
    def check_revoked(jwt_header, jwt_payload):
        jti = jwt_payload['jti']
        return TokenBlocklist.query.filter_by(jti=jti).first() is not None

    @jwt.unauthorized_loader
    def missing_token(reason):
        return jsonify({'success': False, 'message': f'Missing token: {reason}'}), 401

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return jsonify({'success': False, 'message': f'Invalid token: {reason}'}), 422

    @jwt.expired_token_loader
    def expired_token(jwt_header, jwt_payload):
        return jsonify({'success': False, 'message': 'Token expired'}), 401

    @jwt.revoked_token_loader
    def revoked_token(jwt_header, jwt_payload):
        return jsonify({'success': False, 'message': 'Token revoked'}), 401


def _register_blueprints(app):
    from app.api.auth import auth_bp
    from app.api.users import users_bp
    from app.api.providers import providers_bp
    from app.api.services import services_bp
    from app.api.barbers import barbers_bp
    from app.api.bookings import bookings_bp
    from app.api.queue import queue_bp
    from app.api.reviews import reviews_bp
    from app.api.payments import payments_bp
    from app.admin.views import admin_bp
    from app.website.views import website_bp

    app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')
    app.register_blueprint(users_bp, url_prefix='/api/v1/users')
    app.register_blueprint(providers_bp, url_prefix='/api/v1/providers')
    app.register_blueprint(services_bp, url_prefix='/api/v1/services')
    app.register_blueprint(barbers_bp, url_prefix='/api/v1/barbers')
    app.register_blueprint(bookings_bp, url_prefix='/api/v1/bookings')
    app.register_blueprint(queue_bp, url_prefix='/api/v1/queue')
    app.register_blueprint(reviews_bp, url_prefix='/api/v1/reviews')
    app.register_blueprint(payments_bp, url_prefix='/api/v1/payments')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(website_bp, url_prefix='/')


def _register_misc(app):
    @app.route('/uploads/<path:filename>')
    def uploads(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    @app.route('/api/v1/health')
    def health():
        return jsonify({'success': True, 'status': 'ok', 'service': 'slotcut-api'})

    @app.errorhandler(404)
    def not_found(e):
        from flask import request
        if request.path.startswith('/api/'):
            return jsonify({'success': False, 'message': 'Not found'}), 404
        return e, 404

    @app.errorhandler(413)
    def too_large(e):
        return jsonify({'success': False, 'message': 'File too large (max 5MB)'}), 413

    # CLI helpers
    @app.cli.command('init-db')
    def init_db():
        """Create all tables (quick start without migrations)."""
        db.create_all()
        print('Database tables created.')

    @app.cli.command('seed')
    def seed():
        """Populate demo data."""
        from app.seed import run_seed
        run_seed()
