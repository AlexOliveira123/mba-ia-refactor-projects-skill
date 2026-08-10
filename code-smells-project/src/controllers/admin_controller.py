import logging

from flask import jsonify, request

from models import admin_model

logger = logging.getLogger("code_smells_project")


def reset_database():
    admin_model.reset_all_tables()
    logger.info("!!! BANCO DE DADOS RESETADO !!!")
    return jsonify({"mensagem": "Banco de dados resetado", "sucesso": True}), 200


def execute_query():
    dados = request.get_json()
    sql = dados.get("sql", "") if dados else ""
    if not sql:
        return jsonify({"erro": "Query não informada", "sucesso": False}), 400

    try:
        result = admin_model.execute_admin_query(sql)
        if result["rows"] is not None:
            return jsonify({"dados": result["rows"], "sucesso": True}), 200
        return jsonify({"mensagem": "Query executada", "sucesso": True}), 200
    except Exception:
        # malformed/invalid SQL supplied by the caller is an expected, validatable
        # outcome here (this endpoint's whole purpose is running caller-supplied SQL) —
        # not the same thing as an unexpected internal error, so it is not
        # delegated to the central error handler, and the raw exception text is
        # never echoed back to the caller.
        return jsonify({"erro": "SQL inválido", "sucesso": False}), 400


def health_check():
    try:
        counts = admin_model.get_counts()
        return jsonify({
            "dados": {"status": "ok", "database": "connected", "counts": counts, "versao": "1.0.0"},
            "sucesso": True,
        }), 200
    except Exception:
        return jsonify({
            "dados": {"status": "erro", "database": "disconnected"},
            "sucesso": False,
        }), 500
