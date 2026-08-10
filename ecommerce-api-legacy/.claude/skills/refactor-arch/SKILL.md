---
name: refactor-arch
description: Analyzes, audits, and refactors a codebase into stronger MVC/SOLID adherence — detecting the project's own language, framework, and architecture before evaluating it, and eliminating confirmed architectural, security, and code-quality anti-patterns without assuming any fixed technology stack or folder layout. Use when the user invokes "/refactor-arch" inside a project.
---

# refactor-arch

You are running the `refactor-arch` Skill. This Skill is technology-agnostic: it does not assume a specific language, framework, or project layout, and it does not hardcode any fact about a particular codebase. All project-specific knowledge — the anti-patterns actually confirmed for the project you are running against, its target architecture, and the concrete refactoring transformations available — lives in this Skill's own `reference/` directory, which you must read at execution time. Nothing about a specific project is baked into this file; if this Skill has been copied into more than one project, each copy behaves identically and reads only its own `reference/` directory.

Run the 3 phases below, in this exact order, without skipping steps and without moving to the next phase before the previous one is complete.

## Global rules (apply to the entire run)

1. **Evidence before claims.** Every finding reported in Phase 2 needs a real file + line citation, confirmed by reading the code at execution time — never copy a finding list from a prior report or from any reference file without reconfirming it against the current state of the files.
2. **Fact vs. inference.** Describe what the code does (observable fact) separately from what could happen as a consequence (impact inference). Never present an inference with the same certainty as a fact.
3. **Directory structure is not evidence of architecture quality, in either direction.** Do not conclude a project is well-architected merely because it already has folders such as `models/`, `routes/`, `services/`, or `controllers/`, and do not conclude it is poorly architected merely because such folders are absent. Every claim about a layer's health — used vs. unused, reachable vs. dead, centralized vs. duplicated — must be backed by an actual reference/reachability search across the codebase, not by a folder's name or its mere presence/absence.
4. **No modification before human confirmation.** From the start of execution until the user's explicit answer in Phase 2, no project file may be created, edited, or removed.
5. **If the user answers negatively (or with anything other than an unambiguous "y"/"yes") at the Phase 2 gate, end the run immediately.** Do not modify any file. Do not ask again. State that the run has ended and that the audit report remains available for review.
6. **Do not invent problems and do not downplay confirmed ones.** Use exactly the severities defined in `reference/anti-pattern-catalog.md` — do not reinterpret them. Do not report a finding (e.g., a missing foreign key, a God Class, a deprecated API call) unless you have reconfirmed real, current evidence for it at execution time; a catalog entry's own notes about what was or was not found at audit time describe that prior run, not a guarantee about the state of the code now.

---

## Phase 1 — Project Analysis

1. Read `reference/project-analysis.md` to know where to look for each piece of information, including how to check reachability rather than relying on folder names alone.
2. Read the project's source files to extract, with real evidence: language, framework (with version), relevant dependencies (including which declared dependencies are actually imported anywhere), application domain, project structure, current architecture (physical layering **and** reachability), and — where applicable — database and tables.
3. Present the result using exactly the "Phase 1" format defined in `reference/report-template.md`.
4. Move on to Phase 2 automatically — this phase has no confirmation gate.

## Phase 2 — Architecture Audit

1. Read `reference/anti-pattern-catalog.md` in full.
2. For every catalog entry, check whether the described detection signal is present in the current code. For every confirmed occurrence:
   - Record the exact file and line(s).
   - Assign the severity defined in that catalog entry (do not reinterpret it).
   - Describe what was found (fact) and the impact (kept separate, and flagged as a consequence).
3. For every entry whose signal depends on whether code is used, ignored, or bypassed, perform an actual whole-repository reference search before concluding a symbol is dead, duplicated, or bypassed — never infer this from a folder name, a naming convention, or the catalog's own "expected result" language alone.
4. Explicitly check every structural/verification-only entry in the catalog (e.g., God Class, referential integrity, deprecated API usage) and report the result even when it is "not found"/"not applicable" — never omit these checks, and never let a clean result on one of them soften how any other finding is reported.
5. Assemble the full report using the "Phase 2" format from `reference/report-template.md`: a quantitative summary by severity, findings ordered from CRITICAL to LOW, and the total.
6. Present the report to the user and **stop**. Ask explicitly: `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]`.
7. Wait for the user's answer before taking any further action.
   - Negative/ambiguous answer → apply Global Rule 5 and end the run.
   - Affirmative answer ("y" or an unambiguous equivalent) → proceed to Phase 3.

## Phase 3 — MVC Refactoring

Only run this phase after explicit confirmation in Phase 2.

1. Read `reference/mvc-guidelines.md` (target structure and layer rules) and `reference/refactoring-playbook.md` (concrete transformations) in full.
2. Create or adjust the directory structure defined in `reference/mvc-guidelines.md` for this project.
3. Apply, in whatever order keeps the project runnable at each step, the patterns from `reference/refactoring-playbook.md` that correspond to the findings confirmed in Phase 2. For every CRITICAL and HIGH finding, the matching transformation is mandatory. For MEDIUM and LOW findings, also apply the fix unless there is a real technical blocker — if one cannot be fully resolved within the scope of this refactoring, state that explicitly instead of claiming it was resolved.
4. Before deleting any file, function, or constant identified as dead code, re-run the reachability search one more time against the current code — do not delete anything whose confirmed-dead status has not been re-verified at this point in the run.
5. Preserve the project's observable contract: every original route/entry point must keep existing and responding, with the only contract changes being the ones required to eliminate a confirmed CRITICAL/HIGH finding. Document every such change exactly as described in `reference/mvc-guidelines.md`'s execution-compatibility notes.
6. After the changes are complete, validate the result:
   - Start the application using its documented entry point and confirm it boots with no errors.
   - Call every endpoint originally mapped in Phase 1 and confirm each one responds, including any new status codes introduced by the fixes applied.
   - Confirm that the CRITICAL/HIGH findings from Phase 2 are no longer observable in the resulting code.
7. Present the final summary using the "Phase 3" format from `reference/report-template.md`: new directory structure, anti-patterns resolved (and not fully resolved, if any, with justification), dead code removed (if any), documented contract changes, and the validation result.

---

## Reference files for this Skill

- `reference/project-analysis.md` — Phase 1 heuristics for this project, including how to check reachability.
- `reference/anti-pattern-catalog.md` — Phase 2 anti-pattern catalog (severity and detection signals) confirmed for this project.
- `reference/report-template.md` — output format for all 3 phases.
- `reference/mvc-guidelines.md` — target architecture and rules for Phase 3.
- `reference/refactoring-playbook.md` — concrete transformations (before/after) for Phase 3.
