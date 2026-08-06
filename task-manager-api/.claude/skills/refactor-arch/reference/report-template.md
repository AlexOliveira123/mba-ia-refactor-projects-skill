# Output Templates — `task-manager-api`

Mandatory format for all 3 phases. Do not change the structure; only fill in the real values observed in the current run. This file is independent from any equivalent file used for another project.

---

## Phase 1 — Project Analysis

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      <language>
Framework:     <framework + version>
Dependencies:  <relevant dependencies, comma-separated; flag any declared-but-unused ones here too>
Domain:        <application domain>
Architecture:  <current architecture — report physical layering AND reachability findings, not folder names alone>
Source files:  <N> files analyzed (<list of file/package names>)
DB tables:     <list of tables>
================================
```

---

## Phase 2 — Architecture Audit Report

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   <language + framework>
Files:   <N> analyzed | ~<M> lines of code

## Summary
CRITICAL: <n> | HIGH: <n> | MEDIUM: <n> | LOW: <n>

## Findings

### [<SEVERITY>] <Anti-pattern name (catalog ID)>
File: <file>:<line(s)>
Description: <what was found, factual>
Impact: <technical/maintenance/testing/security/performance impact, as applicable>
Recommendation: <reference to the matching playbook entry, without detailing the full fix here>

[... repeat for every finding, ordered by severity CRITICAL → HIGH → MEDIUM → LOW; within the same severity, order by order of appearance in the file]

### [INFO] Structural Verification Checks
- AP-18 (God Class/Module): <result — expect "not found" here, but reconfirm at execution time>
- AP-19 (Referential Integrity): <result — expect "not applicable, FKs declared via SQLAlchemy" here, but reconfirm>
- AP-20 (Deprecated API Usage): <result — expect "not applicable" here, but reconfirm against the exact versions in requirements.txt>

================================
Total: <n> findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

Fill-in rules:
- Every finding must correspond to a `anti-pattern-catalog.md` entry with real evidence reconfirmed in the code at execution time — never reuse the finding list from the project's own prior audit (`hypothesis-validation-task-manager-api.md`) without reconfirming it against the current state of the code.
- **Do not report a finding just because a folder (`services/`, `utils/`) exists or is absent** — every dead-code/unused-dependency finding (AP-06, AP-07, AP-12) requires an actual reachability search confirmed at execution time, not an assumption from directory listing.
- The 3 structural checks (AP-18, AP-19, AP-20) are always printed, even when not applicable — never omit them, and never assume their audit-time result ("not found"/"not applicable") still holds without reconfirming against the current code, since a prior partial refactor could have changed the picture.
- After the report is printed, execution **stops** and waits for the user's answer. No file may be modified before that answer is received. Only an unambiguous affirmative answer (`y` or `yes`) may unblock Phase 3; anything else (`n`, empty, or any other input) is treated as negative.

---

## Phase 3 — Refactoring Complete

```
================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
<directory tree actually created>

## Anti-patterns Resolved
<list of catalog IDs actually eliminated in this run, one line each>

## Dead Code Removed
<list of files/functions/constants actually deleted, one line each — e.g., "services/notification_service.py (AP-06); utils/helpers.py: sanitize_string, generate_id, log_action, is_valid_color, process_task_data (AP-07, no confirmed caller)">

## Anti-patterns Not Fully Resolved (if any)
<list of IDs that could not be fully eliminated within the scope of this refactoring, with justification>

## Known Gaps Outside This Run's Scope
<e.g., "Comprehensive authentication on every route (beyond the destructive/role-change operations guarded here) remains a real, larger gap — not addressed, as documented in mvc-guidelines.md">

## Documented Contract Changes
<list of the exact, minimal HTTP-contract changes applied, each tied to the finding that required it>

## Validation
  <✓ or ✗> Application boots without errors (`python seed.py` then `python app.py`)
  <✓ or ✗> All original endpoints respond (<list of verified paths>)
  <✓ or ✗> `require_auth`-guarded routes return 401 with no/invalid token
  <✓ or ✗> `PUT /users/<id>` changing `role` returns 403 for an authenticated non-admin caller
  <✓ or ✗> Zero CRITICAL/HIGH findings remaining
================================
```

Fill-in rules:
- "Anti-patterns Resolved" and "Dead Code Removed" only list what was actually changed in this run, with real verification of the resulting file — do not copy the playbook's list of intentions without confirming the change was applied.
- Before deleting anything listed as a dead-code removal candidate in `mvc-guidelines.md`, re-run the reachability search one more time against the current code — if a caller now exists that did not exist at audit time, keep that item and note the exception here instead of deleting it.
- The "Validation" section reflects an observed outcome (a real boot, a real call to each endpoint), never an assumption of success.
