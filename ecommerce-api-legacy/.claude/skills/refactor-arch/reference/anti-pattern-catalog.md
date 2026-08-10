# Anti-Pattern Catalog — `ecommerce-api-legacy` (Phase 2)

Reference for **Phase 2 (Architecture Audit)**. Every entry below is grounded in this project's own audit (`comparative-audit-ecommerce-api-legacy.md`, findings G-001 through G-019) — nothing here was copied from another project's catalog; the detection signals point at this project's actual files (`src/AppManager.js`, `src/utils.js`, `package.json`).

## Severity scale (fixed — do not reinterpret)

- **CRITICAL** — directly exploitable security exposure (secrets, missing auth on a destructive/sensitive operation, sensitive data leakage, reversible "hashing") or a structural flaw that makes the rest of the codebase unsafe to change (a God Class owning every responsibility).
- **HIGH** — a correctness or maintainability defect with a realistic path to data corruption, financial/business-logic error, or an untestable codebase, but not immediately exploitable by an anonymous external request the way a CRITICAL is.
- **MEDIUM** — a defect that degrades reliability, performance, or data integrity under normal operation, without a direct security exposure.
- **LOW** — a defect confined to readability, consistency, or dead code, with no functional or security impact on its own.

Every entry declares exactly one severity. AP-20 is the only entry without a fixed severity, because it is a verification step, not a confirmed defect — see its own definition below.

## Evidence rule

An entry is only reported as a Phase 2 finding when the described signal is actually observed in the current code, with a real file and line citation. Do not report an entry "by category" — confirm it against the live file content at execution time.

---

### AP-01 — Hardcoded Secrets [CRITICAL]

**Detection signal:** a configuration object or module-level constant holding a database password, API key, or credential as a literal string, with no read from `process.env`.
**Reference evidence (audit time):** `src/utils.js:1-7` — `config.dbUser`, `config.dbPass`, `config.paymentGatewayKey`, and `config.smtpUser` are all literal strings committed to source, including what reads as a live payment-gateway key (`pk_live_...`).
**Why it matters:** anyone with read access to the repository (or a leaked build artifact) has production credentials; rotating a leaked secret requires a code change and redeploy instead of an environment update.

### AP-02 — Weak, Reversible Password Hashing [CRITICAL]

**Detection signal:** a hand-rolled "hash" function that does not call a real key-derivation/hash primitive (`crypto.scrypt`, `crypto.pbkdf2`, `bcrypt`, etc.) and does not use a per-user salt.
**Reference evidence (audit time):** `src/utils.js:17-23` (`badCrypto`) — repeats a Base64 encoding of the raw password 10,000 times and truncates the result to 10 characters. Base64 is an encoding, not a cryptographic hash; it is trivially reversible, and the loop only lengthens the string, it does not add cryptographic strength. There is no salt, so identical passwords always produce an identical stored value.
**Why it matters:** any database read (backup leak, injection, insider access) exposes passwords in a form that can be decoded directly, not just brute-forced.

### AP-03 — God Class [CRITICAL]

**Detection signal:** a single class or file that owns the database connection, schema definition, seed data, HTTP routing, and business logic for more than one domain, with no delegation to any other module.
**Reference evidence (audit time):** `src/AppManager.js:4-141` — `AppManager` owns the `sqlite3.Database` connection (constructor), defines and seeds the entire schema (`initDb`, lines 10-23), and registers and implements all 3 routes with their full business logic inline (`setupRoutes`, lines 25-138): checkout validation, user lookup/creation, payment approval, enrollment, audit logging, financial-report aggregation, and user deletion.
**Why it matters:** every change, regardless of which domain it touches, requires editing the same file and re-reasoning about the same 140-line method; there is no boundary that lets one domain be modified, tested, or reviewed independently of the others.

### AP-04 — Unauthenticated Destructive Endpoint [CRITICAL]

**Detection signal:** a route that performs a `DELETE`/destructive write with no authentication or authorization check before executing it.
**Reference evidence (audit time):** `src/AppManager.js:131-137` — `app.delete('/api/users/:id', ...)` deletes a row from `users` with no header check, no token, no session, reachable by any anonymous client that knows or guesses an ID.
**Why it matters:** any unauthenticated client can delete any user by ID; the handler's own response text ("as matrículas e pagamentos ficaram sujos no banco") confirms the team was aware the operation leaves orphaned data, yet shipped it with no access control at all.

### AP-05 — Sensitive Data Logged in Plaintext [CRITICAL]

**Detection signal:** a `console.log`/logging call that interpolates a full credit card number, credential, or secret key into the log line.
**Reference evidence (audit time):** `src/AppManager.js:45` — `` console.log(`Processando cartão ${cc} na chave ${config.paymentGatewayKey}`) `` prints the complete card number submitted by the client and the payment-gateway secret key on every checkout call.
**Why it matters:** anything with access to application logs (log aggregators, disk access, misconfigured log shipping) gains full card numbers and the gateway credential — a PCI-relevant exposure independent of the database itself.

### AP-06 — Global Mutable State [HIGH]

**Detection signal:** a module-level `let`/`var` object exported directly and mutated by any importer, with no accessor boundary or encapsulation.
**Reference evidence (audit time):** `src/utils.js:9` (`let globalCache = {}`) and `:12-15` (`logAndCache` mutates it directly); it is exported as-is at `:25`, so any future importer can also assign into it or overwrite it entirely.
**Why it matters:** state shared this way has no single owner; two unrelated call sites can race on the same key, and there is no way to reset, inspect, or bound the cache's size without touching every call site that happens to import it.

### AP-07 — Unvalidated Fake Payment Gateway Logic [HIGH]

**Detection signal:** a "payment approval" decision made from a superficial property of client input (a prefix, a length) with no call to an actual payment processor and no real card validation.
**Reference evidence (audit time):** `src/AppManager.js:46` — `` let status = cc.startsWith("4") ? "PAID" : "DENIED" `` approves or denies a payment based solely on whether the card number starts with the digit `4`; the card number is never checked for length, digit format (Luhn), or expiry, and no external gateway is called.
**Why it matters:** this is not a payment integration, it is a placeholder that will approve any 16 arbitrary digits starting with `4`; treating this as production payment logic (as the `pk_live_...` key in AP-01 suggests it might be) would approve fraudulent charges by construction.

### AP-08 — Insecure Default Credential Fallback [HIGH]

**Detection signal:** a password/credential parameter that, when absent from the request, is silently replaced with a fixed, guessable literal instead of being rejected.
**Reference evidence (audit time):** `src/AppManager.js:68` — `` badCrypto(p || "123456") `` assigns the literal password `123456` to any newly created account whose request omitted `pwd`.
**Why it matters:** every account created without a password is protected by the same publicly-known string; there is no client-visible signal that this happened, since the checkout call still returns `200`.

### AP-09 — Deeply Nested Callback Structure ("Callback Hell") [HIGH]

**Detection signal:** more than 3 levels of nested callback functions handling a single logical operation, where each level's control flow (branching, error handling) depends on correctly closing over the outer scope.
**Reference evidence (audit time):** `src/AppManager.js:37-77` — the checkout handler nests `db.get` (course lookup) → `db.get` (user lookup) → `db.run` (user creation, conditional) → `db.run` (enrollment insert) → `db.run` (payment insert) → `db.run` (audit log insert), five levels deep, before a response is ever sent. `src/AppManager.js:83-127` repeats the pattern for the financial report (see AP-13).
**Why it matters:** every branch (course not found, user not found vs. found, payment denied, each DB error) is handled at a different nesting depth with a different closure scope, which is what allows AP-10 and AP-12 to happen — it is very easy to reference the wrong `err`/variable or to forget an error check at one specific depth without it being visually obvious.

### AP-10 — Race-Condition-Prone Manual Async Completion Tracking [HIGH]

**Detection signal:** a hand-maintained counter (`pendingX--`) used to decide when a set of concurrent async callbacks has "all finished," instead of a coordination primitive (`Promise.all`, an async iteration with `await`).
**Reference evidence (audit time):** `src/AppManager.js:86` (`coursesPending`), `:93` (`enrPending`) — both counters are decremented inside callbacks that fire concurrently (one per course, one per enrollment) and are compared to `0` to decide when to call `res.json(report)`. Because the callbacks at `:104` and `:106` never check their own `err` parameter, a failed query still reaches the decrement at `:117`/`:120` as if it had succeeded — the counter has no way to distinguish "succeeded" from "failed but still decremented."
**Why it matters:** under concurrent execution this pattern is a source of double-responses, hangs (if a callback that should decrement never fires), or a response sent with silently-incomplete data — none of which raise an exception that would surface the bug during manual testing.

### AP-11 — Business Logic Coupled to the HTTP Layer [HIGH]

**Detection signal:** business rules (validation, decision logic, aggregation) implemented directly inside a route handler's closure, with no function that can be invoked or unit-tested without going through `req`/`res`; confirmed by the absence of a test runner/dependency.
**Reference evidence (audit time):** `src/AppManager.js:28-137` — checkout validation, payment approval, and report aggregation are all anonymous logic inside `app.post(...)`/`app.get(...)`/`app.delete(...)` callbacks, not named, exported functions. `package.json:6-8` confirms there is only a `start` script and no test-related dependency (`jest`, `mocha`, `ava`, `supertest`, etc.) — consistent with logic that cannot be exercised without a running HTTP server.
**Why it matters:** verifying the payment-approval rule, the validation rule, or the report aggregation currently requires booting the whole application and issuing real HTTP requests; none of these rules can be covered by a fast, isolated unit test.

### AP-12 — Unchecked Error-First Callback Parameters [MEDIUM]

**Detection signal:** a Node-style `(err, result) => {}` callback where `err` is accepted as a parameter but never checked before `result` is used.
**Reference evidence (audit time):** `src/AppManager.js:92` (`this.db.all(..., (err, enrollments) => { let enrPending = enrollments.length; ...` — `enrollments` is used immediately with no `if (err)` guard), `:104` and `:106` (same pattern for the user and payment lookups inside the report loop).
**Why it matters:** if any of these three queries fails, the callback proceeds as if it had returned an empty/undefined result — at best producing an incomplete report with no error signal, at worst throwing an unhandled `TypeError` when `enrollments.length` is read on `undefined`.

### AP-13 — N+1 Query Pattern [MEDIUM]

**Detection signal:** one query to fetch a parent collection, followed by one additional query per parent row (and, nested further, one more query per child row) to fetch related data that a single JOIN could return.
**Reference evidence (audit time):** `src/AppManager.js:83-125` — one `SELECT * FROM courses` (line 83), then inside `courses.forEach`, one `SELECT * FROM enrollments WHERE course_id = ?` per course (line 92), then inside `enrollments.forEach`, one `SELECT ... FROM users` (line 104) and one `SELECT ... FROM payments` (line 106) per enrollment. For C courses and E total enrollments this issues `1 + C + 2E` queries instead of one joined query.
**Why it matters:** report latency grows linearly with the number of courses and enrollments instead of being a single roughly-constant-cost query; at even a moderate data volume this becomes the dominant cost of the endpoint.

### AP-14 — Missing Referential Integrity [MEDIUM]

**Detection signal:** a foreign-key-shaped column (`*_id`) declared as a plain `INTEGER` with no `REFERENCES`/`FOREIGN KEY` clause tying it to the parent table.
**Reference evidence (audit time):** `src/AppManager.js:12-16` — `enrollments.user_id`, `enrollments.course_id`, and `payments.enrollment_id` are all declared as bare `INTEGER`, with no `FOREIGN KEY` constraint anywhere in `initDb()`.
**Why it matters:** the database itself cannot prevent an enrollment from pointing at a deleted user or a non-existent course; AP-04's unauthenticated `DELETE /api/users/:id` is a direct, already-observed way to produce exactly this orphaned state, and the handler's own response text acknowledges it happens.

### AP-15 — Minimal Input Validation [MEDIUM]

**Detection signal:** request-body validation limited to a truthiness/presence check (`if (!x) ...`), with no format, type, or range validation on fields whose shape matters (email, numeric ID, card number).
**Reference evidence (audit time):** `src/AppManager.js:35` — `` if (!u || !e || !cid || !cc) return res.status(400).send("Bad Request") `` only rejects empty/missing values; `e` is never checked for an email-like shape, `cid` is never checked to be numeric, and `cc` is never checked for length or digit-only format before being used as a card number.
**Why it matters:** malformed input (a non-numeric `c_id`, a non-email `eml`, a `card` value with letters) reaches the database layer and the payment-decision logic unvalidated, relying on incidental failures downstream rather than an explicit, intentional rejection.

### AP-16 — Dead/Unused Code [LOW]

**Detection signal:** a value declared, exported, and imported, but never read or written anywhere in the importing module.
**Reference evidence (audit time):** `src/utils.js:10` (`let totalRevenue = 0`) and `:25` (exported) — imported at `src/AppManager.js:2` but never referenced anywhere else in that file.
**Why it matters:** the name suggests a revenue-tracking feature that does not actually exist; a future reader (or an AI-assisted refactor) could reasonably assume `totalRevenue` reflects real state and build on that false assumption.

### AP-17 — Magic Value [LOW]

**Detection signal:** a literal used to encode a business rule (a status code, a prefix, a threshold) with no named constant and no comment explaining its meaning.
**Reference evidence (audit time):** `src/AppManager.js:46` — the literal `"4"` (a Visa card-number prefix, by convention) is compared directly against `cc.startsWith(...)` with no constant name or comment.
**Why it matters:** a reader unfamiliar with card-network prefix conventions cannot tell what `"4"` means or that it is meant to represent "Visa" without cross-referencing external knowledge.

### AP-18 — Poor/Abbreviated Variable Naming [LOW]

**Detection signal:** single-letter or heavily abbreviated local variable names for values that persist across more than a couple of lines, obscuring their meaning without an IDE/type hint.
**Reference evidence (audit time):** `src/AppManager.js:29-33` — `u`, `e`, `p`, `cid`, `cc` for username, email, password, course ID, and card number, respectively, each used across the following ~45 lines of nested callbacks.
**Why it matters:** the abbreviations are not consistent with any project-wide convention (contrast with the equally short but at least descriptive `req`/`res`), and their meaning must be inferred from the destructured `req.body` keys a few lines above every time the code is read.

### AP-19 — Inconsistent `this` Binding Strategy [LOW]

**Detection signal:** the same method mixing more than one strategy for accessing the enclosing instance (`self` alias, arrow-function lexical `this`, and a `function` expression relying on a callback library's own `this` binding) with no comment explaining why each was chosen.
**Reference evidence (audit time):** `src/AppManager.js:26` (`const self = this;`), used together with direct `this.db...` calls inside arrow-function callbacks (e.g., `:37`, `:40`) that already close over `AppManager`'s `this`, while `:50` and `:54` use non-arrow `function(err) {}` callbacks specifically to access `this.lastID` (the `sqlite3` driver's own per-statement binding) and fall back to `self.db...` inside those same callbacks to reach the outer instance.
**Why it matters:** three different `this`-resolution strategies are active in the same 40-line method for three different reasons, none of which are documented; a maintainer changing one callback's arrow/function style without understanding why it was chosen can silently break `self`/`this` resolution elsewhere in the chain.

### AP-20 — Deprecated API Usage [structural — verify, do not assume]

**Detection signal:** any call into an Express or `sqlite3` API that is documented as deprecated in the major version declared in `package.json` (e.g., a body-parsing pattern predating `express.json()`, a `sqlite3` method removed or replaced in a later major version).
**Reference evidence (audit time):** not applicable — `src/app.js:6` already uses the built-in `express.json()` middleware (not the deprecated third-party `body-parser` pattern), and no other call in `src/AppManager.js` or `src/utils.js` matches a known-deprecated Express 4.x or `sqlite3` ^5.x API at the versions declared in `package.json`.
**Why it has no fixed severity:** this entry exists to force an explicit, current check against the dependency versions actually installed at execution time, not to record a pre-decided defect — if a Phase 2 run finds a real deprecated call, assign its severity using the general scale above based on the concrete consequence (a HIGH if the deprecated call is scheduled for removal in the next major version already targeted by `package.json`'s caret range; a LOW if it is deprecated but stable).

---

## Coverage summary

20 entries: 5 CRITICAL (AP-01…AP-05), 6 HIGH (AP-06…AP-11), 4 MEDIUM (AP-12…AP-15), 4 LOW (AP-16…AP-19), 1 structural/no-fixed-severity (AP-20). Together they account for all 19 confirmed findings of the `ecommerce-api-legacy` comparative audit (G-001 through G-019); no G-finding was left uncataloged, and no entry here was invented beyond what that audit confirmed with evidence.
