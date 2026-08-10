from flask import Blueprint

from controllers import user_controller

user_bp = Blueprint("users", __name__)


@user_bp.route("/usuarios", methods=["GET"])
def list_users_route():
    return user_controller.list_users()


@user_bp.route("/usuarios/<int:user_id>", methods=["GET"])
def get_user_route(user_id):
    return user_controller.get_user(user_id)


@user_bp.route("/usuarios", methods=["POST"])
def create_user_route():
    return user_controller.create_user()


@user_bp.route("/login", methods=["POST"])
def login_route():
    return user_controller.login()
