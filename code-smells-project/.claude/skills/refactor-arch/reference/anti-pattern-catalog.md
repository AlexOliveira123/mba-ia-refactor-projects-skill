# Anti-pattern Catalog — `code-smells-project`

This catalog is the source of truth for **Phase 2 (Architecture Audit)**. It reflects exactly the problems confirmed in the project's manual audit (`manual-analysis-code-smells-project.md`, findings F-001 through F-028). It is not a generic catalog — every entry was validated against real evidence in this project (Python/Flask, files `app.py`, `controllers.py`, `models.py`, `database.py`).

## Severity scale (fixed, do not reinterpret)

- **CRITICAL:** severe architectural or security failures that prevent correct operation, expose sensitive data (e.g., hardcoded credentials, SQL Injection), or completely violate separation of concerns (e.g., a "God Class" containing database access, complex logic, and routing in the same file).
- **HIGH:** strong violations of the MVC pattern or SOLID principles that make maintenance and testing significantly harder (e.g., heavy business logic inside Controllers, tight coupling without Dependency Injection, mutable global state across the application).
- **MEDIUM:** standardization problems, code duplication, or moderate performance bottlenecks (e.g., N+1 queries, improper middleware usage, missing validation on routes).
- **LOW:** readability improvements, poor variable naming, or "magic numbers".

Every entry below must use exactly one of these four levels. AP-20 is the only entry without a fixed default (see its own note on why, and how to classify an actual occurrence if one is ever found).

## Evidence rule (applies to every entry below)

A finding must only be reported if there is a file + line(s) citation that proves exactly the detection signal described. If the signal is not found, the entry simply produces no finding in this run — never guess, never extrapolate from another project, never assume a higher severity than the evidence supports.

---

## AP-01 — Hardcoded Secrets
**Severity:** CRITICAL
**Detection signal:** literal string assigned to a security-sensitive configuration key (`SECRET_KEY`, connection passwords, API tokens) inside `.py` source code, especially in `app.config[...]`.
**Where to look in this project:** `app.py`, assignments to `app.config`.
**Known evidence:** `app.py:7` — `app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"`.
**Known false positive to avoid:** do not report non-sensitive configuration values (e.g., a database file name) under this entry — see AP-17.

## AP-02 — Insecure Debug/Network Configuration
**Severity:** CRITICAL
**Detection signal:** `debug=True` combined with `host="0.0.0.0"` (or equivalent) in `app.run(...)`, or `app.config["DEBUG"] = True` outside an environment-controlled configuration block.
**Where to look in this project:** `app.py`, the `if __name__ == "__main__":` block and initial app configuration.
**Known evidence:** `app.py:8` (`app.config["DEBUG"] = True`) and `app.py:88` (`app.run(host="0.0.0.0", port=5000, debug=True)`).

## AP-03 — Missing Authentication on Sensitive/Destructive Endpoints
**Severity:** CRITICAL
**Detection signal:** a Flask route that performs a destructive operation (bulk DELETE) or an extremely high-privilege operation (arbitrary SQL execution coming from the request body) with no identity/token check before execution.
**Where to look in this project:** `app.py`, the `/admin/*` routes.
**Known evidence:** `app.py:47-57` (`/admin/reset-db`, wipes every table with no check) and `app.py:59-78` (`/admin/query`, runs `cursor.execute(query)` with SQL taken from `request.get_json()["sql"]`, with no check).
**Known false positive to avoid:** public read-only routes (e.g., `/produtos`, `/health`) do not qualify for this entry — missing authentication there is not, by itself, the same risk level as a destructive/administrative route; treat it as an observed fact, do not inflate severity.

## AP-04 — SQL Injection via String Concatenation
**Severity:** CRITICAL
**Detection signal:** a SQL query built by concatenating (`+` or f-string) a user-supplied variable directly into the SQL string, instead of using the `sqlite3` driver's parameterized placeholders (`?`).
**Where to look in this project:** `models.py`, every function that calls `cursor.execute(...)`.
**Known evidence:** `models.py:28,47-50,57-61,68,92,109-111,126-129,140,148-151,155,157-166,174,188,192,220,224,279-281,289-297` — none of the 16 data-access functions use parameterization.
**Aggravated impact note:** the instance inside `login_usuario` (`models.py:105-111`) has an additional impact of a possible authentication bypass — report that specific instance with an explicit "elevated risk: affects the login flow" note, while keeping the same CRITICAL severity as the rest of the entry.

## AP-05 — Inadequate Password Protection
**Severity:** CRITICAL
**Detection signal:** a user password stored and compared as plain text (with no hashing function whatsoever) in the database.
**Where to look in this project:** `database.py` (seed data), `models.py` (`criar_usuario`, `login_usuario`).
**Known evidence:** `database.py:76-79` (plain-text seed passwords) and `models.py:105-111,122-131` (no hashing call before writing or comparing `senha`).

## AP-06 — Sensitive Data Exposure via API Response
**Severity:** CRITICAL
**Detection signal:** a JSON response dictionary returned by a route includes a password field, a secret key, or any other configuration secret.
**Where to look in this project:** `models.py` (functions that build the user dictionary), `controllers.py` (`health_check`).
**Known evidence:** `models.py:72-87,89-103` (the `"senha"` field included in the dictionary returned by `get_todos_usuarios`/`get_usuario_por_id`) and `controllers.py:288-289` (`"debug": True, "secret_key": "minha-chave-super-secreta-123"` in the `GET /health` response).

## AP-07 — God Module (Concentration of Responsibilities)
**Severity:** CRITICAL
**Detection signal:** a single `.py` file concentrates data access, business rules, and/or routing for more than one unrelated business domain (e.g., products, users, and orders in the same file).
**Where to look in this project:** `models.py`, `controllers.py`.
**Known evidence:** `models.py:1-314` (16 functions for 4 domains: products, users, orders, order items) and `controllers.py:1-292` (19 functions for 5 domains: products, users, orders, reports, health).

## AP-08 — Direct Database Access Bypassing the Model Layer
**Severity:** HIGH
**Detection signal:** a file outside `models.py` (a route in `app.py` or a function in `controllers.py`) imports `database.get_db` and runs SQL directly, instead of delegating to a `models.py` function.
**Where to look in this project:** `app.py`, `controllers.py`.
**Known evidence:** `app.py:4,49,66` (the `/admin/reset-db` and `/admin/query` routes use `get_db()` directly) and `controllers.py:266` (`health_check` uses `get_db()` directly).

## AP-09 — Global Mutable State (Shared Database Connection)
**Severity:** HIGH
**Detection signal:** a database connection is stored in a module-level variable (outside any function/class) and reused via the `global` keyword, instead of a per-request lifecycle pattern.
**Where to look in this project:** `database.py`.
**Known evidence:** `database.py:4,8-10` (`db_connection = None` at module level; `global db_connection` inside `get_db()`).

## AP-10 — Business Logic Embedded in a Data-Access Function
**Severity:** HIGH
**Detection signal:** a single data-access function simultaneously performs business-rule validation, value calculation, and persistence across more than one table.
**Where to look in this project:** `models.py`.
**Known evidence:** `models.py:133-169` (`criar_pedido` validates stock, calculates the total, inserts into `pedidos` and `itens_pedido`, and updates stock — all in the same function).

## AP-11 — N+1 Query Pattern
**Severity:** MEDIUM
**Detection signal:** inside a `for` loop over the results of a query, a new query is executed per iteration (or per nested sub-iteration) to fetch related data, instead of a single query with a `JOIN`.
**Where to look in this project:** `models.py`.
**Known evidence:** `models.py:187-199,219-231` (`get_pedidos_usuario` and `get_todos_pedidos` open a new items query per order, and a new product query per item).

## AP-12 — Duplicate Code (Repeated Query/Serialization Logic)
**Severity:** MEDIUM
**Detection signal:** the same block of logic (building a response dictionary from a `row`, or a full query+loop) appears almost identically in more than one function.
**Where to look in this project:** `models.py`.
**Known evidence:** `models.py:171-201` vs. `203-233` (`get_pedidos_usuario`/`get_todos_pedidos` are nearly identical) and `models.py:9-21,30-40,302-313` (product serialization repeated 3 times).

## AP-13 — Generic/Unsafe Exception Handling
**Severity:** MEDIUM
**Detection signal:** an `except Exception as e:` block that returns `str(e)` directly in the HTTP response to the client, repeated identically across multiple functions, with no differentiated handling by error type.
**Where to look in this project:** `controllers.py`.
**Known evidence:** `controllers.py:10-12,21-22,60-62,95-96,108-109,125-126,133-134,143-144,164-165,185-186,226-227,234-235,254-255,261-262,291-292` (15 occurrences of the same pattern).

## AP-14 — Missing/Inconsistent Input Validation
**Severity:** MEDIUM
**Detection signal:** (a) a validation rule applied when creating an entity is absent when updating the same entity; or (b) a field with an implicit uniqueness constraint (e.g., email) is not checked for duplicates before insertion, and the schema does not enforce `UNIQUE`.
**Where to look in this project:** `controllers.py` (compare `criar_produto` vs. `atualizar_produto`), `models.py`/`database.py` (`criar_usuario`, `usuarios` schema).
**Known evidence:** `controllers.py:43-54` (category validation in `criar_produto`) is absent from `controllers.py:64-96` (`atualizar_produto`); `models.py:122-131` has no duplicate-email check, `database.py:27-34` has no `UNIQUE` on `email`.

## AP-15 — Missing Referential Integrity
**Severity:** MEDIUM
**Detection signal:** a column that stores another table's ID (name ending in `_id`, used in implicit joins in the code) is declared as a plain `INTEGER` in `CREATE TABLE`, with no `FOREIGN KEY`/`REFERENCES` clause.
**Where to look in this project:** `database.py`.
**Known evidence:** `database.py:37-53` (`pedidos.usuario_id`, `itens_pedido.pedido_id`, `itens_pedido.produto_id` with no `FOREIGN KEY`).

## AP-16 — Missing Transactional Control on Multi-Step Writes
**Severity:** MEDIUM
**Detection signal:** a function executes multiple sequential `INSERT`/`UPDATE` statements across more than one table with a single `commit()` at the end, with no explicit `try/except`/rollback covering that write block.
**Where to look in this project:** `models.py`.
**Known evidence:** `models.py:133-169` (`criar_pedido` — the same function as AP-10, but the signal here is specifically the absence of a rollback on partial failure).

## AP-17 — Hardcoded Values (Magic Numbers & Non-Sensitive Configuration)
**Severity:** LOW
**Detection signal:** a numeric or string literal with no name/constant, carrying a business rule or a non-sensitive configuration value (e.g., a file path), repeated or used without explanation in the middle of a function.
**Where to look in this project:** `models.py` (discount thresholds), `database.py` (database path).
**Known evidence:** `models.py:256-262` (`10000`, `5000`, `1000`, `0.1`, `0.05`, `0.02`) and `database.py:5` (`db_path = "loja.db"`).

## AP-18 — Inconsistent Conventions (Routing & Response Schema)
**Severity:** LOW
**Detection signal:** (a) more than one Flask route-registration convention used in the same file (`add_url_rule` mixed with `@app.route`); or (b) the JSON response dictionary shape varies between endpoints that should follow the same contract (inconsistent presence/absence of keys such as `sucesso`/`dados`).
**Where to look in this project:** `app.py` (routes), `controllers.py` (response shapes).
**Known evidence:** `app.py:11-30` (`add_url_rule`) vs. `app.py:32,47,59` (`@app.route`); `controllers.py:9,132` (`{"dados":..., "sucesso":...}`) vs. `controllers.py:276-290` (`health_check`, a completely different shape) vs. `controllers.py:142` (`buscar_usuario`, missing `sucesso`).

## AP-19 — Print-Based Logging
**Severity:** LOW
**Detection signal:** use of `print(...)` inside a request-handling or bootstrap function to record events/errors, instead of a configured logger.
**Where to look in this project:** `app.py`, `controllers.py`.
**Known evidence:** `app.py:56,83-86` and `controllers.py:8,11,57,61,106,161,179,182,208-210,248,250`.

## AP-20 — Deprecated API Usage
**Severity:** not fixed in advance — this entry is a mandatory verification step, not a pre-classified problem. If an actual occurrence is found, classify it using the same four-level scale by analogy with its concrete consequence (e.g., a removed API that breaks a security control → CRITICAL; a removed API that breaks a route → HIGH; a merely-announced deprecation with a stable replacement already available → MEDIUM). Do not report this as a fifth, separate severity tier.
**Detection signal:** use of a Flask, Werkzeug, or `flask-cors` function/attribute that is listed as removed or marked `deprecated` in the official changelog of the installed version (`requirements.txt`: `flask==3.1.1`, `flask-cors==5.0.1`).
**Where to look in this project:** every `.py` file, specifically calls to methods on the `app` or `request` objects.
**Known evidence in this project:** **none** — the code only uses `Flask`, `app.config`, `app.add_url_rule`, `@app.route`, `jsonify`, `request.get_json`/`request.args.get`, `CORS(app)`, all valid and not deprecated in the declared versions. This entry stays in the catalog because the audit process structurally requires checking this category on every run, but it must not produce a finding in this project — report it explicitly as "checked, not applicable" in the Phase 2 report, never omit the check silently.

---

## Coverage summary

20 entries — CRITICAL: 7 (AP-01 to AP-07) · HIGH: 3 (AP-08 to AP-10) · MEDIUM: 6 (AP-11 to AP-16) · LOW: 3 (AP-17 to AP-19) · structural/verification-only: 1 (AP-20, not applicable in this run). Together, they cover the entirety of the 28 findings from the manual audit (F-001 through F-028).
