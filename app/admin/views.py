from datetime import datetime, timedelta

from flask import (
    Blueprint, render_template, request, redirect, url_for, session,
    flash, current_app,
)

from app.extensions import db
from app.models.user import User
from app.models.provider import Provider
from app.models.booking import Booking
from app.models.payment import Payment
from app.models.queue_token import QueueToken
from app.admin.decorators import admin_required

admin_bp = Blueprint('admin', __name__, template_folder='../templates/admin')


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if (username == current_app.config['ADMIN_USERNAME']
                and password == current_app.config['ADMIN_PASSWORD']):
            session['admin_logged_in'] = True
            return redirect(url_for('admin.dashboard'))
        flash('Invalid credentials', 'danger')
    return render_template('admin/login.html')


@admin_bp.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin.login'))


@admin_bp.route('/')
@admin_required
def dashboard():
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = today.replace(day=1)

    def revenue(since):
        rows = (
            db.session.query(Payment)
            .filter(Payment.status == 'SUCCESS', Payment.created_at >= since)
            .all()
        )
        return sum(p.amount for p in rows)

    stats = {
        'total_providers': Provider.query.count(),
        'verified_providers': Provider.query.filter_by(is_verified=True).count(),
        'total_users': User.query.count(),
        'today_bookings': Booking.query.filter(Booking.created_at >= today).count(),
        'today_revenue': revenue(today),
        'month_revenue': revenue(month_start),
        'active_queues': db.session.query(QueueToken.provider_id).filter(
            QueueToken.status.in_(['WAITING', 'CALLED', 'SERVING']),
            QueueToken.created_at >= today,
        ).distinct().count(),
    }

    # Last 7 days revenue for chart
    labels, values = [], []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        nxt = day + timedelta(days=1)
        rev = sum(
            p.amount for p in Payment.query.filter(
                Payment.status == 'SUCCESS',
                Payment.created_at >= day,
                Payment.created_at < nxt,
            ).all()
        )
        labels.append(day.strftime('%d %b'))
        values.append(rev)

    return render_template(
        'admin/dashboard.html', stats=stats,
        chart_labels=labels, chart_values=values,
    )


@admin_bp.route('/providers')
@admin_required
def providers():
    q = Provider.query
    if request.args.get('city'):
        q = q.filter(Provider.city.ilike(f"%{request.args['city']}%"))
    if request.args.get('type'):
        q = q.filter(Provider.shop_type == request.args['type'].upper())
    if request.args.get('verified') == 'true':
        q = q.filter_by(is_verified=True)
    items = q.order_by(Provider.created_at.desc()).all()
    return render_template('admin/providers.html', providers=items)


@admin_bp.route('/providers/<provider_id>')
@admin_required
def provider_detail(provider_id):
    p = Provider.query.get_or_404(provider_id)
    return render_template('admin/provider_detail.html', p=p)


@admin_bp.route('/providers/<provider_id>/verify', methods=['POST'])
@admin_required
def verify_provider(provider_id):
    p = Provider.query.get_or_404(provider_id)
    p.is_verified = not p.is_verified
    db.session.commit()
    flash(f'Verification {"granted" if p.is_verified else "revoked"}', 'success')
    return redirect(url_for('admin.provider_detail', provider_id=provider_id))


@admin_bp.route('/providers/<provider_id>/premium', methods=['POST'])
@admin_required
def premium_provider(provider_id):
    p = Provider.query.get_or_404(provider_id)
    days = int(request.form.get('days', 30))
    p.is_premium = True
    p.premium_expiry = datetime.utcnow() + timedelta(days=days)
    db.session.commit()
    flash(f'Premium granted for {days} days', 'success')
    return redirect(url_for('admin.provider_detail', provider_id=provider_id))


@admin_bp.route('/users')
@admin_required
def users():
    items = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=items)


@admin_bp.route('/bookings')
@admin_required
def bookings():
    q = Booking.query
    if request.args.get('status'):
        q = q.filter_by(status=request.args['status'].upper())
    items = q.order_by(Booking.created_at.desc()).limit(500).all()
    return render_template('admin/bookings.html', bookings=items)


@admin_bp.route('/revenue')
@admin_required
def revenue():
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    labels, values = [], []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        nxt = day + timedelta(days=1)
        rev = sum(
            p.amount for p in Payment.query.filter(
                Payment.status == 'SUCCESS',
                Payment.created_at >= day, Payment.created_at < nxt,
            ).all()
        )
        labels.append(day.strftime('%d %b'))
        values.append(rev)
    total = sum(values)
    return render_template(
        'admin/revenue.html', chart_labels=labels, chart_values=values, total=total,
    )


@admin_bp.route('/queue-monitor')
@admin_required
def queue_monitor():
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    rows = (
        db.session.query(QueueToken.provider_id)
        .filter(
            QueueToken.status.in_(['WAITING', 'CALLED', 'SERVING']),
            QueueToken.created_at >= today,
        ).distinct().all()
    )
    queues = []
    for (pid,) in rows:
        provider = Provider.query.get(pid)
        waiting = QueueToken.query.filter(
            QueueToken.provider_id == pid,
            QueueToken.status == 'WAITING',
            QueueToken.created_at >= today,
        ).count()
        serving = QueueToken.query.filter(
            QueueToken.provider_id == pid,
            QueueToken.status.in_(['CALLED', 'SERVING']),
            QueueToken.created_at >= today,
        ).first()
        queues.append({
            'provider': provider,
            'waiting': waiting,
            'serving': serving,
        })
    return render_template('admin/queue_monitor.html', queues=queues)
