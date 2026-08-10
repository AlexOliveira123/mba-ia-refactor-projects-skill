import logging

from flask import jsonify, request

from models import user_model

logger = logging.getLogger("code_smells_project")


def list_users():
    users = user_model.list_users()
    return jsonify({"dados": users, "sucesso": True}), 200


def get_user(user_id):
    user = user_model.get_user_by_id(user_id)
    if user:
        return jsonify({"dados": user, "sucesso": True}), 200
    return jsonify({"erro": "Usuário não encontrado", "sucesso": False}), 404


def create_user():
    dados = request.get_json()

    if not dados:
        return jsonify({"erro": "Dados inválidos", "sucesso": False}), 400

    nome = dados.get("nome", "")
    email = dados.get("email", "")
    senha = dados.get("senha", "")

    if not nome or not email or not senha:
        return jsonify({"erro": "Nome, email e senha são obrigatórios", "sucesso": False}), 400

    if user_model.email_already_registered(email):
        return jsonify({"erro": "Email já cadastrado", "sucesso": False}), 409

    user_id = user_model.create_user(nome, email, senha)
    logger.info("Usuário criado: %s", email)
    return jsonify({"dados": {"id": user_id}, "sucesso": True}), 201


def login():
    dados = request.get_json()
    email = dados.get("email", "")
    senha = dados.get("senha", "")

    if not email or not senha:
        return jsonify({"erro": "Email e senha são obrigatórios", "sucesso": False}), 400

    user = user_model.login_user(email, senha)
    if user:
        logger.info("Login bem-sucedido: %s", email)
        return jsonify({"dados": user, "sucesso": True, "mensagem": "Login OK"}), 200

    logger.info("Login falhou: %s", email)
    return jsonify({"erro": "Email ou senha inválidos", "sucesso": False}), 401
