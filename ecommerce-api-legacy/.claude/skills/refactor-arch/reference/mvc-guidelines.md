# Target MVC Architecture Guidelines — `ecommerce-api-legacy`

Defines the target structure for **Phase 3 (MVC Refactoring)**. The structure below is the only one accepted as the outcome of this project's refactoring. It is designed from scratch for this project's actual stack (Node.js/Express/`sqlite3`) and does not reuse or mirror any file from another project's Skill.

## Target directory structure

```
ecommerce-api-legacy/
├── src/
│   ├── config/
│   │   └── settings.js
│   ├── database.js
│   ├── cache.js
│   ├── models/
│   │   ├── userModel.js
│   │   ├── courseModel.js
│   │   ├── enrollmentModel.js
│   │   ├── paymentModel.js
│   │   ├── auditLogModel.js
│   │   └── reportModel.js
│   ├── services/
│   │   └── paymentGateway.js
│   ├── controllers/
│   │   ├── checkoutController.js
│   │   ├── userController.js
│   │   └── reportController.js
│   ├── routes/
│   │   ├── checkoutRoutes.js
│   │   ├── userRoutes.js
│   │   └── reportRoutes.js
│   ├── middlewares/
│   │   ├── errorHandler.js
│   │   └── adminAuth.js
│   └── app.js
├── package.json
└── package-lock.json
```

**No shim needed at the project root.** Unlike a stack where the start command runs a file at the repository root, this project's `package.json` already points at `src/app.js` (`"main": "src/app.js"`, `"scripts": { "start": "node src/app.js" }`). `src/app.js` simply becomes the composition root instead of a thin delegator — `npm start` keeps working unchanged, with no extra indirection file required.

**Retiring the old flat files:** once its logic has a confirmed equivalent inside the structure above, each original file must be removed, not left behind — `src/AppManager.js` is exactly the God Class this refactoring exists to eliminate (AP-03), and `src/utils.js` is the source of AP-01, AP-02, and AP-06. Leaving either in place after the migration would mean the hardcoded secrets, the fake hash, and the unencapsulated global cache are still reachable from the codebase even if nothing imports them anymore. Concretely:

- Delete `src/AppManager.js` and `src/utils.js` after their logic has a confirmed equivalent under `src/config/`, `src/database.js`, `src/cache.js`, `src/models/`, `src/services/`, `src/controllers/`, and `src/routes/`.
- Keep only `src/app.js` as the composition root; every other piece of logic lives in the files above it.

## Responsibility of each layer

### `config/settings.js`

The only place in the project that reads `process.env` and defines configuration values — replaces the hardcoded literals in the old `utils.js` config object (resolves AP-01). Exposes `port`, `dbUser`, `dbPass`, `paymentGatewayKey`, `smtpUser` (read from environment variables, falling back to the original literal values only as local-development defaults so the app keeps booting unchanged in an environment with no `.env` configured) and `adminToken` (a new value, read from `process.env.ADMIN_TOKEN`, used by `middlewares/adminAuth.js` — see below). No other file may contain a configuration literal.

### `database.js`

The single database-connection module. It is the only file, besides the files inside `models/`, allowed to `require('sqlite3')` or hold a reference to the `Database` instance. It wraps the driver's callback-based API (`db.get`, `db.all`, `db.run`) with `util.promisify`-based helpers (`dbGet`, `dbAll`, `dbRun`) so every model can use `async`/`await` instead of nested callbacks (resolves AP-09 directly, and AP-12 as a consequence — a promisified call either resolves with a real result or rejects, so there is no way to "forget" to check `err`; a rejection either propagates to `await` inside a `try/catch` or, if unhandled, terminates the request through `errorHandler`, it can never silently continue with an `undefined` result the way the raw callback did). It also owns schema creation (`initSchema()`), now including `FOREIGN KEY` constraints on every `*_id` column (resolves AP-14), and seed data (`seed()`), both called once from `app.js` at boot — this is a superset of what `AppManager.initDb()` did, kept in the same place because the connection and the schema it holds are the same concern.

### `cache.js`

Replaces the loose, directly-exported `globalCache` object from `utils.js` (resolves AP-06). Encapsulates the cache behind a small class with `get(key)`/`set(key, value)` methods and a private internal `Map`; a single instance is created once and exported. The observable behavior is unchanged — the same `[LOG] Salvando no cache: <key>` line is still logged on every `set`, and the same `last_checkout_<userId>` key is still written during checkout — but nothing outside `cache.js` can reach into the underlying storage directly or reassign it wholesale. Like `config/settings.js`, `cache.js` is a small cross-cutting infrastructure utility, not a domain model: it holds no persistent business data (only ephemeral, in-memory runtime state) and owns no `*_id`/table, so it does not belong inside `models/`. It may be imported directly by whichever layer needs it — in this project, that is `controllers/checkoutController.js` (see `refactoring-playbook.md` PB-09), not a model — the same way `middlewares/adminAuth.js` imports `config/settings.js` directly without going through a model.

### `models/*.js`

One file per domain (user, course, enrollment, payment, audit log, plus a dedicated `reportModel.js` for the one query that spans all of them — resolves AP-03). Each model file contains **only**:

- Data-access functions built on `database.js`'s promisified helpers, using parameterized queries (already true in the original code and preserved as-is).
- No HTTP input-format validation (that is the Controller's responsibility) and no routing logic.
- `userModel.js` is responsible for hashing/verifying passwords via `crypto.scryptSync` with a per-user salt (resolves AP-02) and must never return the `pass` column value out to a controller in a form meant for the HTTP response.
- `reportModel.js` answers the financial-report query with a single SQL statement using `JOIN`s and `GROUP BY` (resolves AP-13) instead of the nested per-row queries from the original code — see `refactoring-playbook.md` PB-10 for the exact statement.
- `enrollmentModel.js` and `paymentModel.js` each expose a single `create(...)` function with no manual pending-counter logic anywhere in either file (resolves AP-10, together with the `async`/`await` sequencing described under `database.js` above and in `refactoring-playbook.md` PB-09).

### `services/paymentGateway.js`

A single, clearly isolated module for the payment-approval decision (resolves AP-07 and AP-17). It still does not call a real external payment processor — no such integration exists anywhere in the original project and adding one is out of scope for this refactoring — but the mock decision logic is now: (a) isolated in one named, documented function (`charge({ cardNumber })`) instead of inline in a route handler; (b) explicit that it is a mock (a comment and a distinct return shape make this unambiguous to any future reader); (c) built on a named constant instead of the bare literal `"4"` (resolves AP-17); (d) free of the plaintext logging of the card number and the gateway key that the original inline version performed (resolves AP-05, together with `config/settings.js` no longer being read directly inside a `console.log`).

### `controllers/*.js`

One file per domain. Each controller function:

- Parses and validates the HTTP input — course ID is numeric, email contains `@`, card is digits-only with a plausible length, and password is required specifically when the referenced user does not yet exist (resolves AP-15 and AP-08; see `refactoring-playbook.md` PB-08 and PB-12 for the exact validation and the one documented contract change this introduces).
- Calls the matching Model(s) and Service, never `sqlite3` directly (no controller may `require('sqlite3')`).
- Formats the HTTP response. The project's existing response shapes (`{ msg, enrollment_id }` for checkout, a plain-text body for the delete confirmation and for the 4xx/5xx error paths) are preserved as-is — no new response envelope is introduced, since standardizing the response shape across endpoints was not a finding confirmed by this project's audit and is out of scope for this refactoring.
- Must not contain a generic per-function `try/catch` that swallows the error silently — unexpected errors thrown by an `await`ed model/service call must propagate to `next(err)` and be handled centrally by `errorHandler` (resolves the unhandled-rejection risk that AP-12's unchecked-`err` pattern created); business-rule outcomes that already have a defined HTTP status in the original contract (course not found → 404, payment denied → 400) are still handled explicitly inside the controller, which is not the same thing as catching a generic exception.
- `userController.js`'s delete handler is the one that sits behind `adminAuth` (see below) and still returns the original confirmation text.

### `routes/*.js`

One file per domain, each creating an `express.Router()` and registering its route(s) exclusively through `router.get/post/delete(...)`. A route file **only** wires a path/method to the matching Controller function (and, for the delete route, the `adminAuth` middleware); it must not contain validation logic, data access, or response formatting.

### `middlewares/errorHandler.js`

A standard Express 4-argument error-handling middleware (`(err, req, res, next) => {}`), registered last in `app.js`. The only place that decides the shape of an unhandled error response — a generic `500` with a safe message (never the raw `err.stack`/`err.message` sent to the client), and it always logs the real error internally via `console.error` so the failure is still observable in server logs.

### `middlewares/adminAuth.js`

A minimal guard for the one destructive route identified by the audit: validates an `X-Admin-Token` header against `adminToken` from `config/settings.js`; if missing or incorrect, it responds `401` before any data access happens (resolves AP-04). This is not a full user-authentication system — it is the minimal mitigation, proportional to this project's scope, for the one CRITICAL finding that concerns missing access control. `GET /api/admin/financial-report` is **not** placed behind this guard: the audit (G-001 through G-019) did not confirm missing authentication on that endpoint as a finding, and adding a new access-control requirement to an endpoint with no corresponding audit finding would be scope creep beyond what Phase 2 confirmed — this gap is called out explicitly in the Phase 3 summary as a known, out-of-scope observation rather than silently left unmentioned. Do not introduce login, sessions, or JWTs here — that is out of scope for this refactoring.

### `app.js` (composition root)

Creates the Express app, loads `config/settings.js`, calls `database.js`'s `initSchema()`/`seed()` once at boot, registers the routers from `routes/`, registers `errorHandler` last, and starts the server on `config.port`. It is the only place that knows about every piece — no layer imports any layer other than the one immediately below it (Routes never import Models directly; Controllers never register routes; Models never import Controllers).

## Layer dependency rules (do not violate)

```
routes/        → controllers/                 (a route calls a controller)
controllers/   → models/, services/, cache.js  (a controller calls a model, the payment service, and/or the cache utility)
models/        → database.js                   (a model asks the connection module for data)
services/      → nothing above it              (paymentGateway.js has no dependency on models, routes, or controllers)
cache.js       → nothing above it               (a small, self-contained infrastructure utility, like config/settings.js)
database.js    → nothing above it
app.js         → routes/, middlewares/, config/, database.js, models/ (composes everything, including reading userModel.hashPassword once at boot to seed the database — see refactoring-playbook.md PB-09)
```

`cache.js` and `config/settings.js` are the two infrastructure utilities in this project with no domain data of their own; either may be imported directly by `controllers/`, `models/`, or `middlewares/` as needed, the same way a logging or environment-configuration utility would be in any layered design — this is distinct from `database.js`, which only `models/` may reach into.

No file outside `database.js` and `models/` may `require('sqlite3')` or hold a reference to the database connection directly.

## Execution compatibility

`npm install && npm start` must keep working exactly as documented in the project's `README.md`, booting on `http://localhost:3000`. Every original route must keep existing and responding:

- `POST /api/checkout` — same request shape (`usr`, `eml`, `pwd`, `c_id`, `card`), same success response shape (`{ msg: "Sucesso", enrollment_id: <id> }`), **with one documented contract change**: if the referenced user does not exist yet and `pwd` is missing/empty, the request now returns `400` instead of silently creating the account with the password `123456` — this change is required to eliminate AP-08 and is the only behavioral change on this route.
- `GET /api/admin/financial-report` — same response shape (an array of `{ course, revenue, students }`), computed correctly instead of via unchecked, racy nested callbacks; no new access-control requirement is added here (see `middlewares/adminAuth.js` above).
- `DELETE /api/users/:id` — same confirmation text on success, **with one documented contract change**: the request now requires a valid `X-Admin-Token` header and returns `401` without it — this change is required to eliminate AP-04 and is the only behavioral change on this route.

No other route path, method, or response shape may change as a side effect of this refactoring.
