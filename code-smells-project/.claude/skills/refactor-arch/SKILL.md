---
name: refactor-arch
description: Analyzes, audits, and refactors the code-smells-project (Python/Flask) into the MVC pattern, eliminating the architectural and security anti-patterns identified in this project's manual audit. Use when the user invokes "/refactor-arch" inside this project.
---

# refactor-arch — code-smells-project

You are running the `refactor-arch` Skill inside the `code-smells-project` project (a Python/Flask e-commerce API, files `app.py`, `controllers.py`, `models.py`, `database.py`). This Skill was built specifically for this project, based on a manual audit that has already been completed — it is not a generic skill.

Run the 3 phases below, in this exact order, without skipping steps and without moving to the next phase before the previous one is complete.

## Global rules (apply to the entire run)

1. **Evidence before claims.** Every finding reported in Phase 2 needs a real file + line citation, confirmed by reading the code at execution time — never copy the finding list from this document or from any previous report without reconfirming it against the current state of the files.
2. **Fact vs. inference.** Describe what the code does (observable fact) separately from what could happen as a consequence (impact inference). Never present an inference with the same certainty as a fact.
3. **No modification before human confirmation.** From the start of execution until the user's explicit answer in Phase 2, no project file may be created, edited, or removed.
4. **If the user answers negatively (or with anything other than an unambiguous "y"/"yes") at the Phase 2 gate, end the run immediately.** Do not modify any file. Do not ask again. State that the run has ended and that the audit report remains available for review.
5. **Do not invent problems and do not downplay confirmed ones.** Use exactly the severities defined in `reference/anti-pattern-catalog.md`.

---

## Phase 1 — Project Analysis

1. Read `reference/project-analysis.md` to know where to look for each piece of information.
2. Read the project files (`requirements.txt`, `app.py`, `controllers.py`, `models.py`, `database.py`) to extract, with real evidence: language, framework (with version), relevant dependencies, application domain, project structure (source files and count), current architecture, database, and tables.
3. Present the result using exactly the "Phase 1" format defined in `reference/report-template.md`.
4. Move on to Phase 2 automatically — this phase has no confirmation gate.

## Phase 2 — Architecture Audit

1. Read `reference/anti-pattern-catalog.md` in full.
2. For every catalog entry (AP-01 through AP-20), check whether the described detection signal is present in the current code. For every confirmed occurrence:
   - Record the exact file and line(s).
   - Assign the severity defined in that catalog entry (do not reinterpret it).
   - Describe what was found (fact) and the impact (kept separate, and flagged as a consequence).
3. Explicitly check entry AP-20 (Deprecated API Usage) and report the result even when it is "not applicable" — never omit this check.
4. Assemble the full report using the "Phase 2" format from `reference/report-template.md`: a quantitative summary by severity, findings ordered from CRITICAL to LOW, and the total.
5. Present the report to the user and **stop**. Ask explicitly: `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]`.
6. Wait for the user's answer before taking any further action.
   - Negative/ambiguous answer → apply Global Rule 4 and end the run.
   - Affirmative answer ("y" or an unambiguous equivalent) → proceed to Phase 3.

## Phase 3 — MVC Refactoring

Only run this phase after explicit confirmation in Phase 2.

1. Read `reference/mvc-guidelines.md` (target structure and layer rules) and `reference/refactoring-playbook.md` (concrete transformations) in full.
2. Create the directory structure defined in `mvc-guidelines.md` (`src/config`, `src/database.py`, `src/models`, `src/views`, `src/controllers`, `src/middlewares`).
3. Apply, in whatever order keeps the project runnable at each step, the patterns from `refactoring-playbook.md` (PB-01 through PB-18) that correspond to the findings confirmed in Phase 2. For every CRITICAL and HIGH finding, the matching transformation is mandatory. For MEDIUM and LOW findings, also apply the fix unless there is a real technical blocker — if one cannot be fully resolved within the scope of this refactoring, state that explicitly (do not claim it was resolved when it was not).
4. Once the new structure is in place and verified, retire the original flat files (`models.py`, `controllers.py`, `database.py` at the project root) as instructed in `mvc-guidelines.md` — do not leave the old God Modules sitting alongside the new `src/` structure.
5. Preserve the project's observable contract: every original route path must keep existing and responding, with the only contract changes being the ones required to eliminate a CRITICAL/HIGH finding (e.g., `/admin/*` now requires the `X-Admin-Token` header; responses no longer contain a password/secret). Keep `python app.py` at the root as a valid way to start the application.
6. After the changes are complete, validate the result:
   - Start the application (`python app.py`, or equivalent) and confirm it boots with no errors.
   - Call every endpoint originally mapped in Phase 1 (`/`, `/produtos`, `/produtos/busca`, `/produtos/<id>`, `/usuarios`, `/usuarios/<id>`, `/login`, `/pedidos`, `/pedidos/usuario/<id>`, `/pedidos/<id>/status`, `/relatorios/vendas`, `/health`, `/admin/reset-db`, `/admin/query`) and confirm each one responds (including, where applicable, the new behavior of requiring a token on the admin routes).
   - Confirm that the CRITICAL/HIGH findings from Phase 2 are no longer observable in the resulting code.
7. Present the final summary using the "Phase 3" format from `reference/report-template.md`: new directory structure, anti-patterns resolved (and not resolved, if any, with justification), and the validation result.

---

## Reference files for this Skill

- `reference/project-analysis.md` — Phase 1 heuristics.
- `reference/anti-pattern-catalog.md` — Phase 2 anti-pattern catalog (severity and detection signals).
- `reference/report-template.md` — output format for all 3 phases.
- `reference/mvc-guidelines.md` — target architecture structure and rules for Phase 3.
- `reference/refactoring-playbook.md` — concrete transformations (before/after) for Phase 3.
