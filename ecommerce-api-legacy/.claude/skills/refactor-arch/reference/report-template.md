# Output Templates — `ecommerce-api-legacy`

Mandatory format for all 3 phases. Do not change the structure; only fill in the real values observed in the current run. This file is independent from any equivalent file used for another project.

---

## Phase 1 — Project Analysis

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      <language>
Framework:     <framework + version>
Dependencies:  <relevant dependencies, comma-separated>
Domain:        <application domain>
Architecture:  <current architecture, one sentence>
Source files:  <N> files analyzed (<list of file names>)
DB tables:     <list of tables>
================================
```

---

## Phase 2 — Architecture Audit Report

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
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

### [INFO] Deprecated API Check
Description: verification of catalog entry AP-20 — <result: "no deprecated API found in the analyzed dependencies and calls" or the list of findings, if any>

================================
Total: <n> findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

Fill-in rules:
- Every finding reported here must correspond to an `anti-pattern-catalog.md` entry with real evidence reconfirmed in the code at execution time — never reuse the finding list from a previous manual/comparative audit without reconfirming it against the current state of the code.
- If the code has already been partially modified since the last audit, report only what is still observable now.
- The "Deprecated API" check (AP-20) is always printed, even when not applicable — never omit this section.
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
<list of catalog IDs actually eliminated in this run, one line each, e.g., "AP-13 N+1 Query Pattern — single JOIN query in models/reportModel.js">

## Anti-patterns Not Fully Resolved (if any)
<list of IDs that could not be fully eliminated within the scope of this refactoring, with justification>

## Known Gaps Outside This Run's Scope
<e.g., "GET /api/admin/financial-report remains unauthenticated — not a confirmed audit finding for this run, therefore not treated as a required fix; flagged here for visibility">

## Documented Contract Changes
<list of the exact, minimal HTTP-contract changes applied, each tied to the CRITICAL/HIGH finding that required it — e.g., "POST /api/checkout with a new email and no `pwd` now returns 400 instead of silently creating the account with password '123456' (resolves AP-08)">

## Validation
  <✓ or ✗> Application boots without errors (`npm start`)
  <✓ or ✗> All original endpoints respond (<list of verified paths>)
  <✓ or ✗> Zero CRITICAL/HIGH findings remaining
================================
```

Fill-in rules:
- "Anti-patterns Resolved" only lists what was actually changed in this run, with real verification of the resulting file — do not copy the playbook's list of intentions without confirming the change was applied.
- "Documented Contract Changes" must list every behavioral difference from the original API, however small — silence here is read as a claim that nothing changed.
- The "Validation" section reflects an observed outcome (a real boot, a real call to each endpoint), never an assumption of success.
