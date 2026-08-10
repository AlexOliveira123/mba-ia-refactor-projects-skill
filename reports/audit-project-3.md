# Audit Report — Project 3 (`task-manager-api`)

> Output of running the `refactor-arch` Skill's Phase 1 (Project Analysis) and Phase 2 (Architecture Audit) for real against `task-manager-api`'s original, pre-refactoring source (`git show 6d1ce62`, the repository's initial commit, restored into an isolated working copy — the committed, already-refactored code in this repository was not touched). Every finding below was independently re-confirmed line-by-line against that restored code during this run, not copied from the project's own audit (`hypothesis-validation-task-manager-api.md`, findings H-001 through H-020) without verification — see the note on AP-13 for one correction this re-verification produced. The corresponding standardized analysis document is `task-manager-api/project-analysis.md`.
>
> This project already had a partial layered structure (`models/`, `routes/`, `services/`, `utils/`) before the audit. Per this Skill's global rules, that structure was never treated as proof of good architecture on its own — every finding below, including the ones about unused layers, is backed by an actual reachability search, not by folder names.

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python
Framework:     Flask 3.0.0, with flask-sqlalchemy 3.1.1 as the ORM layer
Dependencies:  flask-sqlalchemy, marshmallow 3.20.1 (declared, never imported), python-dotenv 1.0.0 (declared, never imported)
Domain:        Task management API (users, categories, tasks)
Architecture:  Partially layered — code is distributed across models/, routes/, services/, and utils/ packages, but reachability analysis shows a full services/ class and most of utils/ are never invoked from any entry point, and a correct Model method (Task.is_overdue()) is reimplemented manually in 5 other places instead of being reused; no dedicated controllers/ layer, request handling lives inside the route blueprints themselves.
Source files:  11 files analyzed (app.py, database.py, seed.py, models/user.py, models/task.py, models/category.py, routes/user_routes.py, routes/task_routes.py, routes/report_routes.py, services/notification_service.py, utils/helpers.py), 1,152 lines total
DB tables:     users, tasks, categories
================================
```

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python + Flask 3.0.0 / flask-sqlalchemy 3.1.1
Files:   11 analyzed | ~1,152 lines of code

## Summary
CRITICAL: 5 | HIGH: 2 | MEDIUM: 7 | LOW: 3

## Findings

### [CRITICAL] Hardcoded Secrets, Anywhere in the Codebase (AP-01)
File: app.py:13; services/notification_service.py:9-10
Description: `app.config['SECRET_KEY']` is a literal string despite `python-dotenv` already being an installed dependency; `NotificationService` holds a literal SMTP username and password, inside a class with zero references from anywhere else in the codebase.
Impact: Anyone with repository access has the Flask secret key and an SMTP credential — the fact that the SMTP-holding class is never executed does not un-expose the credential in source control.
Recommendation: See `refactoring-playbook.md` PB-01 — extract configuration via `config.py` and `python-dotenv`.

### [CRITICAL] Insecure Debug/Network Configuration (AP-02)
File: app.py:34
Description: `app.run(debug=True, host='0.0.0.0', port=5000)` binds the server to every network interface with the interactive debugger enabled.
Impact: The Werkzeug interactive debugger becomes reachable over the network on any unhandled exception.
Recommendation: See `refactoring-playbook.md` PB-01 — drive debug/host from environment-based configuration.

### [CRITICAL] Absent or Decorative Authentication/Authorization (AP-03)
File: app.py, routes/user_routes.py, routes/task_routes.py, routes/report_routes.py (all route files); routes/user_routes.py:210
Description: No route in the project checks identity, role, or token before executing — including `PUT /users/<id>`, which accepts an arbitrary `role` value with no check of the requester. `POST /login` does issue a token (`'fake-jwt-token-' + str(user.id)`), but it has no signature or expiration, and no other route in the project validates it in any form.
Impact: Every read, write, and delete operation is reachable by any anonymous caller, including a path to self-granted administrative privilege; the presence of a login flow makes this harder to diagnose, not easier, since it looks like a security control that provides no actual protection.
Recommendation: See `refactoring-playbook.md` PB-03 — real signed login token plus an auth guard on destructive/privilege-altering routes.

### [CRITICAL] Inadequate Password Hashing Algorithm (AP-04)
File: models/user.py:27-32
Description: `set_password`/`check_password` compute `hashlib.md5(pwd.encode()).hexdigest()`, with no per-user salt generated or stored anywhere in the `User` model.
Impact: MD5 is fast enough to brute-force at scale and, with no salt, produces identical hashes for identical passwords across different users.
Recommendation: See `refactoring-playbook.md` PB-04 — proper password hashing.

### [CRITICAL] Sensitive Credential Field Exposed via API Response (AP-05)
File: models/user.py:16-25; routes/user_routes.py:33, 209
Description: `User.to_dict()` includes `'password': self.password` (the MD5 hash), and is called by `GET /users/<id>` and `POST /login`, both of which expose the hash in their JSON response; `GET /users` builds its response manually and omits the field, confirming the exposure is inconsistent rather than a deliberate, uniform choice.
Impact: Combined with AP-04 (MD5, no salt) and AP-03 (no authentication), any anonymous caller can retrieve a crackable password hash for any user.
Recommendation: See `refactoring-playbook.md` PB-05 — remove password from serialization.

### [HIGH] Dead or Ignored Utility Layer (AP-07)
File: utils/helpers.py (9 functions, 7 constants); routes/report_routes.py:7, 67, 151; routes/task_routes.py:296
Description: Of 9 functions and 7 constants in `utils/helpers.py`, 7 functions and all 7 constants have zero references anywhere outside the file itself; the 2 that are imported (`format_date`, `calculate_percentage`) are never actually called — the percentage calculation is reimplemented inline instead.
Impact: A module nominally responsible for centralizing validation/formatting is systematically ignored, so the maintenance cost of the same logic is paid twice — once for the unused module, once for every inline duplicate it should have prevented.
Recommendation: See `refactoring-playbook.md` PB-07 — trim and wire up `utils/helpers.py`.

### [HIGH] Reimplementation Bypassing an Existing Model Method (AP-10)
File: models/task.py:50-60; routes/task_routes.py:30-39, 71-80; routes/user_routes.py:171-180; routes/report_routes.py:34-37, 132-135
Description: `Task.is_overdue()` correctly encapsulates the "overdue" rule, but the identical nested-conditional logic is reimplemented manually, with no call to `is_overdue()`, in 5 separate locations across 3 files.
Impact: A future change to the definition of "overdue" requires correctly updating 6 locations; missing any one of them produces a silent behavioral inconsistency between endpoints.
Recommendation: See `refactoring-playbook.md` PB-08 — reuse `Task.is_overdue()` instead of reimplementing it.

### [MEDIUM] Dead Service Layer (AP-06)
File: services/notification_service.py (entire file)
Description: `NotificationService` is never imported or instantiated anywhere else in the codebase — confirmed by a whole-repository search — including by routes that create/update tasks with a `user_id` already assigned.
Impact: The `services/` package gives the appearance of a working notification feature that does not exist in any observable behavior of the running application.
Recommendation: See `refactoring-playbook.md` PB-06 — remove dead service layer.

### [MEDIUM] Duplicated Logic Ignoring an Existing, Equivalent Utility (AP-08)
File: routes/user_routes.py:61, 106 (compared to utils/helpers.py:19-23)
Description: The email-format regex `r'^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$'` is written literally twice in `user_routes.py`, identical to the unused `validate_email` helper.
Impact: A future change to the email-validation rule requires editing both inline occurrences plus the unused function that looks like the "correct" place to make the change.
Recommendation: See `refactoring-playbook.md` PB-07 — trim and wire up `utils/helpers.py`.

### [MEDIUM] N+1 Query Pattern via ORM Calls Inside a Loop (AP-11)
File: routes/task_routes.py:11-63; routes/report_routes.py:53-68
Description: `get_tasks` calls `User.query.get(...)` and `Category.query.get(...)` per task inside a loop; `summary_report` calls `Task.query.filter_by(...)` per user inside a loop — the same N+1 defect expressed through ORM calls instead of raw SQL.
Impact: Query count grows linearly with the collection size instead of remaining constant.
Recommendation: See `refactoring-playbook.md` PB-09 — fix N+1 queries with eager loading.

### [MEDIUM] Declared but Unused Dependency (AP-12)
File: requirements.txt:4, 6
Description: `marshmallow==3.20.1` and `python-dotenv==1.0.0` are both declared dependencies with zero corresponding imports anywhere in the project; all validation is manual and configuration remains hardcoded (see AP-01).
Impact: Concrete evidence of an architectural intention that was never realized — the tooling to fix AP-01 is already installed, just unused.
Recommendation: See `refactoring-playbook.md` PB-10 (remove unused `marshmallow`) and PB-01 (wire up `python-dotenv`).

### [MEDIUM] Inconsistent, Sometimes-Silent Exception Handling (AP-13)
File: routes/task_routes.py:62, 137, 204, 236; routes/report_routes.py:186, 207, 221; routes/user_routes.py:130, 149
Description: 9 call sites across all 3 route files use bare `except:` with no logging of the original exception — 7 of them (`task_routes.py:62,236`; `report_routes.py:186,207,221`; `user_routes.py:130,149`) wrap a database write with a generic rollback and a generic error message, and 2 of them (`task_routes.py:137,204`) wrap a `datetime.strptime(...)` call with a narrower, format-specific error message but are still a bare `except:` with no logging. By contrast, `task_routes.py:151,221` and `user_routes.py:87` use `except Exception as e:` with `print(f"ERRO: {str(e)}")`. **Correction from this run:** the prior audit recorded only 4 of these 9 occurrences (`task_routes.py:62-63`; `report_routes.py:186-188,207-209,221-223`) — a full re-scan of every route file during this Phase 2 execution found the other 5 (`task_routes.py:137,204,236`; `user_routes.py:130,149`), all matching the same detection signal (bare `except:`, no logging of the original exception).
Impact: All 9 bare-`except:` sites are strictly harder to debug than the 3 sites using `except Exception as e:`, since no trace of the real failure is kept anywhere for any of them.
Recommendation: See `refactoring-playbook.md` PB-11 — centralize error handling.

### [MEDIUM] Inconsistent Validation Between Sibling Routes on the Same Entity (AP-14)
File: routes/report_routes.py:167-171 (create_category) vs. 190-202 (update_category)
Description: `create_category` checks `if not data: ...` before use; `update_category` accesses `'name' in data` etc. directly with no equivalent `None` check, risking an unhandled exception on a body-less request.
Impact: Two routes that should follow the same contract for the same entity diverge in a way that is only visible by comparing them side by side.
Recommendation: See `refactoring-playbook.md` PB-12 — consistent validation on sibling routes.

### [MEDIUM] Unrestricted CORS (AP-17)
File: app.py:15
Description: `CORS(app)` is called with no origin, method, or header restriction, permitting cross-origin requests from any domain to every route.
Impact: Combined with AP-03 (no authentication anywhere), this removes even the weak, incidental protection same-origin browser policies would otherwise provide.
Recommendation: See `refactoring-playbook.md` PB-02 — restrict CORS to an explicit origin list.

### [LOW] Duplicated Magic Value Ignoring an Existing Named Constant (AP-09)
File: routes/user_routes.py:64, 115 (compared to utils/helpers.py:114)
Description: `if len(password) < 4:` is written literally twice, instead of referencing the unused `MIN_PASSWORD_LENGTH = 4` constant.
Impact: A reader cannot tell from either inline site whether `4` is arbitrary or a documented rule — it is documented, just in a constant nothing references.
Recommendation: See `refactoring-playbook.md` PB-07 — trim and wire up `utils/helpers.py`.

### [LOW] Module-Level Initialization Side Effect (AP-15)
File: app.py:30-31 (compared to 33-34)
Description: `db.create_all()` sits at module level, outside the `if __name__ == '__main__':` guard; `seed.py:2` (`from app import app, db`) confirms this fires on import alone.
Impact: Any future script that imports `app.py` for an unrelated reason unintentionally triggers database schema creation.
Recommendation: See `refactoring-playbook.md` PB-13 — fix the module-level `db.create_all()` side effect while keeping `seed.py` working.

### [LOW] Unnecessarily Verbose Conditional (AP-16)
File: models/user.py:34-38
Description: `is_admin` is implemented as `if self.role == 'admin': return True else: return False` instead of a direct boolean expression.
Impact: Purely stylistic — behavior is already correct; no functional risk.
Recommendation: See `refactoring-playbook.md` PB-14 — simplify redundant conditional.

### [INFO] Structural Verification Checks
- AP-18 (God Class/Module): not found — responsibility is distributed across `models/`, `routes/`, `services/`, and `utils/`, with no single file resembling a God Class/Module. This is reported as a fact only; it does not offset the CRITICAL/HIGH findings above (see AP-03, AP-06, AP-07, AP-10).
- AP-19 (Referential Integrity): not applicable — `models/task.py:13-14` declares `db.ForeignKey('users.id')` and `db.ForeignKey('categories.id')` correctly via SQLAlchemy.
- AP-20 (Deprecated API Usage): not applicable — only `Flask`, `app.config`, `Blueprint`, `@blueprint.route`, `jsonify`, `request.get_json`, `CORS(app)`, `db.Model`, `db.Column`, `db.relationship`, `Model.query.*`, and `db.session.*` are used, none deprecated at the declared versions (Flask 3.0.0, flask-sqlalchemy 3.1.1, flask-cors 4.0.0).

================================
Total: 17 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

> **Note on subsequent execution:** this run's Phase 3 (MVC refactoring) was executed and committed separately; the project's current source tree (added `controllers/`, `middlewares/` with `auth.py` and `error_handler.py`, and `config.py`) reflects that completed refactoring, not the pre-refactoring state audited above.
