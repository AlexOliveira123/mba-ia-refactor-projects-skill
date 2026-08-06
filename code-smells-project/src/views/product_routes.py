from flask import Blueprint

from controllers import product_controller

product_bp = Blueprint("products", __name__)


@product_bp.route("/produtos", methods=["GET"])
def list_products_route():
    return product_controller.list_products()


@product_bp.route("/produtos/busca", methods=["GET"])
def search_products_route():
    return product_controller.search_products()


@product_bp.route("/produtos/<int:product_id>", methods=["GET"])
def get_product_route(product_id):
    return product_controller.get_product(product_id)


@product_bp.route("/produtos", methods=["POST"])
def create_product_route():
    return product_controller.create_product()


@product_bp.route("/produtos/<int:product_id>", methods=["PUT"])
def update_product_route(product_id):
    return product_controller.update_product(product_id)


@product_bp.route("/produtos/<int:product_id>", methods=["DELETE"])
def delete_product_route(product_id):
    return product_controller.delete_product(product_id)
