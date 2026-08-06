# Analysis Heuristics — `task-manager-api` (Phase 1)

Guide for **Phase 1 (Project Analysis)**. Every heuristic below is specific to what this project actually contains — these are not generic rules for an arbitrary stack, and this file is independent from any equivalent file used for another project's Skill.

**Standing rule for this project (learned from its own audit, apply throughout every phase, not only here):** this codebase already has a `models/`, `routes/`, `services/`, `utils/` package layout. That physical separation is a fact to report in this phase — it is **not**, by itself, evidence of good architecture, effective separation of responsibilities, or absence of anti-patterns. A folder can exist and be structurally correct while being disconnected from the application's real execution path (dead code), or while the code that lives in the "right" layer is bypassed by duplicated logic elsewhere. Phase 2 verifies reachability and actual usage explicitly — do not let a well-organized directory listing substitute for that verification.

## Language

**Signal:** `.py` files, a `requirements.txt` at the project root.
**Expected result:** `Python`.

## Framework

**Signal:** `requirements.txt` → `flask==<version>`; `app.py` contains `from flask import Flask`.
**Expected result:** `Flask <exact version read from requirements.txt>` (at audit time: Flask 3.0.0).

## Relevant dependencies

**Signal:** read every line of `requirements.txt`, then confirm which of them are actually imported anywhere in the `.py` files (`grep`/text search for `import <package>` across the whole tree, not just the files you expect to use it).
**Expected result at audit time:** `flask-sqlalchemy==3.1.1` (ORM, imported in `database.py`) and `flask-cors==4.0.0` (imported in `app.py`) are both in active use. `marshmallow==3.20.1` and `python-dotenv==1.0.0` are declared but, at audit time, not imported anywhere — report this explicitly as part of the dependency summary, it is directly relevant to Phase 2 (see catalog entry for unused dependencies). Re-verify this at execution time: a prior Phase 3 run may have already wired one of them in, which would change this result.

## Application domain

**Signal:** table names in `models/*.py` (`__tablename__`), the root route's response body.
**Expected result:** `Task management (tasks, users, categories)` — evidenced by `models/task.py:6`, `models/user.py:6`, `models/category.py:5`, and `app.py`'s `/` route returning `{'message': 'Task Manager API', 'version': '1.0'}`.

## Project structure

**Signal:** list `.py` files under the project root and its immediate subpackages (`models/`, `routes/`, `services/`, `utils/`), ignoring `__pycache__`, `.claude/`, virtual environments.
**Expected result at audit time:** `app.py`, `database.py`, `seed.py` at the root; `models/` (`user.py`, `task.py`, `category.py`, `__init__.py`); `routes/` (`user_routes.py`, `task_routes.py`, `report_routes.py`, `__init__.py`); `services/` (`notification_service.py`, `__init__.py`); `utils/` (`helpers.py`, `__init__.py`). Report the exact count and names observed at execution time — a prior Phase 3 run may have added a `controllers/` package or removed files.

## Current architecture

**Signal:** presence of the `models/`/`routes/`/`services/`/`utils/` split (a physical fact) **combined with** a reachability check from the application's actual entry points (`app.py`'s blueprint registrations) into each of those packages — do not report "current architecture" from folder names alone.
**How to check reachability, concretely:** for each symbol defined in `services/` and `utils/` (every class, function, and constant), search the entire codebase for references to it outside its own defining file. A symbol with zero external references is not part of the application's real execution path, regardless of which folder it lives in.
**Expected result at audit time:** `models/` and `routes/` are both real and reachable (`app.py` registers all 3 blueprints, and each blueprint's functions call into the models). `services/notification_service.py` (`NotificationService`) has zero external references anywhere in the codebase — it is dead code despite occupying its own package. `utils/helpers.py` is mixed: 2 of its 9 functions (`format_date`, `calculate_percentage`) are imported by `routes/report_routes.py:7` but never actually called there (the same calculations are reimplemented inline instead); the other 7 functions and all 7 constants have zero references anywhere outside `utils/helpers.py` itself. Report this precisely as "partially organized, with structurally-present but functionally-disconnected layers" — not as "well organized" and not as "disorganized," either characterization would be inaccurate given the mixed evidence.

## Database

**Signal:** `SQLALCHEMY_DATABASE_URI` in `app.py`; ORM model definitions in `models/*.py` (`db.Column`, `db.ForeignKey`).
**Expected result:** `SQLite (file tasks.db), accessed via the Flask-SQLAlchemy ORM` — evidenced by `app.py:11` and the `db.Column`/`db.ForeignKey` declarations in `models/task.py:8-18`. Note for Phase 2: `Task` declares `db.ForeignKey('users.id')` and `db.ForeignKey('categories.id')` correctly (`models/task.py:13-14`) — referential integrity is present here, unlike the two prior projects in this challenge; do not report a missing-FK finding for this project without first re-confirming the schema at execution time, since it is expected to be absent.

## Phase 1 summary — output format

Use the format defined in `report-template.md`, "Phase 1" section. Every value above must be extracted from the code at execution time, never copied from this document as if it were the result — this file describes **where to look, what to expect, and which verification (reachability, not just presence) is required**, it does not replace actually reading the code and tracing references on every run.
