# Audit Report — Project 1 (`code-smells-project`)

> Output of running the `refactor-arch` Skill's Phase 1 (Project Analysis) and Phase 2 (Architecture Audit) for real against `code-smells-project`'s original, pre-refactoring source (`git show 6d1ce62`, the repository's initial commit, restored into an isolated working copy — the committed, already-refactored code in this repository was not touched). Every finding below was independently re-confirmed line-by-line against that restored code during this run, not copied from the project's manual audit (`manual-analysis-code-smells-project.md`, findings F-001 through F-028) without verification — see the note on AP-13 for one correction this re-verification produced. The corresponding standardized analysis document is `code-smells-project/project-analysis.md`.

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python
Framework:     Flask 3.1.1
Dependencies:  flask-cors 5.0.1
Domain:        E-commerce API (produtos, usuários, pedidos)
Architecture:  Monolithic and flat — 4 files split by technical type (routing/bootstrap, controllers, models, database access), no MVC layering, no config module, a single globally shared SQLite connection, and 2 administrative routes defined directly in the bootstrap file.
Source files:  4 files analyzed (app.py, controllers.py, models.py, database.py), 780 lines total
DB tables:     produtos, usuarios, pedidos, itens_pedido
================================
```

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python + Flask 3.1.1
Files:   4 analyzed | ~780 lines of code

## Summary
CRITICAL: 7 | HIGH: 3 | MEDIUM: 6 | LOW: 3

## Findings

### [CRITICAL] Hardcoded Secrets (AP-01)
File: app.py:7
Description: `app.config["SECRET_KEY"]` is assigned the literal string `"minha-chave-super-secreta-123"` directly in source code.
Impact: Anyone with repository access has the application's secret key; rotating it requires a code change and redeploy instead of an environment update.
Recommendation: See `refactoring-playbook.md` PB-01 — extract configuration to environment variables via a config module.

### [CRITICAL] Insecure Debug/Network Configuration (AP-02)
File: app.py:8, 88
Description: `app.config["DEBUG"] = True` and `app.run(host="0.0.0.0", port=5000, debug=True)` bind the server to every network interface with the interactive debugger enabled.
Impact: The Werkzeug interactive debugger becomes reachable over the network on any unhandled exception — a known path to arbitrary code execution.
Recommendation: See `refactoring-playbook.md` PB-01 — drive debug/host from environment-based configuration, defaulting to safe values.

### [CRITICAL] Missing Authentication on Sensitive/Destructive Endpoints (AP-03)
File: app.py:47-57, 59-78
Description: `POST /admin/reset-db` deletes every row from all 4 tables, and `POST /admin/query` executes arbitrary SQL taken from the request body (`request.get_json()["sql"]`) — neither route checks identity or a token before executing.
Impact: Any unauthenticated request can wipe the database or run arbitrary SQL, including reads, writes, and schema changes.
Recommendation: See `refactoring-playbook.md` PB-06 — route admin operations through a Model and require an admin token.

### [CRITICAL] SQL Injection via String Concatenation (AP-04)
File: models.py:28, 47-50, 57-61, 68, 92, 109-111, 126-129, 140, 148-151, 155, 157-166, 174, 188, 192, 220, 224, 279-281, 289-297
Description: All 16 data-access functions in `models.py` build SQL by string concatenation instead of using the `sqlite3` driver's `?` parameterized placeholders. The instance inside `login_usuario` (`models.py:105-111`) additionally has a possible authentication-bypass path.
Impact: Any user-controlled input can alter the executed SQL structure, enabling unauthorized read, modification, or deletion of data, including a possible login bypass.
Recommendation: See `refactoring-playbook.md` PB-03 — parameterize every query.

### [CRITICAL] Inadequate Password Protection (AP-05)
File: database.py:76-79; models.py:105-111, 122-131
Description: Seed users are stored with plaintext passwords, and neither `criar_usuario` nor `login_usuario` apply any hashing before writing or comparing the `senha` column.
Impact: A database leak exposes every user's password directly, with no cryptographic barrier at all.
Recommendation: See `refactoring-playbook.md` PB-04 — apply proper password hashing.

### [CRITICAL] Sensitive Data Exposure via API Response (AP-06)
File: models.py:72-87, 89-103; controllers.py:288-289
Description: `get_todos_usuarios`/`get_usuario_por_id` include the `"senha"` field in their response dictionaries, and `health_check` includes `"debug": True, "secret_key": "minha-chave-super-secreta-123"` in its JSON response.
Impact: `GET /usuarios`, `GET /usuarios/<id>`, and `GET /health` leak plaintext passwords and the application secret key to any caller, authenticated or not.
Recommendation: See `refactoring-playbook.md` PB-05 — remove sensitive fields from response payloads.

### [CRITICAL] God Module / Concentration of Responsibilities (AP-07)
File: models.py:1-314; controllers.py:1-292
Description: `models.py` concentrates data access and business rules for 4 unrelated domains (products, users, orders, order items) in 16 functions; `controllers.py` concentrates request handling for 5 domains (products, users, orders, reports, health) in 19 functions.
Impact: Any change to any domain requires touching a file shared by every other domain, with no isolation for testing or independent review.
Recommendation: See `refactoring-playbook.md` PB-02 — split God Modules by domain.

### [HIGH] Direct Database Access Bypassing the Model Layer (AP-08)
File: app.py:4, 49, 66; controllers.py:266
Description: The `/admin/reset-db` and `/admin/query` routes in `app.py`, and `health_check` in `controllers.py`, call `database.get_db()` directly instead of delegating to a `models.py` function, unlike every other route in the project.
Impact: Two inconsistent data-access paths exist in the same codebase, increasing coupling between the entry point and persistence details and making the access pattern harder to change uniformly.
Recommendation: See `refactoring-playbook.md` PB-06 (admin routes) and PB-07 (`/health`) — route all data access through the Model layer.

### [HIGH] Global Mutable State — Shared Database Connection (AP-09)
File: database.py:4, 8-10
Description: `db_connection` is a module-level variable reused via the `global` keyword inside `get_db()`, instead of a per-request connection lifecycle.
Impact: A single connection is shared across all requests and threads, with no owner boundary, complicating both concurrency reasoning and isolated testing.
Recommendation: See `refactoring-playbook.md` PB-08 — per-request database connection via `flask.g`.

### [HIGH] Business Logic Embedded in a Data-Access Function (AP-10)
File: models.py:133-169
Description: `criar_pedido` performs stock validation, total calculation, and persistence across two tables (`pedidos`, `itens_pedido`) all within a single function.
Impact: The function has multiple reasons to change (a stock rule, a calculation rule, a persistence detail) and cannot be tested in isolation from a real database.
Recommendation: See `refactoring-playbook.md` PB-09 — separate concerns and wrap the operation in a transaction.

### [MEDIUM] N+1 Query Pattern (AP-11)
File: models.py:187-199, 219-231
Description: `get_pedidos_usuario` and `get_todos_pedidos` open one additional items query per order, and one additional product query per item, instead of a single joined query.
Impact: Query count grows linearly with the number of orders and items instead of remaining constant, degrading performance as data volume grows.
Recommendation: See `refactoring-playbook.md` PB-10 — eliminate N+1 with a JOIN.

### [MEDIUM] Duplicate Code — Repeated Query/Serialization Logic (AP-12)
File: models.py:171-201 vs. 203-233; models.py:9-21, 30-40, 302-313
Description: `get_pedidos_usuario` and `get_todos_pedidos` are near-identical, and product-row serialization is repeated almost identically in 3 separate functions.
Impact: Any change to the order or product response format must be replicated manually across multiple functions, risking silent divergence.
Recommendation: See `refactoring-playbook.md` PB-02 (domain split) and PB-11 — deduplicate serialization.

### [MEDIUM] Generic/Unsafe Exception Handling (AP-13)
File: controllers.py:10-12, 21-22, 60-62, 95-96, 108-109, 125-126, 133-134, 143-144, 164-165, 185-186, **218-220**, 226-227, 234-235, 254-255, 261-262, 291-292
Description: 16 of 19 functions in `controllers.py` use `except Exception as e: return jsonify({"erro": str(e)}), 500`, returning the raw internal exception message to the client with no differentiation by error type. **Correction from this run:** the prior manual audit recorded 15 occurrences; a full re-scan of `controllers.py` during this Phase 2 execution found a 16th, at `controllers.py:218-220` (inside `criar_pedido`'s handler, `except Exception as e: print(...); return jsonify({"erro": str(e)}), 500`) — same pattern, previously missed.
Impact: Internal error details (potentially including fragments of SQL or implementation specifics) are exposed to clients, and no error is handled differently from another.
Recommendation: See `refactoring-playbook.md` PB-12 — centralize error handling.

### [MEDIUM] Missing/Inconsistent Input Validation (AP-14)
File: controllers.py:43-54 vs. 64-96; models.py:122-131; database.py:27-34
Description: `criar_produto` validates category against a fixed list, but `atualizar_produto` applies no equivalent check; `criar_usuario` does not check for duplicate emails, and the `usuarios` table has no `UNIQUE` constraint on `email`.
Impact: A product can be updated into an invalid category even though creation prevents it, and multiple users can register with the same email.
Recommendation: See `refactoring-playbook.md` PB-13 — consistent validation and email uniqueness.

### [MEDIUM] Missing Referential Integrity (AP-15)
File: database.py:37-53
Description: `pedidos.usuario_id`, `itens_pedido.pedido_id`, and `itens_pedido.produto_id` are declared as plain `INTEGER` columns with no `FOREIGN KEY` constraint.
Impact: The database cannot prevent orders or order items from referencing non-existent users or products; integrity is left entirely to application code.
Recommendation: See `refactoring-playbook.md` PB-14 — add foreign keys.

### [MEDIUM] Missing Transactional Control on Multi-Step Writes (AP-16)
File: models.py:133-169
Description: `criar_pedido` executes several sequential `INSERT`/`UPDATE` statements across two tables with a single `commit()` at the end and no explicit rollback on partial failure.
Impact: A failure partway through order creation can leave the order, its items, and product stock in an inconsistent state with no automatic recovery.
Recommendation: See `refactoring-playbook.md` PB-09 — wrap the operation in an explicit transaction with rollback.

### [LOW] Hardcoded Values — Magic Numbers & Non-Sensitive Configuration (AP-17)
File: models.py:256-262; database.py:5
Description: Discount thresholds (`10000`, `5000`, `1000`, `0.1`, `0.05`, `0.02`) are literal, unnamed values in `relatorio_vendas`, and the database file path (`"loja.db"`) is a literal in `database.py`.
Impact: A reader cannot tell whether the thresholds are arbitrary or a documented business rule without external context, and the DB path cannot be changed without editing source.
Recommendation: See `refactoring-playbook.md` PB-01 (config) and PB-15 — extract business constants.

### [LOW] Inconsistent Conventions — Routing & Response Schema (AP-18)
File: app.py:11-30 vs. 32, 47, 59; controllers.py:9, 132 vs. 276-290 vs. 142
Description: Routes are registered using both `add_url_rule` and `@app.route` in the same file, and the JSON response shape (`dados`/`sucesso` keys) is inconsistent across endpoints, notably in `health_check` and `buscar_usuario`.
Impact: Reduced predictability for anyone adding a route or consuming the API, since neither a routing convention nor a response contract is applied uniformly.
Recommendation: See `refactoring-playbook.md` PB-16 (routing) and PB-17 — standardize the response envelope.

### [LOW] Print-Based Logging (AP-19)
File: app.py:56, 83-86; controllers.py:8, 11, 57, 61, 106, 161, 179, 182, 208-210, 248, 250
Description: `print(...)` is used throughout request-handling and bootstrap code to record events, instead of a configured logger.
Impact: No log level control, no structured/persistent log destination, and no way to filter or route log output without editing source.
Recommendation: See `refactoring-playbook.md` PB-18 — replace `print()` with `logging`.

### [INFO] Deprecated API Check
Description: verification of catalog entry AP-20 — no deprecated API found. The code only uses `Flask`, `app.config`, `app.add_url_rule`, `@app.route`, `jsonify`, `request.get_json`/`request.args.get`, and `CORS(app)`, all valid and not deprecated at the declared versions (`flask==3.1.1`, `flask-cors==5.0.1`).

================================
Total: 19 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

> **Note on subsequent execution:** this run's Phase 3 (MVC refactoring) was executed and committed separately; the project's current source tree (`src/config`, `src/models`, `src/views`, `src/controllers`, `src/middlewares`) reflects that completed refactoring, not the pre-refactoring state audited above.
