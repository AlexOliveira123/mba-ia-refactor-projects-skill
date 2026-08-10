from functools import wraps

from flask import jsonify, request

from config import settings


def require_admin_token(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        token = request.headers.get("X-Admin-Token")
        if token != settings.ADMIN_TOKEN:
            return jsonify({"erro": "Acesso negado", "sucesso": False}), 401
        return view_func(*args, **kwargs)
    return wrapper
