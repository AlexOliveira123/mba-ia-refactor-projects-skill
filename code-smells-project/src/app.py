import logging

from flask import Flask, jsonify
from flask_cors import CORS

from config import settings
from database import close_db, init_schema
from middlewares.error_handler import register_error_handlers
from views.admin_routes import admin_bp
from views.order_routes import order_bp
from views.product_routes import product_bp
from views.user_routes import user_bp

logger = logging.getLogger("code_smells_project")

app = Flask(__name__)
app.config["SECRET_KEY"] = settings.SECRET_KEY
CORS(app)

init_schema()
app.teardown_appcontext(close_db)

register_error_handlers(app)

app.register_blueprint(product_bp)
app.register_blueprint(user_bp)
app.register_blueprint(order_bp)
app.register_blueprint(admin_bp)


@app.route("/")
def index():
    return jsonify({
        "mensagem": "Bem-vindo à API da Loja",
        "versao": "1.0.0",
        "endpoints": {
            "produtos": "/produtos",
            "usuarios": "/usuarios",
            "pedidos": "/pedidos",
            "login": "/login",
            "relatorios": "/relatorios/vendas",
            "health": "/health",
        },
    })


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger.info("=" * 50)
    logger.info("SERVIDOR INICIADO")
    logger.info("Rodando em http://localhost:%d", settings.PORT)
    logger.info("=" * 50)
    app.run(host=settings.HOST, port=settings.PORT, debug=settings.DEBUG)


if __name__ == "__main__":
    main()
