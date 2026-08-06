from flask import Blueprint

from controllers import order_controller

order_bp = Blueprint("orders", __name__)


@order_bp.route("/pedidos", methods=["POST"])
def create_order_route():
    return order_controller.create_order()


@order_bp.route("/pedidos", methods=["GET"])
def list_all_orders_route():
    return order_controller.list_all_orders()


@order_bp.route("/pedidos/usuario/<int:usuario_id>", methods=["GET"])
def list_user_orders_route(usuario_id):
    return order_controller.list_user_orders(usuario_id)


@order_bp.route("/pedidos/<int:pedido_id>/status", methods=["PUT"])
def update_order_status_route(pedido_id):
    return order_controller.update_order_status(pedido_id)


@order_bp.route("/relatorios/vendas", methods=["GET"])
def sales_report_route():
    return order_controller.sales_report()
