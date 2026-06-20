from functools import wraps

from flask import session, redirect, url_for


def admin_required(fn):
    @wraps(fn)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin.login'))
        return fn(*args, **kwargs)
    return decorated
