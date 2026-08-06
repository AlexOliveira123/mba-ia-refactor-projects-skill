# Target MVC Architecture Guidelines — `task-manager-api`

Defines the target structure for **Phase 3 (MVC Refactoring)**. Unlike a project with no layering at all, this refactoring is an **evolution** of an already-partial structure, not a from-scratch rebuild: `models/` is kept as-is in location and mostly in content, `routes/` is narrowed to a true View role, a new `controllers/` package is introduced, and `services/`/`utils/` are corrected — not simply preserved — based on what Phase 2 confirms is actually reachable.

## Target directory structure

```
task-manager-api/
├── app.py
├── config.py
├── database.py
├── seed.py
├── requirements.txt
├── models/
│   ├── __init__.py
│   ├── user.py
│   ├── task.py
│   └── category.py
├── controllers/
│   ├── __init__.py
│   ├── task_controller.py
│   ├── user_controller.py
│   └── report_controller.py
├── routes/
│   ├── __init__.py
│   ├── task_routes.py
│   ├── user_routes.py
│   └── report_routes.py
├── middlewares/
│   ├── __init__.py
│   ├── error_handler.py
│   └── auth.py
└── utils/
    ├── __init__.py
    └── helpers.py
```

`services/notification_service.py` and its containing `services/` package are removed — see "Removing dead code" below. `utils/helpers.py` is kept, but trimmed to only the functions and constants Phase 2 confirms have (or, after this refactoring, gain) a real call site — see the same section.

**No new entry point.** `python app.py` and `python seed.py` (in that order, per `README.md`) must keep working exactly as documented — both files stay at the project root.

## Removing dead code (do not leave it "in case it's needed")

Phase 2's catalog (AP-06, AP-07) exists specifically because this project already demonstrates that a structurally-present, disconnected module creates a false impression of functionality. Leaving it in place after a refactoring that claims to have addressed AP-06/AP-07 would repeat the exact problem the audit flagged, only now inside a "refactored" codebase instead of a legacy one:

- **`services/notification_service.py`**: delete the file and the `services/` package. Its only reachable effect today is exposing the hardcoded SMTP credential (AP-01); it implements no behavior any current route depends on. Do not wire it into the checkout/task-creation flow to "make it useful" — actually sending emails on task assignment is new observable behavior this project does not have today, and introducing it is out of scope for a refactoring that must preserve behavior.
- **`utils/helpers.py`**: keep `validate_email`, `calculate_percentage`, `format_date`, `parse_date`, and the 7 constants (`VALID_STATUSES`, `VALID_ROLES`, `MAX_TITLE_LENGTH`, `MIN_TITLE_LENGTH`, `MIN_PASSWORD_LENGTH`, `DEFAULT_PRIORITY`, `DEFAULT_COLOR`) — every one of these has a real, confirmed duplicate inline in `routes/` today (AP-07, AP-08, AP-09), so wiring them into the new `controllers/` layer both fixes the duplication and makes the module genuinely used. Remove `sanitize_string`, `generate_id`, `log_action`, `is_valid_color`, and `process_task_data` — none of these has any confirmed call site or a confirmed inline duplicate anywhere in the codebase (re-verify this at execution time before deleting each one; if a later change introduced a real caller for any of them, keep that one and note the exception in the Phase 3 summary).
- **`requirements.txt`**: remove `marshmallow` (AP-12) — wiring in a schema-validation library would mean designing new `Schema` classes, which is new validation infrastructure, not a reorganization of what already exists; that is out of scope here. Keep `python-dotenv` and actually use it (see `config.py` below) — using an already-installed dependency for the exact purpose its presence already implies is a reorganization, not new scope, and is the direct fix for AP-01/AP-12's `python-dotenv` half.

## New/changed files

### `config.py` (new)

The only place that reads `os.environ` (via `python-dotenv`'s `load_dotenv()`) and defines configuration values, replacing the literals in `app.py:11-13` (resolves AP-01's `SECRET_KEY` half and AP-12's `python-dotenv` half). Local-development fallbacks equal to the original literal values are kept so the app boots unchanged with no `.env` file present.

### `database.py`

Unchanged in content and responsibility — still exports the single `db = SQLAlchemy()` instance used by every model.

### `models/*.py`

Column definitions and relationships are unchanged. `User.to_dict()` (`models/user.py:16-25`) stops including the `password` field (resolves AP-05) — see `controllers/user_controller.py` below for the one place a hash comparison still legitimately needs raw access to `self.password`, which stays inside the model, never serialized out. `User.is_admin()` becomes a direct boolean expression (resolves AP-16). `Task.is_overdue()`, `Task.validate_status()`, `Task.validate_priority()` are unchanged in the model — what changes is that `controllers/` now actually call them (resolves AP-10).

### `controllers/*.py` (new)

One file per domain (task, user, report+category — mirroring the existing blueprint grouping, since `report_routes.py` already mixes reports and categories and no evidence suggests separating them further). Each controller function:

- Receives already-parsed input from the calling route (or parses `request.get_json()` itself — either is acceptable as long as it is not duplicated between the route and the controller).
- Validates using the real `utils/helpers.py` functions/constants kept above, called for real (resolves AP-08, AP-09, and the reachable half of AP-07).
- Calls `Task.is_overdue()` instead of reimplementing it (resolves AP-10 — the only one of the Model's own methods that finding's evidence actually covers). `Task.validate_status()`/`Task.validate_priority()` are not wired in as a substitute for the inline checks against `utils/helpers.py`'s `VALID_STATUSES` constant (see `refactoring-playbook.md` PB-07) — the audit never established these two methods as reimplemented-elsewhere findings the way it did for `is_overdue()` (H-012), so no catalog ID is claimed for them; they remain available on `Task` for future use. `User.is_admin()` gets its first real call site in this refactoring, inside the `role`-change branch described under `middlewares/auth.py` below — not because any catalog entry required it, but because it is the correct, minimal check for that specific guard (see the note there).
- Applies the **same** validation rule on equivalent create/update operations for the same entity — in particular, `update_category` gains the same `if not data: return ..., 400` guard `create_category` already has (resolves AP-14).
- Does not contain a bare `except:` or a per-function `except Exception as e:` around unexpected errors — those propagate to `middlewares/error_handler.py` (resolves AP-13); a business-rule outcome that already has a defined status in the original contract (not found → 404, validation failure → 400) is still returned explicitly, which is not the same thing as catching a generic exception.
- Never includes `password`/hash fields in a dictionary meant for an HTTP response (resolves AP-05, together with the `to_dict()` change above).

### `routes/*.py`

Narrowed to true Views: each file creates its `Blueprint` (unchanged) and registers routes via `@blueprint.route(...)` (unchanged convention, already consistent in this project — no finding requires changing it), delegating immediately to the matching controller function. A route file contains no validation, no `Model.query`/`db.session` call, and no response-dictionary construction — all of that moves to `controllers/`.

### `middlewares/error_handler.py` (new)

Registered via `@app.errorhandler(Exception)` in `app.py`. The only place that decides the shape of an unhandled-error response (a generic `500` with a safe message) and the only place that logs the real exception — replacing the inconsistent mix of bare `except:` (silent) and `except Exception as e:` (printed) found across `routes/` (resolves AP-13).

### `middlewares/auth.py` (new)

A `require_auth` decorator, a shared `get_authenticated_user_id()` helper (both built on a real, signed token via `itsdangerous.URLSafeTimedSerializer`, keyed by `config.SECRET_KEY` — `itsdangerous` is already an installed transitive dependency of Flask itself, so this adds no new library), issued by `POST /login` in place of the current `'fake-jwt-token-' + str(user.id)` (resolves AP-03's decorative-token half). `require_auth` is applied to `DELETE /tasks/<id>`, `DELETE /users/<id>`, `DELETE /categories/<id>` — proving the caller is *some* authenticated user is a sufficient, proportional guard for these. The `role`-changing branch of `PUT /users/<id>` needs a stricter check than that: `get_authenticated_user_id()` combined with `User.is_admin()` on the requester, since H-003's most severe named consequence is specifically self-granted privilege — a check that only proved "some valid token" would still let any logged-in non-admin user promote themselves, which would not actually close the finding. `get_authenticated_user_id()` exists specifically so this header-parsing/verification logic has one implementation, used by both the decorator and this inline check — duplicating it between the two would be exactly the kind of defect this project's own catalog (AP-08) exists to catch. Every other route (all `GET`s, task/category creation and update, user creation, and non-`role` fields on `PUT /users/<id>`) is left exactly as reachable as it is today.

**Why the fix is scoped to destructive/privilege-altering routes, not the whole API:** requiring a valid session on every read and every ordinary write would be a much larger behavioral change than "reorganize responsibilities, preserve behavior" — it would break every example flow in this project's own `README.md`/`seed.py` usage pattern unless a login step were prepended to all of them, which is new required client behavior, not a reorganization. This mirrors the proportionality already established for the two prior projects of this challenge (a minimal guard on the specific destructive/administrative operations named as most severe, not a full authentication system). **Comprehensive authentication across all CRUD operations remains a real, larger gap** — document it explicitly as a known, out-of-scope observation in the Phase 3 summary, exactly as AP-03's own catalog entry requires reporting the check even where it is not fully resolved.

### `app.py`

Creates the Flask app, loads `config.py` (which calls `load_dotenv()`), registers CORS with an explicit, documented origin list instead of `CORS(app)` with no arguments (resolves AP-17 — see note below), registers the 3 blueprints, registers `middlewares/error_handler.py`, and exposes a `create_tables()` function containing exactly what today sits at module level (`with app.app_context(): db.create_all()`), called only inside `if __name__ == '__main__':` (resolves AP-15).

**Preserving `seed.py`'s behavior after fixing AP-15:** today, `seed.py:2` (`from app import app, db`) relies on `db.create_all()` firing as a side effect of that import. Moving `db.create_all()` inside `app.py`'s `if __name__` guard removes that side effect for every importer, including `seed.py` — so `seed.py` must be updated to call `create_tables()` explicitly, near the top of `seed_data()`, before it deletes/inserts any row. This keeps `python seed.py` behaving exactly as before (tables exist before seeding runs) while removing the unintended side effect for any other future importer of `app.py`. Call this out explicitly in the Phase 3 summary as a required, coupled change — fixing AP-15 in `app.py` alone, without this `seed.py` update, would break `python seed.py` on a fresh database, which is a regression, not a fix.

**CORS note (AP-17):** an explicit origin allowlist is a config-level tightening with no dependency change and no route-shape change; if no legitimate origin is documented anywhere in this project (none is, at audit time), restrict to `http://localhost:3000` as the most defensible default for a locally-developed API and document this exact default in the Phase 3 summary as a decision the project owner should confirm or adjust — do not silently invent a production origin.

## Layer dependency rules (do not violate)

```
routes/        → controllers/, middlewares/auth.py    (a route calls a controller; a route decorates itself with @require_auth directly, the same way v1's admin_routes.py imported its guard at the routing layer)
controllers/   → models/, utils/, middlewares/auth.py  (a controller calls a model, a helper, and/or get_authenticated_user_id())
models/        → database.py                            (a model asks the connection module for a session)
utils/         → nothing above it                        (helpers.py has no dependency on models, routes, or controllers)
middlewares/   → config.py                               (auth.py reads SECRET_KEY; error_handler.py has no further dependency)
database.py    → nothing above it
app.py         → routes/, middlewares/, config.py, database.py, models/ (composes everything, including calling create_tables())
```

`routes/` depending directly on `middlewares/auth.py` (specifically, the `require_auth` decorator) is the one intentional exception to "routes only call controllers" — decorating a route is a routing-layer concern, not business logic, so it belongs at the point where the route itself is declared, not inside the controller it delegates to.

No file outside `database.py` and `models/` may query or write to the database directly (no `Model.query`/`db.session` call inside `routes/`, `middlewares/`, or `utils/`).

## Execution compatibility

`pip install -r requirements.txt && python seed.py && python app.py` must keep working exactly as documented in `README.md`, booting on `http://localhost:5000`. Every original route must keep existing and responding, with the following **documented contract changes** — each is required to eliminate the specific confirmed finding named next to it (three CRITICAL, one MEDIUM; this refactoring does not limit contract changes to CRITICAL findings only, it limits them to *confirmed* findings, at whatever severity):

- `POST /login` returns a real, signed token instead of `'fake-jwt-token-' + str(user.id)` (resolves AP-03's decorative-token half, CRITICAL). Existing callers that only stored/displayed the token string are unaffected; callers that parsed the old token's structure (none are documented in this project) would need to adjust.
- `DELETE /tasks/<id>`, `DELETE /users/<id>`, `DELETE /categories/<id>` now require a valid `Authorization: Bearer <token>` header obtained from `POST /login`, returning `401` without one (resolves AP-03, CRITICAL). `PUT /users/<id>` when changing `role` additionally requires the authenticated caller to already hold the `admin` role, returning `403` if authenticated but not an admin (resolves AP-03's most severe named consequence, privilege escalation, CRITICAL).
- `GET /users/<id>` and the `POST /login` response no longer include the `password` field (resolves AP-05, CRITICAL).
- `CORS` is restricted to an explicit, documented origin list instead of every origin (resolves AP-17, MEDIUM — this one is not tied to a CRITICAL finding, and is listed here anyway because it is still an observable contract change a client could notice).

No other route path, method, or response shape may change as a side effect of this refactoring. Comprehensive authentication on every route, real email delivery via a restored `NotificationService`, and adopting `marshmallow` for schema validation are all explicitly out of scope — see the corresponding notes above for why each was deliberately not done.
