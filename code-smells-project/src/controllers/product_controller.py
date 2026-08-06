import logging

from flask import jsonify, request

from models import product_model

logger = logging.getLogger("code_smells_project")

VALID_CATEGORIES = ["informatica", "moveis", "vestuario", "geral", "eletronicos", "livros"]


def _validate_product_input(dados):
    if not dados:
        return "Dados inválidos"
    if "nome" not in dados:
        return "Nome é obrigatório"
    if "preco" not in dados:
        return "Preço é obrigatório"
    if "estoque" not in dados:
        return "Estoque é obrigatório"

    if dados["preco"] < 0:
        return "Preço não pode ser negativo"
    if dados["estoque"] < 0:
        return "Estoque não pode ser negativo"
    if len(dados["nome"]) < 2:
        return "Nome muito curto"
    if len(dados["nome"]) > 200:
        return "Nome muito longo"

    categoria = dados.get("categoria", "geral")
    if categoria not in VALID_CATEGORIES:
        return f"Categoria inválida. Válidas: {VALID_CATEGORIES}"

    return None


def list_products():
    products = product_model.list_products()
    logger.info("Listando %d produtos", len(products))
    return jsonify({"dados": products, "sucesso": True}), 200


def get_product(product_id):
    product = product_model.get_product_by_id(product_id)
    if product:
        return jsonify({"dados": product, "sucesso": True}), 200
    return jsonify({"erro": "Produto não encontrado", "sucesso": False}), 404


def create_product():
    dados = request.get_json()

    error = _validate_product_input(dados)
    if error:
        return jsonify({"erro": error, "sucesso": False}), 400

    nome = dados["nome"]
    descricao = dados.get("descricao", "")
    preco = dados["preco"]
    estoque = dados["estoque"]
    categoria = dados.get("categoria", "geral")

    product_id = product_model.create_product(nome, descricao, preco, estoque, categoria)
    logger.info("Produto criado com ID: %s", product_id)
    return jsonify({"dados": {"id": product_id}, "sucesso": True, "mensagem": "Produto criado"}), 201


def update_product(product_id):
    dados = request.get_json()

    existing = product_model.get_product_by_id(product_id)
    if not existing:
        return jsonify({"erro": "Produto não encontrado", "sucesso": False}), 404

    error = _validate_product_input(dados)
    if error:
        return jsonify({"erro": error, "sucesso": False}), 400

    nome = dados["nome"]
    descricao = dados.get("descricao", "")
    preco = dados["preco"]
    estoque = dados["estoque"]
    categoria = dados.get("categoria", "geral")

    product_model.update_product(product_id, nome, descricao, preco, estoque, categoria)
    return jsonify({"sucesso": True, "mensagem": "Produto atualizado"}), 200


def delete_product(product_id):
    product = product_model.get_product_by_id(product_id)
    if not product:
        return jsonify({"erro": "Produto não encontrado", "sucesso": False}), 404

    product_model.delete_product(product_id)
    logger.info("Produto %s deletado", product_id)
    return jsonify({"sucesso": True, "mensagem": "Produto deletado"}), 200


def search_products():
    termo = request.args.get("q", "")
    categoria = request.args.get("categoria", None)
    preco_min = request.args.get("preco_min", None)
    preco_max = request.args.get("preco_max", None)

    if preco_min:
        preco_min = float(preco_min)
    if preco_max:
        preco_max = float(preco_max)

    resultados = product_model.search_products(termo, categoria, preco_min, preco_max)
    return jsonify({"dados": resultados, "total": len(resultados), "sucesso": True}), 200
