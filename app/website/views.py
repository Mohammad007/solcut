import os

from flask import (
    Blueprint, render_template, abort, send_from_directory, current_app,
)

from app.models.provider import Provider
from app.models.service import Service
from app.models.barber import Barber
from app.models.review import Review

website_bp = Blueprint('website', __name__, template_folder='../templates/website')


def apk_available():
    """True if the APK has been placed on the server."""
    folder = current_app.config['DOWNLOAD_FOLDER']
    return os.path.exists(os.path.join(folder, current_app.config['APK_FILENAME']))


@website_bp.app_context_processor
def inject_download_flags():
    """Expose download availability + version to every template."""
    try:
        return {'apk_available': apk_available(),
                'app_version': current_app.config.get('APP_VERSION', '1.0')}
    except Exception:
        return {'apk_available': False, 'app_version': '1.0'}


@website_bp.route('/download/app')
def download_app():
    folder = current_app.config['DOWNLOAD_FOLDER']
    filename = current_app.config['APK_FILENAME']
    if not os.path.exists(os.path.join(folder, filename)):
        abort(404, description='App build not uploaded yet. '
                               'Place the APK at backend/downloads/.')
    return send_from_directory(
        folder, filename, as_attachment=True, download_name='SlotCut.apk',
    )


@website_bp.route('/')
def index():
    return render_template('website/index.html')


@website_bp.route('/shop/<provider_id>')
def shop(provider_id):
    p = Provider.query.get(provider_id)
    if not p:
        abort(404)
    services = Service.query.filter_by(provider_id=p.id, is_active=True).all()
    barbers = Barber.query.filter_by(provider_id=p.id, is_active=True).all()
    reviews = (
        Review.query.filter_by(provider_id=p.id)
        .order_by(Review.created_at.desc()).limit(10).all()
    )
    return render_template(
        'website/shop.html', p=p, services=services, barbers=barbers, reviews=reviews,
    )


@website_bp.route('/privacy-policy')
def privacy():
    return render_template('website/legal.html', title='Privacy Policy')


@website_bp.route('/terms-of-service')
def terms():
    return render_template('website/legal.html', title='Terms of Service')


@website_bp.route('/about')
def about():
    return render_template('website/legal.html', title='About SlotCut')


@website_bp.route('/contact')
def contact():
    return render_template('website/legal.html', title='Contact Us')
