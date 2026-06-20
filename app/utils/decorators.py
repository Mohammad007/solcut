from functools import wraps

from flask_jwt_extended import get_jwt, verify_jwt_in_request

from app.utils.helpers import err


def role_required(role):
    """Ensure the JWT belongs to the given role ('customer' or 'provider')."""
    def wrapper(fn):
        @wraps(fn)
        def decorated(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            if claims.get('role') != role:
                return err(f'{role} access required', 403)
            return fn(*args, **kwargs)
        return decorated
    return wrapper


customer_required = role_required('customer')
provider_required = role_required('provider')
