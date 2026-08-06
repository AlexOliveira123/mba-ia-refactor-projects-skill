from flask import Blueprint

from controllers import admin_controller
from middlewares.admin_auth import require_admin_token

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin/reset-db", methods=["POST"])
@require_admin_token
def reset_database_route():
    return admin_controller.reset_database()


@admin_bp.route("/admin/query", methods=["POST"])
@require_admin_token
def execute_query_route():
    return admin_controller.execute_query()


@admin_bp.route("/health", methods=["GET"])
def health_check_route():
    return admin_controller.health_check()
