# Refactoring Playbook — `code-smells-project`

Transformation patterns for **Phase 3 (MVC Refactoring)**, mapped to the entries in `anti-pattern-catalog.md`. Every pattern starts from this project's real code. Apply exactly these transformations; where a pattern needs to be repeated for another analogous function/domain, that is stated explicitly under "Replicate for".

**Naming convention used below:** new Python module, file, and function names introduced by this refactoring are written in English (e.g., `product_model.py`, `create_product`), since they are purely internal implementation details with no effect on the outside world. Database column/table names (`nome`, `preco`, `produtos`, `usuario_id`, ...) and JSON request/response keys (`dados`, `sucesso`, `mensagem`, `erro`, ...) are kept exactly as in the original project and are **never** translated or renamed — changing them would alter the database schema and the API contract, which would violate the requirement to preserve behavior and is not something the audit asked for.

---

## PB-01 — Extract Configuration (resolves AP-01, AP-02, part of AP-17)

**Before** (`app.py:6-9,88`):
```python
app = Flask(__name__)
app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"
app.config["DEBUG"] = True
CORS(app)
...
app.run(host="0.0.0.0", port=5000, debug=True)
```

**After** (`src/config/settings.py`, new file):
```python
import os

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
HOST = os.environ.get("FLASK_HOST", "0.0.0.0")
PORT = int(os.environ.get("FLASK_PORT", "5000"))
DB_PATH = os.environ.get("DB_PATH", "loja.db")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "dev-admin-token-change-me")
```

**After** (`src/app.py`, usage):
```python
from config import settings

app = Flask(__name__)
app.config["SECRET_KEY"] = settings.SECRET_KEY
CORS(app)
...
app.run(host=settings.HOST, port=settings.PORT, debug=settings.DEBUG)
```

**Notes:** `DEBUG` now defaults to `False` (eliminates AP-02); the fallback values only exist to allow a local boot with no extra setup, but they are no longer hardcoded in the business-logic flow — the source of truth is the environment variable. `db_path` (`database.py:5`) now comes from `settings.DB_PATH`.

---

## PB-02 — Split God Modules by Domain (resolves AP-07)

**Before:** `models.py` (314 lines, 4 domains) and `controllers.py` (292 lines, 5 domains) as single files.

**After:** one file per domain under `models/` and under `controllers/`. Representative example (product domain):

`src/models/product_model.py`:
```python
from database import get_db


def _serialize_product(row):
    return {
        "id": row["id"],
        "nome": row["nome"],
        "descricao": row["descricao"],
        "preco": row["preco"],
        "estoque": row["estoque"],
        "categoria": row["categoria"],
        "ativo": row["ativo"],
        "criado_em": row["criado_em"],
    }


def list_products():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM produtos")
    return [_serialize_product(row) for row in cursor.fetchall()]


def get_product_by_id(product_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM produtos WHERE id = ?", (product_id,))
    row = cursor.fetchone()
    return _serialize_product(row) if row else None


def search_products(term, category=None, min_price=None, max_price=None):
    db = get_db()
    cursor = db.cursor()
    query = "SELECT * FROM produtos WHERE 1=1"
    params = []
    if term:
        query += " AND (nome LIKE ? OR descricao LIKE ?)"
        params.extend([f"%{term}%", f"%{term}%"])
    if category:
        query += " AND categoria = ?"
        params.append(category)
    if min_price:
        query += " AND preco >= ?"
        params.append(min_price)
    if max_price:
        query += " AND preco <= ?"
        params.append(max_price)
    cursor.execute(query, params)
    return [_serialize_product(row) for row in cursor.fetchall()]


def create_product(name, description, price, stock, category):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
        (name, description, price, stock, category),
    )
    db.commit()
    return cursor.lastrowid


def update_product(product_id, name, description, price, stock, category):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, categoria = ? WHERE id = ?",
        (name, description, price, stock, category, product_id),
    )
    db.commit()
    return True


def delete_product(product_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM produtos WHERE id = ?", (product_id,))
    db.commit()
    return True
```

**Replicate for:** `models/user_model.py` (the `get_todos_usuarios`, `get_usuario_por_id`, `login_usuario`, `criar_usuario` functions from `models.py:72-131`, also applying PB-04 and PB-05 below) and `models/order_model.py` (the order functions from `models.py:133-274`, also applying PB-09 and PB-10). The same "one file per domain" principle applies to `controllers/product_controller.py`, `controllers/user_controller.py`, `controllers/order_controller.py`, built from `controllers.py`.

**Notes:** every resulting file must have a single reason to change (the domain it represents) — no model file may contain logic belonging to another domain.

---

## PB-03 — Parameterize SQL Queries (resolves AP-04)

**Before** (`models.py:24-29`):
```python
def get_produto_por_id(id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM produtos WHERE id = " + str(id))
    row = cursor.fetchone()
```

**After:**
```python
def get_product_by_id(product_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM produtos WHERE id = ?", (product_id,))
    row = cursor.fetchone()
```

**Replicate for:** every other function listed in the AP-04 evidence (`models.py:47-50,57-61,68,92,109-111,126-129,140,148-151,155,157-166,174,188,192,220,224,279-281,289-297`) — with no exception, no data-access function in the refactored project may concatenate an input value into a SQL string.

**Special attention** — `login_usuario` (`models.py:105-111`):
```python
# Before
cursor.execute(
    "SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"
)

# After (also applies PB-04 — comparison happens against the hash)
cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,))
row = cursor.fetchone()
# password verification happens in Python against the hash, not inside the SQL — see PB-04
```

---

## PB-04 — Proper Password Hashing (resolves AP-05)

**Before** (`models.py:105-131`):
```python
def login_usuario(email, senha):
    ...
    cursor.execute("SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'")
    ...

def criar_usuario(nome, email, senha, tipo="cliente"):
    ...
    cursor.execute("INSERT INTO usuarios (nome, email, senha, tipo) VALUES ('" + nome + "', '" + email + "', '" + senha + "', '" + tipo + "')")
```

**After** (`src/models/user_model.py`, using `werkzeug.security`, already available as a transitive Flask dependency — no new library is added):
```python
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db


def create_user(name, email, password, role="cliente"):
    db = get_db()
    cursor = db.cursor()
    password_hash = generate_password_hash(password)
    cursor.execute(
        "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
        (name, email, password_hash, role),
    )
    db.commit()
    return cursor.lastrowid


def login_user(email, password):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,))
    row = cursor.fetchone()
    if row and check_password_hash(row["senha"], password):
        return {"id": row["id"], "nome": row["nome"], "email": row["email"], "tipo": row["tipo"]}
    return None
```

**Notes:** existing seed data (`database.py:76-79`, plain-text passwords such as `"admin123"`) needs to be rewritten using `generate_password_hash` at seed time, or login will stop working for those users — handle this explicitly during Phase 3 (regenerate the seed with hashed passwords) and document the change in the final summary.

---

## PB-05 — Remove Sensitive Fields from Responses (resolves AP-06)

**Before** (`models.py:72-87`):
```python
def get_todos_usuarios():
    ...
    result.append({
        "id": row["id"], "nome": row["nome"], "email": row["email"],
        "senha": row["senha"], "tipo": row["tipo"], "criado_em": row["criado_em"]
    })
```

**After:**
```python
def _serialize_user(row):
    return {
        "id": row["id"],
        "nome": row["nome"],
        "email": row["email"],
        "tipo": row["tipo"],
        "criado_em": row["criado_em"],
    }
    # the "senha" field is never included in a serialization meant for an HTTP response
```

**Before** (`controllers.py:276-290`, `health_check`):
```python
return jsonify({
    "status": "ok", "database": "connected",
    "counts": {...}, "versao": "1.0.0", "ambiente": "producao",
    "db_path": "loja.db", "debug": True,
    "secret_key": "minha-chave-super-secreta-123"
}), 200
```

**After:**
```python
return jsonify({
    "dados": {"status": "ok", "database": "connected", "counts": counts, "versao": "1.0.0"},
    "sucesso": True,
}), 200
```

**Notes:** no configuration secret (`SECRET_KEY`, tokens) or user credential may, under any circumstance, appear in an HTTP response body.

---

## PB-06 — Admin Routes: Go Through a Model + Require a Token (resolves AP-03, AP-08 on the `/admin/*` routes)

**Before** (`app.py:47-78`):
```python
@app.route("/admin/reset-db", methods=["POST"])
def reset_database():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM itens_pedido")
    ...

@app.route("/admin/query", methods=["POST"])
def executar_query():
    dados = request.get_json()
    query = dados.get("sql", "")
    ...
    cursor.execute(query)
```

**After** (`src/middlewares/admin_auth.py`):
```python
from functools import wraps
from flask import request, jsonify
from config import settings


def require_admin_token(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        token = request.headers.get("X-Admin-Token")
        if token != settings.ADMIN_TOKEN:
            return jsonify({"erro": "Acesso negado", "sucesso": False}), 401
        return view_func(*args, **kwargs)
    return wrapper
```

**After** (`src/models/admin_model.py`):
```python
from database import get_db


def reset_all_tables():
    db = get_db()
    cursor = db.cursor()
    for table in ("itens_pedido", "pedidos", "produtos", "usuarios"):
        cursor.execute(f"DELETE FROM {table}")
    db.commit()


def execute_admin_query(sql):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(sql)
    if sql.strip().upper().startswith("SELECT"):
        rows = cursor.fetchall()
        return {"rows": [dict(row) for row in rows]}
    db.commit()
    return {"rows": None}
```

**After** (`src/controllers/admin_controller.py`):
```python
from flask import request, jsonify
from models import admin_model


def reset_database():
    admin_model.reset_all_tables()
    return jsonify({"mensagem": "Banco de dados resetado", "sucesso": True}), 200


def execute_query():
    data = request.get_json()
    sql = data.get("sql", "") if data else ""
    if not sql:
        return jsonify({"erro": "Query não informada", "sucesso": False}), 400
    try:
        result = admin_model.execute_admin_query(sql)
        return jsonify({"dados": result, "sucesso": True}), 200
    except Exception:
        # unexpected DB errors are handled by the central error handler (PB-12);
        # this except only covers malformed SQL supplied by the caller, which is
        # an expected/validatable outcome, not an internal server error.
        return jsonify({"erro": "SQL inválido", "sucesso": False}), 400
```

**After** (`src/views/admin_routes.py`):
```python
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
```

**Notes on `/admin/query`:** this endpoint used to run arbitrary SQL coming from the request — the audit classified this as CRITICAL exactly for that reason (unrestricted command execution, not just missing authentication). Adding the token guard mitigates unauthorized access, but the ability to run arbitrary SQL remains a risk surface even when authenticated. Keep the endpoint functional (compatibility) but protected by the same `require_admin_token`, and explicitly document in the Phase 3 summary that this endpoint is still a high-risk administrative tool and should be removed or replaced with specific operations in a future iteration — that redesign is out of scope for this refactoring (do not introduce a new SQL-sandboxing mechanism, which would be functionality not required by the challenge).

---

## PB-07 — Route `/health` Through the Model (resolves the rest of AP-08)

**Before** (`controllers.py:264-292`): `health_check` calls `get_db()` directly.

**After** (`src/models/admin_model.py`, add):
```python
def get_counts():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM produtos")
    products = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM pedidos")
    orders = cursor.fetchone()[0]
    return {"produtos": products, "usuarios": users, "pedidos": orders}
```

`src/controllers/admin_controller.py` (add):
```python
def health_check():
    try:
        counts = admin_model.get_counts()
        return jsonify({"dados": {"status": "ok", "database": "connected", "counts": counts}, "sucesso": True}), 200
    except Exception:
        return jsonify({"dados": {"status": "erro", "database": "disconnected"}, "sucesso": False}), 500
```

`src/views/admin_routes.py` (add, no token required — this route stays public, matching its original behavior; it exposes no sensitive data after PB-05):
```python
@admin_bp.route("/health", methods=["GET"])
def health_check_route():
    return admin_controller.health_check()
```

---

## PB-08 — Per-Request Database Connection via `flask.g` (resolves AP-09)

**Before** (`database.py:1-11`):
```python
db_connection = None
db_path = "loja.db"

def get_db():
    global db_connection
    if db_connection is None:
        db_connection = sqlite3.connect(db_path, check_same_thread=False)
        db_connection.row_factory = sqlite3.Row
        ...
    return db_connection
```

**After** (`src/database.py`):
```python
import sqlite3
from flask import g
from config import settings


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(settings.DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_schema():
    db = sqlite3.connect(settings.DB_PATH)
    db.row_factory = sqlite3.Row
    cursor = db.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            descricao TEXT,
            preco REAL,
            estoque INTEGER,
            categoria TEXT,
            ativo INTEGER DEFAULT 1,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            email TEXT UNIQUE,
            senha TEXT,
            tipo TEXT DEFAULT 'cliente',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # pedidos and itens_pedido are created with FOREIGN KEY constraints — see PB-14
    # for the exact statements; they are not repeated here to avoid two sources of
    # truth for the same schema.
    db.commit()
    db.close()
```

`src/app.py` (register the teardown and the one-time schema init):
```python
from database import close_db, init_schema

init_schema()
app.teardown_appcontext(close_db)
```

**Notes:** `init_schema()` is called once at bootstrap (outside the request cycle); `get_db()` no longer depends on mutable module-level state, and instead uses Flask's own application context (an idiomatic pattern, no new dependency). This entry shows the `produtos` and `usuarios` tables in full to avoid leaving an incomplete schema; `pedidos` and `itens_pedido` are defined once, with their final `FOREIGN KEY` clauses, in PB-14 — apply PB-14's statements inside this same `init_schema()` function rather than writing the schema twice.

---

## PB-09 — Refactor `criar_pedido`: Separate Concerns + Transaction (resolves AP-10, AP-16)

**Before** (`models.py:133-169`): a single function validates stock, calculates the total, and runs 2+N inserts, with one `commit()` at the end and no rollback.

**After** (`src/models/order_model.py`):
```python
from database import get_db


def _validate_and_calculate(cursor, items):
    total = 0
    for item in items:
        cursor.execute("SELECT * FROM produtos WHERE id = ?", (item["produto_id"],))
        product = cursor.fetchone()
        if product is None:
            return None, f"Produto {item['produto_id']} não encontrado"
        if product["estoque"] < item["quantidade"]:
            return None, f"Estoque insuficiente para {product['nome']}"
        total += product["preco"] * item["quantidade"]
    return total, None


def create_order(user_id, items):
    db = get_db()
    cursor = db.cursor()

    total, error = _validate_and_calculate(cursor, items)
    if error:
        return {"erro": error}

    try:
        cursor.execute(
            "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, 'pendente', ?)",
            (user_id, total),
        )
        order_id = cursor.lastrowid

        for item in items:
            cursor.execute("SELECT preco FROM produtos WHERE id = ?", (item["produto_id"],))
            price = cursor.fetchone()["preco"]
            cursor.execute(
                "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
                (order_id, item["produto_id"], item["quantidade"], price),
            )
            cursor.execute(
                "UPDATE produtos SET estoque = estoque - ? WHERE id = ?",
                (item["quantidade"], item["produto_id"]),
            )

        db.commit()
        return {"pedido_id": order_id, "total": total}
    except Exception:
        db.rollback()
        return {"erro": "Falha ao processar pedido, nenhuma alteração foi salva"}
```

**Notes:** validation (`_validate_and_calculate`) is isolated in its own, independently testable function; the write sequence is now wrapped in `try/except` with an explicit `rollback()`, guaranteeing that a mid-loop failure never leaves stock decremented without the matching order saved.

---

## PB-10 — Eliminate N+1 with a JOIN (resolves AP-11)

**Before** (`models.py:171-233`): one orders query + one items query per order + one product query per item, in nested loops.

**After:**
```python
def _fetch_orders(where_clause="", params=()):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        f"""
        SELECT p.id, p.usuario_id, p.status, p.total, p.criado_em,
               i.produto_id, i.quantidade, i.preco_unitario, pr.nome AS produto_nome
        FROM pedidos p
        LEFT JOIN itens_pedido i ON i.pedido_id = p.id
        LEFT JOIN produtos pr ON pr.id = i.produto_id
        {where_clause}
        ORDER BY p.id
        """,
        params,
    )
    orders = {}
    for row in cursor.fetchall():
        oid = row["id"]
        if oid not in orders:
            orders[oid] = {
                "id": oid, "usuario_id": row["usuario_id"], "status": row["status"],
                "total": row["total"], "criado_em": row["criado_em"], "itens": [],
            }
        if row["produto_id"] is not None:
            orders[oid]["itens"].append({
                "produto_id": row["produto_id"],
                "produto_nome": row["produto_nome"] or "Desconhecido",
                "quantidade": row["quantidade"],
                "preco_unitario": row["preco_unitario"],
            })
    return list(orders.values())


def get_user_orders(user_id):
    return _fetch_orders("WHERE p.usuario_id = ?", (user_id,))


def list_orders():
    return _fetch_orders()
```

**Notes:** this transformation also resolves half of PB-11 (it unifies the two previously near-identical functions into a single, reused base query).

---

## PB-11 — Deduplicate Serialization (resolves the rest of AP-12)

**Before:** the same product-dictionary assembly repeated in `models.py:9-21,30-40,302-313`.

**After:** already resolved by the centralized `_serialize_product` from PB-02 — every product-reading function now calls that single function, never rebuilding the dictionary by hand.

---

## PB-12 — Centralize Error Handling (resolves AP-13)

**Before:** the same block repeated across 15 functions in `controllers.py`:
```python
except Exception as e:
    return jsonify({"erro": str(e)}), 500
```

**After** (`src/middlewares/error_handler.py`):
```python
import logging
from flask import jsonify

logger = logging.getLogger("code_smells_project")


def register_error_handlers(app):
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        logger.exception("Unhandled error: %s", error)
        return jsonify({"erro": "Erro interno no servidor", "sucesso": False}), 500
```

`src/app.py`:
```python
from middlewares.error_handler import register_error_handlers
register_error_handlers(app)
```

**After** (controllers, `list_products` example):
```python
def list_products():
    products = product_model.list_products()
    return jsonify({"dados": products, "sucesso": True}), 200
    # no generic try/except — an unexpected exception is caught by the central error handler
```

**Notes:** business-rule validations (e.g., "product not found" → 404) remain explicit in the controller via `if`/`return` — that is not the same thing as catching a generic exception, and must be preserved.

---

## PB-13 — Consistent Validation + Email Uniqueness (resolves AP-14)

**Before:** `criar_produto` validates category (`controllers.py:52-54`); `atualizar_produto` does not.

**After** (`src/controllers/product_controller.py`):
```python
VALID_CATEGORIES = ["informatica", "moveis", "vestuario", "geral", "eletronicos", "livros"]


def _validate_category(category):
    if category not in VALID_CATEGORIES:
        return f"Categoria inválida. Válidas: {VALID_CATEGORIES}"
    return None


# applied in both create_product and update_product, with no exception
```

**Before** (`models.py:122-131`, `criar_usuario` with no duplicate check):

**After** (`src/models/user_model.py`):
```python
def email_already_registered(email):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT 1 FROM usuarios WHERE email = ?", (email,))
    return cursor.fetchone() is not None
```
Called by the controller before `create_user`, returning `409 Conflict` if the email already exists — also reinforced by the schema's `UNIQUE` constraint (PB-14/PB-08).

---

## PB-14 — Add Foreign Keys (resolves AP-15)

**Before** (`database.py:36-53`):
```python
cursor.execute("""
    CREATE TABLE IF NOT EXISTS pedidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        status TEXT DEFAULT 'pendente',
        total REAL,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS itens_pedido (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pedido_id INTEGER,
        produto_id INTEGER,
        quantidade INTEGER,
        preco_unitario REAL
    )
""")
```

**After** (added inside `init_schema()` from PB-08, right after the `produtos`/`usuarios` statements; `PRAGMA foreign_keys = ON` is already set once at the top of that same function):
```python
cursor.execute("""
    CREATE TABLE IF NOT EXISTS pedidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
        status TEXT DEFAULT 'pendente',
        total REAL,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS itens_pedido (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pedido_id INTEGER NOT NULL REFERENCES pedidos(id),
        produto_id INTEGER NOT NULL REFERENCES produtos(id),
        quantidade INTEGER,
        preco_unitario REAL
    )
""")
```
The `usuarios.email` column already gets its `UNIQUE` constraint directly in PB-08's version of `init_schema()`.

**Notes:** `PRAGMA foreign_keys = ON` is required because SQLite does not enforce FKs by default even when they are declared — without that pragma, the constraint would be documentation only, not an enforced rule.

---

## PB-15 — Extract Business Constants (resolves the rest of AP-17)

**Before** (`models.py:256-262`):
```python
desconto = 0
if faturamento > 10000:
    desconto = faturamento * 0.1
elif faturamento > 5000:
    desconto = faturamento * 0.05
elif faturamento > 1000:
    desconto = faturamento * 0.02
```

**After:**
```python
DISCOUNT_TIERS = [
    (10000, 0.10),
    (5000, 0.05),
    (1000, 0.02),
]


def _calculate_discount(revenue):
    for threshold, rate in DISCOUNT_TIERS:
        if revenue > threshold:
            return revenue * rate
    return 0
```

---

## PB-16 — Adopt Blueprints Consistently (resolves AP-18, routing part)

**Before** (`app.py:11-30` vs. `app.py:32,47,59`): `add_url_rule` mixed with `@app.route` in the same file.

**After:** every route is declared through a Blueprint using the `@blueprint.route(...)` decorator, per `mvc-guidelines.md`. Example (`src/views/product_routes.py`):
```python
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
```
`src/app.py` registers every blueprint: `app.register_blueprint(product_bp)`, etc. This same decorator-based shape is used for `user_routes.py`, `order_routes.py`, and `admin_routes.py` (see PB-06/PB-07) — no file registers a route any other way.

---

## PB-17 — Standardize the Response Envelope (resolves AP-18, schema part)

**Before:** `controllers.py:142` (`buscar_usuario`) omits `"sucesso"`; `health_check` uses a completely different shape.

**After:** every controller returns exactly `{"dados": ..., "sucesso": bool, "mensagem": <optional>}` — including `/health` (see PB-07). No endpoint is an exception to this contract.

---

## PB-18 — Replace `print()` with `logging` (resolves AP-19)

**Before** (`controllers.py:8`, and the other occurrences listed under AP-19):
```python
print("Listando " + str(len(produtos)) + " produtos")
```

**After:**
```python
import logging
logger = logging.getLogger("code_smells_project")
...
logger.info("Listing %d products", len(products))
```

**Replicate for:** every `print(...)` occurrence listed in the AP-19 evidence in `app.py` and `controllers.py` — including the simulated email/SMS/push messages inside `criar_pedido` (`controllers.py:208-210`), which become `logger.info` calls.

---

## Coverage

18 transformation patterns, covering the 19 catalog entries with a real finding (AP-01 through AP-19); AP-20 produces no transformation in this run because it is not applicable (no deprecated API found).
