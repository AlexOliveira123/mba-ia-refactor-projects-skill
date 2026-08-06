from flask import Blueprint

from controllers import report_controller
from middlewares.auth import require_auth

report_bp = Blueprint('reports', __name__)


@report_bp.route('/reports/summary', methods=['GET'])
def summary_report_route():
    return report_controller.summary_report()


@report_bp.route('/reports/user/<int:user_id>', methods=['GET'])
def user_report_route(user_id):
    return report_controller.user_report(user_id)


@report_bp.route('/categories', methods=['GET'])
def get_categories_route():
    return report_controller.get_categories()


@report_bp.route('/categories', methods=['POST'])
def create_category_route():
    return report_controller.create_category()


@report_bp.route('/categories/<int:cat_id>', methods=['PUT'])
def update_category_route(cat_id):
    return report_controller.update_category(cat_id)


@report_bp.route('/categories/<int:cat_id>', methods=['DELETE'])
@require_auth
def delete_category_route(cat_id):
    return report_controller.delete_category(cat_id)
