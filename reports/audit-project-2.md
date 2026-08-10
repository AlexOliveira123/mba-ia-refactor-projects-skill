# Audit Report — Project 2 (`ecommerce-api-legacy`)

> Output of running the `refactor-arch` Skill's Phase 1 (Project Analysis) and Phase 2 (Architecture Audit) for real against `ecommerce-api-legacy`'s original, pre-refactoring source (`git show 6d1ce62`, the repository's initial commit, restored into an isolated working copy — the committed, already-refactored code in this repository was not touched). Every finding below was independently re-confirmed line-by-line against that restored code during this run; all 19 catalog entries matched the project's own comparative audit (`comparative-audit-ecommerce-api-legacy.md`, findings G-001 through G-019) exactly, with no corrections needed. The corresponding standardized analysis document is `ecommerce-api-legacy/project-analysis.md`.

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      JavaScript (Node.js, CommonJS)
Framework:     Express ^4.18.2
Dependencies:  sqlite3 ^5.1.6 (callback-based driver)
Domain:        LMS API with a course-checkout/payment flow
Architecture:  Flat and monolithic — a single class (`AppManager`) owns the database connection, schema/seed, all 3 routes, and every piece of business logic inline inside deeply nested callbacks; no Model, View, Controller, or Router isolation.
Source files:  3 files analyzed (src/app.js, src/AppManager.js, src/utils.js), 180 lines total
DB tables:     courses, enrollments, payments
================================
```

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   Node.js + Express ^4.18.2
Files:   3 analyzed | ~180 lines of code

## Summary
CRITICAL: 5 | HIGH: 6 | MEDIUM: 4 | LOW: 4

## Findings

### [CRITICAL] Hardcoded Secrets (AP-01)
File: src/utils.js:1-7
Description: `config.dbUser`, `config.dbPass`, `config.paymentGatewayKey` (a `pk_live_...`-shaped key), and `config.smtpUser` are all literal strings, with no read from `process.env`.
Impact: Anyone with repository access has database, payment-gateway, and SMTP credentials; rotation requires a code change and redeploy.
Recommendation: See `refactoring-playbook.md` PB-01 — centralize configuration via environment variables.

### [CRITICAL] Weak, Reversible Password Hashing (AP-02)
File: src/utils.js:17-23
Description: `badCrypto(pwd)` repeats a Base64 encoding of the password 10,000 times and truncates the result to 10 characters — Base64 is a reversible encoding, not a cryptographic hash, and no salt is used.
Impact: Any database read exposes passwords in a form that can be decoded directly, and identical passwords produce identical stored values across users.
Recommendation: See `refactoring-playbook.md` PB-02 — replace with salted `crypto.scryptSync` hashing.

### [CRITICAL] God Class (AP-03)
File: src/AppManager.js:4-141
Description: `AppManager` owns the database connection, schema definition, seed data, all 3 route registrations, and every piece of business logic (checkout, payment approval, enrollment, financial reporting, user deletion) inline.
Impact: Every change, regardless of domain, requires editing the same file and reasoning about the same ~140-line method, with no independent testing or review boundary.
Recommendation: See `refactoring-playbook.md` PB-03 — split the God Class by domain.

### [CRITICAL] Unauthenticated Destructive Endpoint (AP-04)
File: src/AppManager.js:131-137
Description: `DELETE /api/users/:id` deletes a user row with no authentication or authorization check; the handler's own response text acknowledges the resulting orphaned data in `enrollments`/`payments`.
Impact: Any anonymous client can delete any user by ID.
Recommendation: See `refactoring-playbook.md` PB-04 — guard the endpoint with an admin-token middleware.

### [CRITICAL] Sensitive Data Logged in Plaintext (AP-05)
File: src/AppManager.js:45
Description: A `console.log` call interpolates the full card number submitted by the client together with the payment-gateway secret key on every checkout call.
Impact: Anything with access to application logs gains full card numbers and the gateway credential in the same log line — a PCI-relevant exposure independent of the database.
Recommendation: See `refactoring-playbook.md` PB-05 — stop logging sensitive payment data.

### [HIGH] Global Mutable State (AP-06)
File: src/utils.js:9-10, 14
Description: `globalCache` and `totalRevenue` are module-level mutable variables, exported directly and mutated by `logAndCache` with no accessor boundary.
Impact: State shared this way has no single owner; concurrent requests can race on the same key with no way to bound or reset it centrally.
Recommendation: See `refactoring-playbook.md` PB-06 — encapsulate the cache behind a small class.

### [HIGH] Unvalidated Fake Payment Gateway Logic (AP-07)
File: src/AppManager.js:46
Description: Payment approval is decided solely by whether the card number starts with `"4"` — no real gateway is called and no card format/expiry validation is performed, despite `config.paymentGatewayKey` being referenced immediately above.
Impact: Any 16 arbitrary digits starting with `4` are approved as a "paid" transaction; this is a placeholder, not a payment integration.
Recommendation: See `refactoring-playbook.md` PB-07 — isolate the mock payment gateway into its own service, clearly marked as non-production.

### [HIGH] Insecure Default Credential Fallback (AP-08)
File: src/AppManager.js:68
Description: `badCrypto(p || "123456")` silently assigns the literal password `123456` to any newly created account whose request omitted `pwd`.
Impact: Every account created without an explicit password shares the same publicly-known credential, with no client-visible signal that this happened.
Recommendation: See `refactoring-playbook.md` PB-08 — require the password explicitly when creating a new account.

### [HIGH] Deeply Nested Callback Structure / "Callback Hell" (AP-09)
File: src/AppManager.js:37-77, 83-127
Description: The checkout handler nests up to 5 levels of callbacks before a response is sent; the financial-report handler repeats a comparable nesting pattern.
Impact: Every branch (not-found, denied payment, DB error) is handled at a different nesting depth with a different closure scope, making it easy to reference the wrong variable or skip an error check.
Recommendation: See `refactoring-playbook.md` PB-09 — promisify the database layer and refactor to `async`/`await`.

### [HIGH] Race-Condition-Prone Manual Async Completion Tracking (AP-10)
File: src/AppManager.js:86, 93 (counters), 104, 106 (unchecked callbacks)
Description: `coursesPending`/`enrPending` counters are decremented inside concurrent callbacks to decide when to send the report response; the callbacks that decrement them never check their own `err` parameter first.
Impact: Under concurrent execution this can produce double responses, hangs, or a response sent with silently incomplete data.
Recommendation: See `refactoring-playbook.md` PB-09 — promisify the database layer and refactor to `async`/`await`.

### [HIGH] Business Logic Coupled to the HTTP Layer (AP-11)
File: src/AppManager.js:28-137; package.json:6-8
Description: Checkout validation, payment approval, and report aggregation are all anonymous logic inside route-handler closures, with no exported, independently testable function; `package.json` declares only a `start` script, no test runner.
Impact: Verifying any of these rules currently requires booting the whole application and issuing real HTTP requests — none can be covered by a fast, isolated unit test.
Recommendation: See `refactoring-playbook.md` PB-13 — extract business logic into testable Model/Service functions.

### [MEDIUM] Unchecked Error-First Callback Parameters (AP-12)
File: src/AppManager.js:92, 104, 106
Description: The `db.all`/`db.get` callbacks that build the financial report accept an `err` parameter but never check it before using `enrollments`/`user`/`payment`.
Impact: A failed query is silently treated as if it had returned valid data — at best an incomplete report, at worst an unhandled `TypeError`.
Recommendation: See `refactoring-playbook.md` PB-09 — promisify the database layer and refactor to `async`/`await`.

### [MEDIUM] N+1 Query Pattern (AP-13)
File: src/AppManager.js:83-125
Description: One query fetches all courses, then one additional query per course fetches enrollments, then one additional query per enrollment fetches the user and the payment — `1 + C + 2E` queries instead of one joined query.
Impact: Report latency grows linearly with the number of courses and enrollments instead of remaining roughly constant.
Recommendation: See `refactoring-playbook.md` PB-10 — replace N+1 queries with a single JOIN-based report query.

### [MEDIUM] Missing Referential Integrity (AP-14)
File: src/AppManager.js:12-16
Description: `enrollments.user_id`, `enrollments.course_id`, and `payments.enrollment_id` are declared as bare `INTEGER` with no `FOREIGN KEY` constraint anywhere in `initDb()`.
Impact: The database cannot prevent an enrollment or payment from referencing a deleted user or non-existent course — the already-observed orphaned-data behavior of AP-04 is a direct consequence.
Recommendation: See `refactoring-playbook.md` PB-11 — add foreign key constraints to the schema.

### [MEDIUM] Minimal Input Validation (AP-15)
File: src/AppManager.js:35
Description: Checkout validation is limited to a presence check (`if (!u || !e || !cid || !cc) ...`), with no format/type/range validation on email, course ID, or card number.
Impact: Malformed input reaches the database and payment-decision logic unvalidated, relying on incidental downstream failures rather than an explicit rejection.
Recommendation: See `refactoring-playbook.md` PB-12 — strengthen input validation in the checkout controller.

### [LOW] Dead/Unused Code (AP-16)
File: src/utils.js:10, 25; src/AppManager.js:2
Description: `totalRevenue` is declared, exported, and imported into `AppManager.js`, but never referenced anywhere else in that file.
Impact: A future reader could reasonably assume `totalRevenue` reflects real accumulated state, when it does not.
Recommendation: See `refactoring-playbook.md` PB-14 — remove dead code.

### [LOW] Magic Value (AP-17)
File: src/AppManager.js:46
Description: The literal `"4"` (a Visa card-number prefix, by convention) is compared directly with no named constant or comment.
Impact: A reader unfamiliar with card-network prefix conventions cannot tell what `"4"` represents without external knowledge.
Recommendation: See `refactoring-playbook.md`'s constant-extraction guidance alongside PB-07 (mock gateway isolation) — name the literal as a documented constant.

### [LOW] Poor/Abbreviated Variable Naming (AP-18)
File: src/AppManager.js:29-33
Description: `u`, `e`, `p`, `cid`, `cc` (username, email, password, course ID, card number) are used across roughly 45 lines of nested callbacks with no more descriptive naming.
Impact: Meaning must be inferred from the destructured `req.body` keys a few lines above every time the code is read.
Recommendation: See `refactoring-playbook.md` PB-15 — rename internal variables for clarity.

### [LOW] Inconsistent `this` Binding Strategy (AP-19)
File: src/AppManager.js:26, 37, 40, 50, 54
Description: The same method mixes a `self` alias, arrow-function lexical `this`, and a non-arrow `function` callback relying on the `sqlite3` driver's own `this` binding, with no comment explaining why each was chosen.
Impact: A maintainer changing one callback's arrow/function style without understanding the reason can silently break `this` resolution elsewhere in the chain.
Recommendation: See `refactoring-playbook.md` PB-16 — eliminate the need for manual `this` juggling.

### [INFO] Deprecated API Check
Description: verification of catalog entry AP-20 — no deprecated API found. `src/app.js:6` already uses the built-in `express.json()` middleware, and no call in `src/AppManager.js` or `src/utils.js` matches a known-deprecated Express 4.x or `sqlite3` ^5.x API at the versions declared in `package.json`.

================================
Total: 19 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

> **Note on subsequent execution:** this run's Phase 3 (MVC refactoring) was executed and committed separately; the project's current source tree (`src/config`, `src/models`, `src/services`, `src/controllers`, `src/routes`, `src/middlewares`, `src/database.js`, `src/cache.js`) reflects that completed refactoring, not the pre-refactoring state audited above.
