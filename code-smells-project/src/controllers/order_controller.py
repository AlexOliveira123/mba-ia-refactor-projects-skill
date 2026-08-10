import logging

from flask import jsonify, request

from models import order_model

logger = logging.getLogger("code_smells_project")

VALID_STATUSES = ["pendente", "aprovado", "enviado", "entregue", "cancelado"]


def create_order():
    dados = request.get_json()

    if not dados:
        return jsonify({"erro": "Dados inválidos", "sucesso": False}), 400

    usuario_id = dados.get("usuario_id")
    itens = dados.get("itens", [])

    if not usuario_id:
        return jsonify({"erro": "Usuario ID é obrigatório", "sucesso": False}), 400
    if not itens or len(itens) == 0:
        return jsonify({"erro": "Pedido deve ter pelo menos 1 item", "sucesso": False}), 400

    resultado = order_model.create_order(usuario_id, itens)

    if "erro" in resultado:
        return jsonify({"erro": resultado["erro"], "sucesso": False}), 400

    logger.info("ENVIANDO EMAIL: Pedido %s criado para usuario %s", resultado["pedido_id"], usuario_id)
    logger.info("ENVIANDO SMS: Seu pedido foi recebido!")
    logger.info("ENVIANDO PUSH: Novo pedido recebido pelo sistema")

    return jsonify({
        "dados": resultado,
        "sucesso": True,
        "mensagem": "Pedido criado com sucesso",
    }), 201


def list_user_orders(usuario_id):
    pedidos = order_model.get_user_orders(usuario_id)
    return jsonify({"dados": pedidos, "sucesso": True}), 200


def list_all_orders():
    pedidos = order_model.list_orders()
    return jsonify({"dados": pedidos, "sucesso": True}), 200


def update_order_status(pedido_id):
    dados = request.get_json()
    novo_status = dados.get("status", "")

    if novo_status not in VALID_STATUSES:
        return jsonify({"erro": "Status inválido", "sucesso": False}), 400

    order_model.update_order_status(pedido_id, novo_status)

    if novo_status == "aprovado":
        logger.info("NOTIFICAÇÃO: Pedido %s foi aprovado! Preparar envio.", pedido_id)
    if novo_status == "cancelado":
        logger.info("NOTIFICAÇÃO: Pedido %s cancelado. Devolver estoque.", pedido_id)

    return jsonify({"sucesso": True, "mensagem": "Status atualizado"}), 200


def sales_report():
    relatorio = order_model.sales_report()
    return jsonify({"dados": relatorio, "sucesso": True}), 200
