---
name: refactor-arch
description: Analyzes, audits, and refactors the ecommerce-api-legacy project (Node.js/Express) into the MVC pattern, eliminating the architectural and security anti-patterns identified in this project's comparative audit. Use when the user invokes "/refactor-arch" inside this project.
---

# refactor-arch — ecommerce-api-legacy

You are running the `refactor-arch` Skill inside the `ecommerce-api-legacy` project (a Node.js/Express LMS API with a checkout flow, files `src/app.js`, `src/AppManager.js`, `src/utils.js`). This Skill was built specifically for this project, based on this project's own comparative audit — it is not a generic skill, and it is fully independent from any Skill built for another project: it does not read, import, or depend on any file outside this project's own `.claude/skills/refactor-arch/` directory.

Run the 3 phases below, in this exact order, without skipping steps and without moving to the next phase before the previous one is complete.

## Global rules (apply to the entire run)

1. **Evidence before claims.** Every finding reported in Phase 2 needs a real file + line citation, confirmed by reading the code at execution time — never copy the finding list from this document or from any previous report without reconfirming it against the current state of the files.
2. **Fact vs. inference.** Describe what the code does (observable fact) separately from what could happen as a consequence (impact inference). Never present an inference with the same certainty as a fact.
3. **No modification before human confirmation.** From the start of execution until the user's explicit answer in Phase 2, no project file may be created, edited, or removed.
4. **If the user answers negatively (or with anything other than an unambiguous "y"/"yes") at the Phase 2 gate, end the run immediately.** Do not modify any file. Do not ask again. State that the run has ended and that the audit report remains available for review.
5. **Do not invent problems and do not downplay confirmed ones.** Use exactly the severities defined in `reference/anti-pattern-catalog.md`. Do not add a "required fix" for anything that is not backed by a catalog entry with real evidence, even if it resembles a defect (see `reference/mvc-guidelines.md`'s explicit note on `GET /api/admin/financial-report`'s missing authentication, which is a known gap outside this run's confirmed scope, not a required fix).

---

## Phase 1 — Project Analysis

1. Read `reference/project-analysis.md` to know where to look for each piece of information.
2. Read the project files (`package.json`, `src/app.js`, `src/AppManager.js`, `src/utils.js`) to extract, with real evidence: language, framework (with version), relevant dependencies, application domain, project structure (source files and count), current architecture, database, and tables.
3. Present the result using exactly the "Phase 1" format defined in `reference/report-template.md`.
4. Move on to Phase 2 automatically — this phase has no confirmation gate.

## Phase 2 — Architecture Audit

1. Read `reference/anti-pattern-catalog.md` in full.
2. For every catalog entry (AP-01 through AP-20), check whether the described detection signal is present in the current code. For every confirmed occurrence:
   - Record the exact file and line(s).
   - Assign the severity defined in that catalog entry (do not reinterpret it).
   - Describe what was found (fact) and the impact (kept separate, and flagged as a consequence).
3. Explicitly check entry AP-20 (Deprecated API Usage) against the exact dependency versions in `package.json` at execution time, and report the result even when it is "not applicable" — never omit this check.
4. Assemble the full report using the "Phase 2" format from `reference/report-template.md`: a quantitative summary by severity, findings ordered from CRITICAL to LOW, and the total.
5. Present the report to the user and **stop**. Ask explicitly: `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]`.
6. Wait for the user's answer before taking any further action.
   - Negative/ambiguous answer → apply Global Rule 4 and end the run.
   - Affirmative answer ("y" or an unambiguous equivalent) → proceed to Phase 3.

## Phase 3 — MVC Refactoring

Only run this phase after explicit confirmation in Phase 2.

1. Read `reference/mvc-guidelines.md` (target structure and layer rules) and `reference/refactoring-playbook.md` (concrete transformations) in full.
2. Create the directory structure defined in `mvc-guidelines.md` (`src/config`, `src/database.js`, `src/cache.js`, `src/models`, `src/services`, `src/controllers`, `src/routes`, `src/middlewares`).
3. Apply, in whatever order keeps the project runnable at each step, the patterns from `refactoring-playbook.md` (PB-01 through PB-16) that correspond to the findings confirmed in Phase 2. For every CRITICAL and HIGH finding, the matching transformation is mandatory. For MEDIUM and LOW findings, also apply the fix unless there is a real technical blocker — if one cannot be fully resolved within the scope of this refactoring, state that explicitly (do not claim it was resolved when it was not).
4. Once the new structure is in place and verified, retire the original flat files (`src/AppManager.js`, `src/utils.js`) as instructed in `mvc-guidelines.md` — do not leave the old God Class sitting alongside the new layered structure.
5. Preserve the project's observable contract: every original route path must keep existing and responding, with the only contract changes being the ones required to eliminate a CRITICAL/HIGH finding (the `pwd`-required-for-new-accounts change from AP-08, and the `X-Admin-Token` requirement on `DELETE /api/users/:id` from AP-04 — see `mvc-guidelines.md`'s "Execution compatibility" section for the full, exact list). Keep `npm start` (→ `node src/app.js`) as the way to start the application; no root-level shim file is needed since `src/app.js` already is the entry point declared in `package.json`.
6. After the changes are complete, validate the result:
   - Start the application (`npm start`) and confirm it boots with no errors on `http://localhost:3000`.
   - Call every endpoint originally mapped in Phase 1 (`POST /api/checkout`, `GET /api/admin/financial-report`, `DELETE /api/users/:id`) and confirm each one responds (including, where applicable, the new behavior of requiring the `X-Admin-Token` header on the delete route and rejecting a passwordless new-account checkout).
   - Confirm that the CRITICAL/HIGH findings from Phase 2 are no longer observable in the resulting code.
7. Present the final summary using the "Phase 3" format from `reference/report-template.md`: new directory structure, anti-patterns resolved (and not resolved, if any, with justification), known gaps left outside this run's scope, documented contract changes, and the validation result.

---

## Reference files for this Skill

- `reference/project-analysis.md` — Phase 1 heuristics.
- `reference/anti-pattern-catalog.md` — Phase 2 anti-pattern catalog (severity and detection signals).
- `reference/report-template.md` — output format for all 3 phases.
- `reference/mvc-guidelines.md` — target architecture structure and rules for Phase 3.
- `reference/refactoring-playbook.md` — concrete transformations (before/after) for Phase 3.
