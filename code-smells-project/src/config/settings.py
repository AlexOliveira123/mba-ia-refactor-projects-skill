import os

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
HOST = os.environ.get("FLASK_HOST", "0.0.0.0")
PORT = int(os.environ.get("FLASK_PORT", "5000"))
DB_PATH = os.environ.get("DB_PATH", "loja.db")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "dev-admin-token-change-me")
