# Target MVC Architecture Guidelines — `code-smells-project`

Defines the target structure for **Phase 3 (MVC Refactoring)**. The structure below is the only one accepted as the outcome of this project's refactoring.

## Target directory structure

```
code-smells-project/
├── src/
│   ├── config/
│   │   └── settings.py
│   ├── database.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── product_model.py
│   │   ├── user_model.py
│   │   ├── order_model.py
│   │   └── admin_model.py
│   ├── views/
│   │   ├── __init__.py
│   │   ├── product_routes.py
│   │   ├── user_routes.py
│   │   ├── order_routes.py
│   │   └── admin_routes.py
│   ├── controllers/
│   │   ├── __init__.py
│   │   ├── product_controller.py
│   │   ├── user_controller.py
│   │   ├── order_controller.py
│   │   └── admin_controller.py
│   ├── middlewares/
│   │   ├── __init__.py
│   │   ├── error_handler.py
│   │   └── admin_auth.py
│   └── app.py
├── requirements.txt
└── loja.db
```

`app.py` at the project root is kept as a small *shim* (`python app.py` keeps working, see "Execution compatibility" below) that imports and delegates to `src/app.py`.

**Retiring the old flat files:** once its logic has been fully migrated into the structure above, each original flat file must be removed, not left behind — `models.py` and `controllers.py` are exactly the God Modules this refactoring exists to eliminate (AP-07); leaving them in place alongside `src/` would recreate AP-07 as dead, duplicated code and create import ambiguity (two different modules named `models`/`controllers` reachable from the same run). Concretely:
- Delete `models.py`, `controllers.py`, and the original `database.py` at the project root after their content has a confirmed equivalent inside `src/`.
- Keep only the root `app.py` shim described above; every other piece of logic lives under `src/`.

## Responsibility of each layer

### `config/settings.py`
The only place in the project that reads environment variables and defines configuration values (replaces the hardcoded literals for `SECRET_KEY`, `DEBUG`, `HOST`, `DB_PATH` — resolves AP-01, AP-02, AP-17). No other file may contain a configuration literal.

### `database.py`
The single database-connection module. It is the only file, besides the files inside `models/`, allowed to import `sqlite3` or open a connection (resolves AP-08 and, by adopting `flask.g` + `teardown_appcontext`, also resolves AP-09 — a per-request connection instead of a mutable module-level global). Files inside `models/` call into this module; they never open a connection themselves.

### `models/*_model.py`
One file per domain (product, user, order — resolves AP-07). Each file contains **only**:
- Data-access functions (parameterized queries — resolves AP-04).
- Row-to-dictionary serialization specific to that domain, with no duplication between functions in the same file (resolves AP-12).
- No HTTP input-format validation (that is the Controller's responsibility) and no routing logic.
- `user_model.py` is responsible for hashing/verifying passwords (resolves AP-05) and must never include the password field in a dictionary meant to be serialized into an HTTP response (resolves AP-06).
- `order_model.py` must clearly separate, within the module, stock validation, total calculation, and persistence into distinct, named functions (resolves AP-10), and wrap the related sequence of writes in a transaction with an explicit rollback on failure (resolves AP-16).
- Queries that currently trigger N+1 behavior must be rewritten as a single query with a `JOIN` (resolves AP-11).

### `views/*_routes.py`
One file per domain, each defining a `flask.Blueprint` and registering its routes exclusively through the `@blueprint.route(...)` decorator — a single convention, never mixed with `add_url_rule` (resolves AP-18a). A route here **only** declares the path/HTTP method and points to the matching Controller function; it must not contain validation logic, data access, or response formatting.

### `controllers/*_controller.py`
One file per domain. Each controller function:
- Parses and validates the HTTP input (applying the same validation rule on both creation and update of the same entity — resolves AP-14).
- Calls the matching Model.
- Formats the response following **a single envelope contract** for the whole project: `{"dados": <value or null>, "sucesso": <bool>, "mensagem": <optional string>}` — every endpoint follows this shape, with no exceptions, including `/health` (resolves AP-18b).
- Must not contain a generic per-function `try/except Exception` — unexpected errors must propagate to the centralized `error_handler` (resolves AP-13); business-rule validations (e.g., "product not found") still return the appropriate HTTP status explicitly, which is not the same thing as catching a generic exception.
- `admin_controller.py` concentrates the logic currently loose in `app.py` for `/admin/reset-db` and `/admin/query`, now delegating data access to a Model (resolves AP-08) and requiring the administrative-authentication middleware (resolves AP-03).

### `middlewares/error_handler.py`
Registered via `@app.errorhandler(Exception)` in the composition root. The only place that decides the shape of an unhandled error response — always a generic 500 with a safe message (never the raw `str(exception)`), and it always logs the real error internally via `logging` (resolves AP-13, and the error-related part of AP-19).

### `middlewares/admin_auth.py`
A minimal guard for the administrative routes: validates an `X-Admin-Token` header against `ADMIN_TOKEN` read from `config/settings.py`; if missing or incorrect, it responds `401` before any data access or SQL execution happens (resolves AP-03). This is not a full user-authentication system — it is the minimal mitigation, proportional to this project's scope, for the CRITICAL problem identified in the audit (destructive/administrative endpoints with no access control whatsoever). Do not introduce login, sessions, or JWTs here — that is out of scope for this refactoring.

### `app.py` (composition root, inside `src/`)
Creates the Flask instance, loads `config/settings.py`, registers the Blueprints from `views/`, registers the `error_handler`, and starts the server using host/port/debug values from `config/settings.py`. It is the only place that knows about every piece — no layer imports any layer other than the one immediately below it (Views never import Models directly; Controllers never register routes).

## Layer dependency rules (do not violate)

```
views/        → controllers/  (a route calls a controller)
controllers/  → models/       (a controller calls a model)
models/       → database.py   (a model asks the connection module for a connection)
database.py   → nothing above it
app.py        → views/, middlewares/, config/  (composes everything)
```

No file outside `database.py` and `models/` may import `sqlite3` or open a database connection directly.

## Execution compatibility

The command documented in the project's `README.md` (`python app.py`) must keep working after the refactoring. The root `app.py` must remain a valid entry point (even if it only delegates to `src/app.py`), and the base URL `http://localhost:5000` and every original route path (`/produtos`, `/usuarios`, `/pedidos`, `/login`, `/relatorios/vendas`, `/health`, `/admin/reset-db`, `/admin/query`, `/`) must keep responding — the only acceptable contract change is one required to eliminate a CRITICAL/HIGH finding (e.g., `/admin/*` now requires the `X-Admin-Token` header; responses no longer include a password/secret).
