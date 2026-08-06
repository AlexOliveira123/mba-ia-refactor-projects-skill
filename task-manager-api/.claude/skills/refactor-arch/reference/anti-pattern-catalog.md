# Anti-Pattern Catalog — `task-manager-api`

Reference for **Phase 2 (Architecture Audit)**. Every entry is grounded in this project's own audit (`hypothesis-validation-task-manager-api.md`, findings H-001 through H-020) — nothing here was copied from another project's catalog. This project already has a partial layered structure, so several entries below are written specifically to avoid the two failure modes its audit called out explicitly: treating structural separation as proof of good architecture (false negative), and flagging normal validation/duplication as a defect without checking whether it is actually reachable and actually inconsistent (false positive).

## Severity scale (fixed — do not reinterpret)

- **CRITICAL** — directly exploitable security exposure (secrets, missing/decorative authentication, credential exposure, inadequate password protection) or a structural flaw that undermines the safety of the rest of the codebase.
- **HIGH** — a correctness, testability, or maintainability defect with a realistic path to inconsistent behavior or an untestable codebase, short of direct exploitability.
- **MEDIUM** — a defect that degrades reliability, performance, consistency, or project hygiene under normal operation, without a direct security exposure.
- **LOW** — a defect confined to readability, verbosity, or a narrow, non-security-relevant side effect.

Three entries (AP-18, AP-19, AP-20) are mandatory verification steps rather than pre-classified defects — see their own notes on why, and how to classify a real occurrence if one is ever found.

## Evidence rule

An entry is only reported as a Phase 2 finding when its detection signal is confirmed in the current code, with a real file and line citation, **and**, for any entry whose signal depends on whether a piece of code is used or ignored, confirmed by an actual reachability/reference search — not by assuming from folder structure, naming, or the mere presence of a `try/except` or a `models/`/`services/` package. If a signal is not found, or is only partially found, the entry produces no finding (or a partial finding scoped to exactly what was confirmed) — never extrapolate from another project in this challenge or from this catalog's "expected result" language.

---

### AP-01 — Hardcoded Secrets, Anywhere in the Codebase [CRITICAL]

**Detection signal:** a literal string assigned to a security-sensitive configuration key (`SECRET_KEY`, database credentials, API/service credentials, SMTP credentials) inside `.py` source code.
**Reachability note — apply this check without restriction:** unlike the dead-code entries below (AP-06/AP-07), this check must be run against **every** `.py` file, including ones with zero references from the application's entry points. A secret does not stop being a leaked secret because the file that holds it is never imported at runtime — the source-control repository itself is the relevant exposure surface.
**Reference evidence (audit time):** `app.py:13` — `app.config['SECRET_KEY'] = 'super-secret-key-123'`, despite `python-dotenv` already being declared in `requirements.txt:6` (see AP-12). `services/notification_service.py:9-10` — `self.email_user = 'taskmanager@gmail.com'` and `self.email_password = 'senha123'`, inside a class with zero references from anywhere else in the codebase (see AP-06) — the credential is exposed in source control regardless.
**Why it matters:** anyone with repository access has the Flask secret key and, separately, an SMTP credential; the fact that the SMTP-holding class is never executed does not un-expose the credential in the repository.

### AP-02 — Insecure Debug/Network Configuration [CRITICAL]

**Detection signal:** `debug=True` combined with `host='0.0.0.0'` (or equivalent) in `app.run(...)`.
**Reference evidence (audit time):** `app.py:34` — `app.run(debug=True, host='0.0.0.0', port=5000)`.
**Why it matters:** the interactive Werkzeug debugger becomes reachable over the network on any unhandled exception, a known path to arbitrary code execution.

### AP-03 — Absent or Decorative Authentication/Authorization [CRITICAL]

**Detection signal — two parts, both must be checked, not just the first:** (a) search the whole project for any access-control mechanism (`Authorization` header checks, `login_required`-style decorators, token verification) actually applied to a route; (b) if a login/token-issuing endpoint exists, separately confirm whether the token it issues is verified by **any** other route. A project can fail on (a) alone (no login exists at all, as in the first two projects of this challenge), or pass a naive check of "a `/login` route exists" while still failing entirely on (b) — do not treat the mere existence of a login endpoint as evidence of access control.
**Reference evidence (audit time):** (a) no route in `app.py`, `routes/user_routes.py`, `routes/task_routes.py`, or `routes/report_routes.py` checks identity, role, or token before executing — including `DELETE /users/<id>`, `DELETE /tasks/<id>`, `DELETE /categories/<id>`, and `PUT /users/<id>`, which accepts an arbitrary `role` value (`routes/user_routes.py:119-122`) with no check of who is making the request, allowing any anonymous caller to grant themselves `admin`. (b) `routes/user_routes.py:210` — `POST /login` returns `'token': 'fake-jwt-token-' + str(user.id)`, a value with no signature and no expiration; no other route in the project reads or validates any `Authorization` header or this token in any form.
**Why it matters:** every read, write, and delete operation across the entire API is reachable by any anonymous caller, including a path to self-granted administrative privilege; the presence of a login flow makes this worse to diagnose, not better, because it creates the appearance of a security control that provides no actual protection.

### AP-04 — Inadequate Password Hashing Algorithm [CRITICAL]

**Detection signal:** evaluate the **specific algorithm** used to protect a password, not merely whether some hashing function is called. Algorithms considered inadequate for password storage even when correctly invoked: MD5, SHA-1, or any fast general-purpose digest used with no per-user salt. A call into `hashlib` is not, by itself, evidence of adequate protection — `hashlib.md5(...)` is exactly as unsafe for passwords as no hashing at all, despite being "a real hash."
**Reference evidence (audit time):** `models/user.py:27-32` — `set_password` computes `hashlib.md5(pwd.encode()).hexdigest()`; `check_password` recomputes the same MD5 digest for comparison. No salt is generated or stored anywhere in the `User` model.
**Why it matters:** MD5 is fast enough to brute-force at scale and, with no salt, produces identical hashes for identical passwords across different users — directly observable in this project's own seed data, where short passwords (`seed.py:19,26,33`: `'1234'`, `'abcd'`, `'pass'`) would hash identically for any other user who chose the same password.

### AP-05 — Sensitive Credential Field Exposed via API Response [CRITICAL]

**Detection signal:** check this **per response-building code path**, not per model. A model's serialization method (e.g., `to_dict()`) including a password/hash field is a necessary but not sufficient signal — confirm which routes actually call that method to build their response, since a project may build some responses manually (omitting the field) and others via the model method (including it), inconsistently.
**Reference evidence (audit time):** `models/user.py:16-25` — `User.to_dict()` includes `'password': self.password` (line 21), the MD5 hash. This method is called by `routes/user_routes.py:33` (`GET /users/<id>`) and `routes/user_routes.py:209` (`POST /login`), both of which expose the hash in their JSON response. By contrast, `GET /users` (`routes/user_routes.py:10-25`) builds its response dictionary manually and does **not** include the password field — confirming this is an inconsistency between endpoints of the same resource, not a deliberate, uniformly-applied choice.
**Why it matters:** combined with AP-04 (MD5, no salt), any unauthenticated caller (see AP-03) can retrieve a crackable password hash for any user via `GET /users/<id>`.

### AP-06 — Dead Service Layer [MEDIUM]

**Detection signal:** a class or module inside `services/` with zero references (import or instantiation) anywhere else in the codebase, confirmed by a whole-repository text search for the symbol's name.
**Reference evidence (audit time):** `services/notification_service.py` (the entire file, `NotificationService`) — a whole-repository search for `NotificationService` returns matches only within its own defining file. No route that creates or updates a task, including ones that assign a `user_id` at creation time (`routes/task_routes.py:131`), calls `notify_task_assigned` or any other method on this class.
**Why it matters:** this is not merely unused code — it occupies a `services/` package, giving the appearance of a working notification feature that does not exist in any observable behavior of the running application; see AP-01 for the credential this dead code still exposes.

### AP-07 — Dead or Ignored Utility Layer [HIGH]

**Detection signal:** for each function/constant defined in `utils/`, confirm via whole-repository search whether it is (a) never referenced outside its own file, or (b) imported somewhere but never actually called at the import site (the import exists, but the equivalent logic is reimplemented inline nearby instead of invoking the import).
**Reference evidence (audit time):** of the 9 functions and 7 constants in `utils/helpers.py`, `format_date` and `calculate_percentage` are imported by `routes/report_routes.py:7` but never called anywhere in that file — the percentage calculation is instead reimplemented inline at `routes/report_routes.py:67,151` and `routes/task_routes.py:296`. The remaining 7 functions (`validate_email`, `sanitize_string`, `generate_id`, `log_action`, `is_valid_color`, `parse_date`, `process_task_data`) and all 7 constants (`VALID_STATUSES`, `VALID_ROLES`, `MAX_TITLE_LENGTH`, `MIN_TITLE_LENGTH`, `MIN_PASSWORD_LENGTH`, `DEFAULT_PRIORITY`, `DEFAULT_COLOR`) have zero references anywhere outside `utils/helpers.py` itself.
**Why it matters:** rated HIGH rather than MEDIUM (unlike AP-06) because this is not just one unused class — it is a whole module nominally responsible for centralizing validation/formatting that the rest of the application systematically ignores in favor of duplicating the same logic inline (see AP-08, AP-09), meaning the maintenance cost is paid twice: once for the unused module, once for every inline duplicate it should have prevented.

### AP-08 — Duplicated Logic Ignoring an Existing, Equivalent Utility [MEDIUM]

**Detection signal:** the same non-trivial expression (a validation regex, a formula) appears literally more than once in route/controller code, while an equivalent, already-defined utility function exists and is not called at any of those sites.
**Reference evidence (audit time):** the email-format regex `r'^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$'` appears literally at `routes/user_routes.py:61` (user creation) and `:106` (user update), identical to `utils/helpers.py:19-23`'s `validate_email`, which is never called from either site.
**Why it matters:** a future change to the email-validation rule requires finding and editing both inline occurrences, plus the unused function that looks like the "correct" place to make the change but silently has no effect on real behavior.

### AP-09 — Duplicated Magic Value Ignoring an Existing Named Constant [LOW]

**Detection signal:** a literal value with clear business meaning (a threshold, a limit) is repeated inline, while a named constant with the same value and an evidently matching purpose already exists elsewhere in the codebase and is unused at those sites.
**Reference evidence (audit time):** `if len(password) < 4:` appears literally at `routes/user_routes.py:64` and `:115`, instead of referencing `MIN_PASSWORD_LENGTH = 4`, already defined at `utils/helpers.py:114`.
**Why it matters:** a reader cannot tell from either inline site whether `4` is an arbitrary value or a documented business rule — it is, in fact, documented, just in a constant nothing references.

### AP-10 — Reimplementation Bypassing an Existing Model Method [HIGH]

**Detection signal:** a domain rule is correctly implemented as a method on a Model class, and the identical conditional logic is also written out manually, more than once, at call sites that never invoke the Model method.
**Reference evidence (audit time):** `Task.is_overdue()` (`models/task.py:50-60`) correctly encapsulates "has a `due_date` in the past, and status is not `done`/`cancelled`." The identical nested-conditional sequence is reimplemented manually, with no call to `is_overdue()`, at `routes/task_routes.py:30-39` (inside `get_tasks`), `:71-80` (inside `get_task`), `routes/user_routes.py:171-180` (inside `get_user_tasks`), and `routes/report_routes.py:34-37` and `:132-135` (inside `summary_report` and `user_report`) — five separate reimplementations across three files.
**Why it matters:** rated HIGH, not MEDIUM like ordinary duplication (AP-08), because the correct abstraction already exists specifically for this rule and is simply never used — a future change to the definition of "overdue" (e.g., a new terminal status) requires correctly updating six locations, and missing any one of them produces a silent behavioral inconsistency between endpoints rather than an error.

### AP-11 — N+1 Query Pattern via ORM Calls Inside a Loop [MEDIUM]

**Detection signal:** inside a loop over a collection fetched by one query, a per-iteration call to `Model.query.get(...)` or an equivalent single-row ORM fetch, where the related data could be obtained by a single query (a `JOIN`, `joinedload`, or an `IN`-based batch fetch).
**Reference evidence (audit time):** `routes/task_routes.py:11-63` (`get_tasks`) — for each task returned by `Task.query.all()` (line 14), the loop calls `User.query.get(t.user_id)` (line 42) and `Category.query.get(t.category_id)` (line 51). `routes/report_routes.py:53-68` (`summary_report`) — for each user returned by `User.query.all()` (line 53), the loop calls `Task.query.filter_by(user_id=u.id).all()` (line 56).
**Why it matters:** the same performance defect as raw-SQL N+1 queries in the other two projects of this challenge, expressed through the ORM's API instead of string concatenation — the query count still grows linearly with the collection size instead of staying constant.

### AP-12 — Declared but Unused Dependency [MEDIUM]

**Detection signal:** a package listed in `requirements.txt` with zero corresponding `import` anywhere in the `.py` files.
**Reference evidence (audit time):** `marshmallow==3.20.1` (`requirements.txt:4`) — no `import marshmallow` or `Schema` usage found anywhere in the project; all input validation is manual, inline conditionals. `python-dotenv==1.0.0` (`requirements.txt:6`) — no `import dotenv`/`load_dotenv` found anywhere; configuration (`SECRET_KEY`, database URI) remains hardcoded in `app.py:11-13` (see AP-01) despite the tool that would typically load these values from the environment already being installed.
**Why it matters:** an installed-but-unused dependency is concrete evidence of an architectural intention that was never realized — for `python-dotenv` specifically, it shows the CRITICAL hardcoded-secret problem (AP-01) is not blocked by a tooling gap, only by the tool not being used.

### AP-13 — Inconsistent, Sometimes-Silent Exception Handling [MEDIUM]

**Detection signal:** more than one exception-handling convention used across otherwise-equivalent code paths in the same project — specifically, a bare `except:` that discards the original error with no logging, next to an `except Exception as e:` elsewhere that at least prints the error.
**Reference evidence (audit time):** `routes/task_routes.py:62-63` (`get_tasks`) and `routes/report_routes.py:186-188,207-209,221-223` (`create_category`, `update_category`, `delete_category`) all use bare `except:` with no logging of the original exception. By contrast, `routes/user_routes.py:87-89` uses `except Exception as e:` with `print(f"ERRO: {str(e)}")`.
**Why it matters:** the 4 bare-`except:` sites are strictly harder to debug than the rest of the same project, since no trace of the real failure is kept anywhere — the inconsistency itself (not just the bare `except:` in isolation) is evidence that this is not a deliberate, uniform error-handling strategy.

### AP-14 — Inconsistent Validation Between Sibling Routes on the Same Entity [MEDIUM]

**Detection signal:** two routes that create and update the same entity apply different input-validation rules for the same input shape (one checks something the other does not).
**Reference evidence (audit time):** `routes/report_routes.py`'s `create_category` (lines 167-171) checks `if not data: return ... 400` before accessing `data.get(...)`; `update_category` (lines 190-202) accesses `'name' in data`, `'description' in data`, `'color' in data` directly, with no equivalent check that `data` is not `None` first — a `PUT /categories/<id>` with no JSON body would raise an unhandled exception on `'name' in data` before reaching the `try/except` that only wraps the persistence step (lines 204-209).
**Why it matters:** the two routes that should follow the same contract for the same entity diverge in a way that is only visible by comparing them side by side — a caller cannot predict, from one endpoint's behavior, how its sibling will behave for the same category of malformed input.

### AP-15 — Module-Level Initialization Side Effect [LOW]

**Detection signal:** code with an observable side effect (schema creation, a network call, a file write) placed at a module's top level, outside any `if __name__ == '__main__':` guard or an explicitly-called initialization function — meaning the side effect fires on every import of that module, not only when it is run directly.
**Reference evidence (audit time):** `app.py:30-31` — `with app.app_context(): db.create_all()` sits at module level, outside the `if __name__ == '__main__':` block (lines 33-34). `seed.py:2` (`from app import app, db`) confirms this fires on import: running `seed.py` triggers table creation as a side effect of importing `app`, not because `seed.py` asked for it explicitly.
**Why it matters:** any future script that imports `app.py` for an unrelated reason (e.g., to reuse the Flask instance in a test) unintentionally triggers database schema creation as a side effect of the import statement alone.

### AP-16 — Unnecessarily Verbose Conditional [LOW]

**Detection signal:** an `if/else` block whose two branches return literal `True`/`False` for a boolean-valued comparison already available directly.
**Reference evidence (audit time):** `models/user.py:34-38` — `is_admin` is `if self.role == 'admin': return True else: return False`.
**Why it matters:** purely stylistic — the behavior is already correct and identical to a direct boolean expression; flagged at LOW severity strictly for readability, with no functional risk.

### AP-17 — Unrestricted CORS [MEDIUM]

**Detection signal:** `CORS(app)` (or equivalent) called with no origin, method, or header restriction.
**Reference evidence (audit time):** `app.py:15` — `CORS(app)` with no arguments, permitting cross-origin requests from any domain to every route in the API.
**Why it matters:** combined with AP-03 (no authentication anywhere), this removes even the weak, incidental protection that same-origin browser policies would otherwise provide against browser-based abuse of the API.

### AP-18 — God Class / God Module [structural — verify, do not assume absent means healthy]

**Detection signal:** a single file or class concentrating data access, business rules, and routing for more than one unrelated domain, with no delegation elsewhere.
**Reference evidence (audit time):** **not found** — this project distributes responsibility across `models/`, `routes/`, `services/`, and `utils/`, with no single file resembling the God Class/Module pattern seen in this challenge's other two projects.
**Why this entry still exists and must still be checked explicitly:** the absence of a God Class must never be reported as "this project has good architecture" by itself — this project's own audit is the direct evidence for that caution: it has no God Class and still has a CRITICAL-severity total absence of authentication (AP-03), a dead service layer (AP-06), a mostly-dead utility layer (AP-07), and business logic that bypasses an existing, correct Model method (AP-10). Report this entry's result plainly ("not found") and let the other 19 entries speak for the actual state of the architecture — do not let a "not found" here soften how any other entry is reported.

### AP-19 — Missing Referential Integrity [structural — verify, do not assume]

**Detection signal:** a foreign-key-shaped column declared with no `ForeignKey`/`REFERENCES` constraint, when the project's data-access technology supports declaring one.
**Reference evidence (audit time):** **not applicable** — `models/task.py:13-14` declares `db.ForeignKey('users.id')` and `db.ForeignKey('categories.id')` correctly via SQLAlchemy.
**Why this entry still exists and must still be checked explicitly:** this pattern was CRITICAL/MEDIUM evidence in this challenge's two prior, raw-SQL-based projects; it does not recur here because this project uses an ORM with native foreign-key support, correctly declared. Report the check and its "not applicable, ORM declares FKs correctly" result explicitly — do not omit it, and do not treat this project's clean result here as license to skip the check on a future project that might use raw SQL.

### AP-20 — Deprecated API Usage [structural — verify, do not assume]

**Detection signal:** any call into Flask, Flask-SQLAlchemy, or `flask-cors` that is documented as removed or deprecated in the version declared in `requirements.txt` (Flask 3.0.0, flask-sqlalchemy 3.1.1, flask-cors 4.0.0).
**Reference evidence (audit time):** **not applicable** — the project only uses `Flask`, `app.config`, `Blueprint`, `@blueprint.route`, `jsonify`, `request.get_json`, `CORS(app)`, `db.Model`, `db.Column`, `db.relationship`, `Model.query.*`, and `db.session.*`, none of which are deprecated at the declared versions.
**Why it has no fixed severity:** this is a mandatory, version-specific verification, not a pre-decided defect — classify any real occurrence found at execution time using the general severity scale above, based on its concrete consequence, exactly as in this catalog's sibling entries for the other two projects of this challenge.

---

## Coverage summary

20 entries: 5 CRITICAL (AP-01…AP-05), 2 HIGH (AP-07, AP-10), 7 MEDIUM (AP-06, AP-08, AP-11, AP-12, AP-13, AP-14, AP-17), 3 LOW (AP-09, AP-15, AP-16), 3 structural/verification-only (AP-18, AP-19, AP-20). Together they account for all 20 confirmed findings of the `task-manager-api` audit. Three entries merge two findings each because the audit itself treats them as one underlying defect checked two ways, not two separate defects (see each entry's own text for why); every other finding maps one-to-one:

| Catalog entry | Audit finding(s) | Merge rationale (if any) |
|---|---|---|
| AP-01 | H-001, H-008 | Same defect (hardcoded secret), checked with no reachability restriction — a secret in dead code is still a leaked secret. |
| AP-02 | H-002 | — |
| AP-03 | H-003, H-004 | Same defect (no real access control) — total absence and a decorative/unvalidated token are one integrated check, not two. |
| AP-04 | H-005 | — |
| AP-05 | H-006 | — |
| AP-06 | H-007 | — |
| AP-07 | H-009 | — |
| AP-08 | H-010 | — |
| AP-09 | H-011 | — |
| AP-10 | H-012 | — |
| AP-11 | H-013 | — |
| AP-12 | H-014, H-015 | Same defect (declared-but-unused dependency), for two different packages. |
| AP-13 | H-016 | — |
| AP-14 | H-017 | — |
| AP-15 | H-018 | — |
| AP-16 | H-019 | — |
| AP-17 | H-020 | — |
| AP-18, AP-19, AP-20 | — (structural checks, not tied to a single finding) | — |

No finding from this project's own audit was left uncataloged, and no entry here was invented beyond what that audit confirmed with evidence — in particular, no God Class and no missing-FK entry is reported as a positive finding, consistent with this project's actual, verified state.
