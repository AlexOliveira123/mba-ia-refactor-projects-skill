---
name: refactor-arch
description: Analyzes, audits, and refactors the task-manager-api project (Python/Flask, partially layered) into stronger MVC adherence, eliminating the architectural and security anti-patterns identified in this project's own audit — without treating its existing folder structure as proof of good architecture. Use when the user invokes "/refactor-arch" inside this project.
---

# refactor-arch — task-manager-api

You are running the `refactor-arch` Skill inside the `task-manager-api` project (a Python/Flask task-management API with `models/`, `routes/`, `services/`, `utils/` packages, plus `app.py`, `database.py`, `seed.py` at the root). This Skill was built specifically for this project, based on this project's own audit — it is not a generic skill, and it is fully independent from any Skill built for the other two projects of this challenge: it does not read, import, or depend on any file outside this project's own `.claude/skills/refactor-arch/` directory.

Run the 3 phases below, in this exact order, without skipping steps and without moving to the next phase before the previous one is complete.

## Global rules (apply to the entire run)

1. **Evidence before claims.** Every finding reported in Phase 2 needs a real file + line citation, confirmed by reading the code at execution time — never copy the finding list from this document or from any previous report without reconfirming it against the current state of the files.
2. **Fact vs. inference.** Describe what the code does (observable fact) separately from what could happen as a consequence (impact inference). Never present an inference with the same certainty as a fact.
3. **Directory structure is not evidence of architecture quality, in either direction.** This project already has `models/`, `routes/`, `services/`, `utils/` packages. Do not conclude the project is well-architected because these folders exist, and do not conclude it is poorly architected merely because it lacks a `controllers/` folder. Every claim about a layer's health — used vs. unused, reachable vs. dead, centralized vs. duplicated — must be backed by an actual reference/reachability search across the codebase, not by the folder's name or existence. This project's own audit is the direct evidence for this rule: it has no God Class and still has a CRITICAL-severity total absence of effective authentication.
4. **No modification before human confirmation.** From the start of execution until the user's explicit answer in Phase 2, no project file may be created, edited, or removed.
5. **If the user answers negatively (or with anything other than an unambiguous "y"/"yes") at the Phase 2 gate, end the run immediately.** Do not modify any file. Do not ask again. State that the run has ended and that the audit report remains available for review.
6. **Do not invent problems and do not downplay confirmed ones.** Use exactly the severities defined in `reference/anti-pattern-catalog.md`. In particular, do not report a missing-foreign-key or a God Class finding for this project unless you have re-confirmed, at execution time, that the schema/structure has actually changed since the audit — both are expected to be absent here (see AP-18/AP-19), and reporting them without new evidence would be a fabricated finding.

---

## Phase 1 — Project Analysis

1. Read `reference/project-analysis.md` to know where to look for each piece of information, including how to check reachability rather than relying on folder names.
2. Read the project files (`requirements.txt`, `app.py`, `database.py`, `models/*.py`, `routes/*.py`, `services/*.py`, `utils/*.py`) to extract, with real evidence: language, framework (with version), relevant dependencies (including which declared dependencies are actually imported anywhere), application domain, project structure, current architecture (physical layering **and** reachability), database, and tables.
3. Present the result using exactly the "Phase 1" format defined in `reference/report-template.md`.
4. Move on to Phase 2 automatically — this phase has no confirmation gate.

## Phase 2 — Architecture Audit

1. Read `reference/anti-pattern-catalog.md` in full.
2. For every catalog entry (AP-01 through AP-20), check whether the described detection signal is present in the current code. For every confirmed occurrence:
   - Record the exact file and line(s).
   - Assign the severity defined in that catalog entry (do not reinterpret it).
   - Describe what was found (fact) and the impact (kept separate, and flagged as a consequence).
3. For every entry whose signal depends on whether code is used or ignored (AP-06, AP-07, AP-08, AP-09, AP-10, AP-12), perform an actual whole-repository reference search before concluding a symbol is dead, duplicated, or bypassed — never infer this from a folder name or from this catalog's "expected result" language alone.
4. Explicitly check the 3 structural entries (AP-18 God Class, AP-19 Referential Integrity, AP-20 Deprecated API Usage) and report the result even when "not found"/"not applicable" — never omit these checks, and never let a clean result on any of them soften how any other finding is reported.
5. Assemble the full report using the "Phase 2" format from `reference/report-template.md`: a quantitative summary by severity, findings ordered from CRITICAL to LOW, and the total.
6. Present the report to the user and **stop**. Ask explicitly: `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]`.
7. Wait for the user's answer before taking any further action.
   - Negative/ambiguous answer → apply Global Rule 5 and end the run.
   - Affirmative answer ("y" or an unambiguous equivalent) → proceed to Phase 3.

## Phase 3 — MVC Refactoring

Only run this phase after explicit confirmation in Phase 2.

1. Read `reference/mvc-guidelines.md` (target structure and layer rules) and `reference/refactoring-playbook.md` (concrete transformations) in full.
2. Create the directory structure defined in `mvc-guidelines.md` (add `controllers/`, `middlewares/`, and `config.py`; keep `models/`, `routes/`, `utils/`, `database.py`, `app.py`, `seed.py` in place).
3. Apply, in whatever order keeps the project runnable at each step, the patterns from `refactoring-playbook.md` (PB-01 through PB-14) that correspond to the findings confirmed in Phase 2. For every CRITICAL and HIGH finding, the matching transformation is mandatory. For MEDIUM and LOW findings, also apply the fix unless there is a real technical blocker — if one cannot be fully resolved within the scope of this refactoring, state that explicitly.
4. Before deleting any file/function/constant identified as dead code (`services/notification_service.py`; the 5 unused items in `utils/helpers.py` — see `mvc-guidelines.md`), re-run the reachability search one more time against the current code — do not delete anything whose confirmed-dead status has not been re-verified at this point in the run.
5. Preserve the project's observable contract: every original route path must keep existing and responding, with the only contract changes being the ones required to eliminate a confirmed finding (the real signed login token and the auth guard on destructive/role-change routes for CRITICAL AP-03, the removal of the `password` field from `GET /users/<id>` and `POST /login` for CRITICAL AP-05, and the CORS restriction for MEDIUM AP-17 — see `mvc-guidelines.md`'s "Execution compatibility" section for the exact list and severities). Keep `python seed.py` then `python app.py` as the documented way to start the application — apply PB-13's coupled `seed.py` change together with the `app.py` fix, never one without the other.
6. After the changes are complete, validate the result:
   - Run `python seed.py` then `python app.py` and confirm both complete/boot with no errors on `http://localhost:5000`.
   - Call every endpoint originally mapped in Phase 1 (`/`, `/health`, `/tasks`, `/tasks/<id>`, `/tasks/search`, `/tasks/stats`, `/users`, `/users/<id>`, `/users/<id>/tasks`, `/login`, `/reports/summary`, `/reports/user/<id>`, `/categories`, `/categories/<id>`) and confirm each one responds, including the new `401` behavior on the routes now guarded by `require_auth` and the new `403` behavior when a non-admin, authenticated caller attempts to change `role` via `PUT /users/<id>`.
   - Confirm that the CRITICAL/HIGH findings from Phase 2 are no longer observable in the resulting code.
7. Present the final summary using the "Phase 3" format from `reference/report-template.md`: new directory structure, anti-patterns resolved, dead code removed, known gaps left outside this run's scope, documented contract changes, and the validation result.

---

## Reference files for this Skill

- `reference/project-analysis.md` — Phase 1 heuristics, including how to check reachability.
- `reference/anti-pattern-catalog.md` — Phase 2 anti-pattern catalog (severity and detection signals, refined to avoid false positives from folder structure and false negatives from partial/decorative fixes).
- `reference/report-template.md` — output format for all 3 phases.
- `reference/mvc-guidelines.md` — target architecture (an evolution of the existing structure) and rules for Phase 3.
- `reference/refactoring-playbook.md` — concrete transformations (before/after) for Phase 3.
