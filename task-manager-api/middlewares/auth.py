from functools import wraps

from flask import current_app, jsonify, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer


def generate_token(user_id):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps({'user_id': user_id})


def verify_token(token):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        data = serializer.loads(token, max_age=86400)
        return data.get('user_id')
    except (BadSignature, SignatureExpired):
        return None


def _extract_bearer_token():
    auth_header = request.headers.get('Authorization', '')
    return auth_header[len('Bearer '):] if auth_header.startswith('Bearer ') else ''


def get_authenticated_user_id():
    """Single place that turns the current request's Authorization header into a
    verified user_id (or None). Used by both require_auth and any controller that
    needs to inspect *who* is calling, not just *whether* they are authenticated."""
    return verify_token(_extract_bearer_token())


def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user_id = get_authenticated_user_id()
        if not user_id:
            return jsonify({'error': 'Autenticação necessária'}), 401
        request.user_id = user_id
        return f(*args, **kwargs)
    return wrapper
