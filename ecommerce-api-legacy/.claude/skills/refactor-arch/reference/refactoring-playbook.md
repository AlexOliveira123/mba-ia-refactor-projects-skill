# Refactoring Playbook — `ecommerce-api-legacy`

Concrete transformations for **Phase 3 (MVC Refactoring)**. Every "Before" snippet below is the real, current content of `src/AppManager.js` or `src/utils.js` at the audit's line numbers; every "After" snippet is new code written for this project's target structure (`mvc-guidelines.md`). Nothing here was copied from another project's playbook.

At execution time, re-read the current file before applying a transformation — if a previous partial refactor already changed the line numbers cited here, adapt the entry's intent to the current state of the code rather than applying it blindly.

---

## PB-01 — Centralize Configuration via Environment Variables

**Resolves:** AP-01 (Hardcoded Secrets)

**Before** (`src/utils.js:1-7`):
```js
const config = {
    dbUser: "admin_master",
    dbPass: "senha_super_secreta_prod_123", 
    paymentGatewayKey: "pk_live_1234567890abcdef",
    smtpUser: "no-reply@fullcycle.com.br",
    port: 3000
};
```

**After** (`src/config/settings.js`):
```js
const config = {
  port: Number(process.env.PORT) || 3000,
  dbUser: process.env.DB_USER || 'admin_master',
  dbPass: process.env.DB_PASS || 'senha_super_secreta_prod_123',
  paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY || 'pk_live_1234567890abcdef',
  smtpUser: process.env.SMTP_USER || 'no-reply@fullcycle.com.br',
  adminToken: process.env.ADMIN_TOKEN || 'change-me-admin-token',
};

module.exports = config;
```

The literal values are kept only as local-development fallbacks so the application keeps booting unchanged in an environment with no `.env` configured (same runtime behavior as today); in any environment where the corresponding variable is set, the environment value wins and the secret is no longer sourced from committed code. `adminToken` is a new value introduced for PB-04.

---

## PB-02 — Replace `badCrypto` with Salted `crypto.scryptSync` Hashing

**Resolves:** AP-02 (Weak, Reversible Password Hashing)

**Before** (`src/utils.js:17-23`):
```js
function badCrypto(pwd) {
    let hash = "";
    for(let i = 0; i < 10000; i++) {
        hash += Buffer.from(pwd).toString('base64').substring(0, 2);
    }
    return hash.substring(0, 10);
}
```

**After** (`src/models/userModel.js`, excerpt):
```js
const crypto = require('crypto');

function hashPassword(password) {
  const salt = crypto.randomBytes(16).toString('hex');
  const derivedKey = crypto.scryptSync(password, salt, 64);
  return `${salt}:${derivedKey.toString('hex')}`;
}

function verifyPassword(password, stored) {
  const [salt, storedHex] = stored.split(':');
  const derivedKey = crypto.scryptSync(password, salt, 64);
  const storedBuffer = Buffer.from(storedHex, 'hex');
  return derivedKey.length === storedBuffer.length && crypto.timingSafeEqual(derivedKey, storedBuffer);
}
```

`crypto` is a Node.js built-in module — no new npm dependency is introduced. The salt is stored alongside the derived key inside the existing `pass TEXT` column (`"<saltHex>:<hashHex>"`), so no schema change is required and the wire contract (nothing about the password is ever returned to a client) is unaffected. `verifyPassword` is exported for future use even though, as in the original code, no route currently checks an existing user's password — see PB-13 for why this asymmetry is preserved rather than "fixed" here.

---

## PB-03 — Split the God Class by Domain

**Resolves:** AP-03 (God Class)

**Before** (`src/AppManager.js:1-8`, class shape):
```js
const sqlite3 = require('sqlite3').verbose();
const { config, logAndCache, badCrypto, totalRevenue } = require('./utils');

class AppManager {
    constructor() {
        this.db = new sqlite3.Database(':memory:');
    }
    // initDb(), setupRoutes(app) — schema, seed, routing, and all business logic follow
```

**After** (`src/app.js`, composition root):
```js
const express = require('express');
const settings = require('./config/settings');
const database = require('./database');
const userModel = require('./models/userModel');
const checkoutRoutes = require('./routes/checkoutRoutes');
const userRoutes = require('./routes/userRoutes');
const reportRoutes = require('./routes/reportRoutes');
const errorHandler = require('./middlewares/errorHandler');

async function start() {
  const app = express();
  app.use(express.json());

  await database.initSchema();
  await database.seed({ seedUserPasswordHash: userModel.hashPassword('123') });

  app.use('/api/checkout', checkoutRoutes);
  app.use('/api/users', userRoutes);
  app.use('/api/admin', reportRoutes);

  app.use(errorHandler);

  app.listen(settings.port, () => {
    console.log(`Frankenstein LMS rodando na porta ${settings.port}...`);
  });
}

start();

module.exports = { start };
```

`AppManager`'s four responsibilities (connection ownership, schema/seed, routing, business logic) now live in four different places: `database.js` (connection + schema + seed), `routes/*.js` (routing only), `controllers/*.js` (orchestration), and `models/*.js`/`services/*.js` (business/data logic) — see PB-09 through PB-13 for each of those files in full. `src/app.js` remains the entry point `npm start` already targets (`package.json`'s `main`/`start` both point at `src/app.js`), so no root-level shim file is needed.

---

## PB-04 — Guard the Destructive Endpoint with an Admin-Token Middleware

**Resolves:** AP-04 (Unauthenticated Destructive Endpoint)

**Before** (`src/AppManager.js:131-137`):
```js
app.delete('/api/users/:id', (req, res) => {
    let id = req.params.id;
    this.db.run("DELETE FROM users WHERE id = ?", [id], (err) => {
        res.send("Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco.");
    });
});
```

**After** (`src/middlewares/adminAuth.js`):
```js
const { adminToken } = require('../config/settings');

function adminAuth(req, res, next) {
  const token = req.get('X-Admin-Token');
  if (!token || token !== adminToken) {
    return res.status(401).send('Unauthorized');
  }
  next();
}

module.exports = adminAuth;
```

**After** (`src/routes/userRoutes.js`):
```js
const express = require('express');
const adminAuth = require('../middlewares/adminAuth');
const userController = require('../controllers/userController');

const router = express.Router();

router.delete('/:id', adminAuth, userController.remove);

module.exports = router;
```

**After** (`src/controllers/userController.js`):
```js
const userModel = require('../models/userModel');

async function remove(req, res, next) {
  try {
    await userModel.remove(req.params.id);
    res.send('Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco.');
  } catch (err) {
    next(err);
  }
}

module.exports = { remove };
```

This is a minimal, proportional mitigation (a shared static token), not a full user-authentication system — consistent with `mvc-guidelines.md`'s explicit statement that login/sessions/JWTs are out of scope. The success response text is preserved verbatim.

---

## PB-05 — Stop Logging Sensitive Payment Data

**Resolves:** AP-05 (Sensitive Data Logged in Plaintext)

**Before** (`src/AppManager.js:45`):
```js
console.log(`Processando cartão ${cc} na chave ${config.paymentGatewayKey}`);
let status = cc.startsWith("4") ? "PAID" : "DENIED";
```

**After** (`src/services/paymentGateway.js`, see PB-07 for the full file): the card number and the gateway key are never passed to `console.log`; the only logging this module performs, if any, would be a non-sensitive event (e.g., an approval/denial outcome with no card digits), and none is strictly necessary to preserve the original observable behavior, so none is added.

---

## PB-06 — Encapsulate the Cache Behind a Small Class

**Resolves:** AP-06 (Global Mutable State)

**Before** (`src/utils.js:9,12-15`):
```js
let globalCache = {};
...
function logAndCache(key, data) {
    console.log(`[LOG] Salvando no cache: ${key}`);
    globalCache[key] = data;
}
```

**After** (`src/cache.js`):
```js
class Cache {
  constructor() {
    this._store = new Map();
  }

  set(key, value) {
    console.log(`[LOG] Salvando no cache: ${key}`);
    this._store.set(key, value);
  }

  get(key) {
    return this._store.get(key);
  }
}

module.exports = new Cache();
```

A single instance is created once and exported (still one shared cache for the process, matching the original's single `globalCache` object), but the underlying `Map` is private to the module — nothing outside `cache.js` can reassign or directly mutate it. The exact log line and cache key format (`last_checkout_<userId>`) are preserved; see PB-09 for the call site.

---

## PB-07 — Isolate the Mock Payment Gateway into Its Own Service

**Resolves:** AP-07 (Unvalidated Fake Payment Gateway Logic), AP-17 (Magic Value)

**Before** (`src/AppManager.js:46`):
```js
let status = cc.startsWith("4") ? "PAID" : "DENIED";
```

**After** (`src/services/paymentGateway.js`):
```js
const VISA_PREFIX = '4';

/**
 * Mock payment approval. This is NOT a real payment-gateway integration —
 * the original project never called an external processor, and adding one
 * is out of scope for this refactoring. This module exists to isolate the
 * mock decision behind one named, documented boundary instead of leaving it
 * inline inside a route handler, so a real integration can later replace
 * only this file without touching any controller or model.
 */
function charge({ cardNumber }) {
  const status = cardNumber.startsWith(VISA_PREFIX) ? 'PAID' : 'DENIED';
  return { status };
}

module.exports = { charge, VISA_PREFIX };
```

The decision logic is unchanged (still a prefix check, still a mock) — this transformation is about isolation and honesty about what the module is, not about adding real payment processing, which is out of scope.

---

## PB-08 — Require the Password Explicitly When Creating a New Account

**Resolves:** AP-08 (Insecure Default Credential Fallback)

**Before** (`src/AppManager.js:66-72`):
```js
if (!user) {
    let hash = badCrypto(p || "123456");
    this.db.run("INSERT INTO users (name, email, pass) VALUES (?, ?, ?)", [u, e, hash], function(err) {
        if (err) return res.status(500).send("Erro ao criar usuário");
        processPaymentAndEnroll(this.lastID);
    });
} else {
    processPaymentAndEnroll(user.id);
}
```

**After** (`src/controllers/checkoutController.js`, excerpt — full file in PB-09):
```js
if (!user) {
  if (!input.password) {
    return res.status(400).send('Senha é obrigatória para criar uma conta');
  }
  const hashedPassword = userModel.hashPassword(input.password);
  const { lastID } = await userModel.create({
    name: input.username,
    email: input.email,
    hashedPassword,
  });
  userId = lastID;
} else {
  userId = user.id;
}
```

**Documented contract change:** a checkout for a new email with no `pwd` now returns `400` instead of `200` with a silently-assigned `"123456"` password. This is the one behavioral change required to eliminate AP-08, called out explicitly in `mvc-guidelines.md`'s "Execution compatibility" section.

---

## PB-09 — Promisify the Database Layer and Refactor to `async`/`await`

**Resolves:** AP-09 (Callback Hell), AP-10 (Race-Condition-Prone Manual Async Counters), AP-12 (Unchecked Error-First Callback Parameters)

**Before** (`src/AppManager.js:37-77`, checkout — 5 levels of nested callbacks) and (`src/AppManager.js:83-127`, report — nested callbacks plus `coursesPending`/`enrPending` counters with unchecked `err` at lines 92, 104, 106). See the full original text in `project-analysis.md`'s referenced source or the live file; it is not repeated here in full to keep this entry focused on the transformation.

**After** (`src/database.js` — the promisified wrapper every model builds on):
```js
const sqlite3 = require('sqlite3').verbose();

const db = new sqlite3.Database(':memory:');

function dbGet(sql, params = []) {
  return new Promise((resolve, reject) => {
    db.get(sql, params, (err, row) => (err ? reject(err) : resolve(row)));
  });
}

function dbAll(sql, params = []) {
  return new Promise((resolve, reject) => {
    db.all(sql, params, (err, rows) => (err ? reject(err) : resolve(rows)));
  });
}

function dbRun(sql, params = []) {
  return new Promise((resolve, reject) => {
    // A plain `function` expression (not an arrow function) is required here:
    // the sqlite3 driver binds `this.lastID`/`this.changes` on the callback's
    // own `this`, and that binding only happens for non-arrow functions. This
    // is the one, documented place in the whole project where that quirk is
    // handled — see PB-16 for why it no longer needs to leak into business logic.
    db.run(sql, params, function callback(err) {
      if (err) return reject(err);
      resolve({ lastID: this.lastID, changes: this.changes });
    });
  });
}

function initSchema() {
  return new Promise((resolve, reject) => {
    db.serialize(() => {
      // SQLite does not enforce declared FOREIGN KEY constraints unless this
      // pragma is turned on for the connection — without it, the constraints
      // added below would be documentation only, not an enforced rule (resolves
      // AP-14 completely, not just at the schema-declaration level).
      db.run('PRAGMA foreign_keys = ON');
      db.run('CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, pass TEXT)');
      db.run('CREATE TABLE courses (id INTEGER PRIMARY KEY, title TEXT, price REAL, active INTEGER)');
      db.run(`CREATE TABLE enrollments (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        course_id INTEGER,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (course_id) REFERENCES courses(id)
      )`);
      db.run(`CREATE TABLE payments (
        id INTEGER PRIMARY KEY,
        enrollment_id INTEGER,
        amount REAL,
        status TEXT,
        FOREIGN KEY (enrollment_id) REFERENCES enrollments(id)
      )`);
      db.run('CREATE TABLE audit_logs (id INTEGER PRIMARY KEY, action TEXT, created_at DATETIME)', (err) => {
        if (err) return reject(err);
        resolve();
      });
    });
  });
}

function seed({ seedUserPasswordHash }) {
  return dbRun('INSERT INTO users (name, email, pass) VALUES (?, ?, ?)', [
    'Leonan', 'leonan@fullcycle.com.br', seedUserPasswordHash,
  ])
    .then(() => dbRun("INSERT INTO courses (title, price, active) VALUES ('Clean Architecture', 997.00, 1), ('Docker', 497.00, 1)"))
    .then(() => dbRun('INSERT INTO enrollments (user_id, course_id) VALUES (1, 1)'))
    .then(({ lastID }) => dbRun('INSERT INTO payments (enrollment_id, amount, status) VALUES (?, 997.00, ?)', [lastID, 'PAID']));
}

module.exports = { dbGet, dbAll, dbRun, initSchema, seed };
```

**After** (`src/controllers/checkoutController.js` — the full checkout flow, now linear):
```js
const courseModel = require('../models/courseModel');
const userModel = require('../models/userModel');
const enrollmentModel = require('../models/enrollmentModel');
const paymentModel = require('../models/paymentModel');
const auditLogModel = require('../models/auditLogModel');
const paymentGateway = require('../services/paymentGateway');
const cache = require('../cache');

function parseCheckoutInput(body) {
  return {
    username: body.usr,
    email: body.eml,
    password: body.pwd,
    courseId: body.c_id,
    cardNumber: body.card,
  };
}

function validateCheckoutInput({ username, email, courseId, cardNumber }) {
  if (!username || !email || !courseId || !cardNumber) return 'Bad Request';
  if (!/^\S+@\S+\.\S+$/.test(email)) return 'Bad Request';
  if (!Number.isInteger(Number(courseId))) return 'Bad Request';
  if (!/^\d{13,19}$/.test(String(cardNumber))) return 'Bad Request';
  return null;
}

async function checkout(req, res, next) {
  try {
    const input = parseCheckoutInput(req.body);
    const validationError = validateCheckoutInput(input);
    if (validationError) return res.status(400).send(validationError);

    const course = await courseModel.findActiveById(input.courseId);
    if (!course) return res.status(404).send('Curso não encontrado');

    const existingUser = await userModel.findByEmail(input.email);
    let userId;

    if (!existingUser) {
      if (!input.password) {
        return res.status(400).send('Senha é obrigatória para criar uma conta');
      }
      const hashedPassword = userModel.hashPassword(input.password);
      const { lastID } = await userModel.create({
        name: input.username,
        email: input.email,
        hashedPassword,
      });
      userId = lastID;
    } else {
      userId = existingUser.id;
    }

    const { status } = paymentGateway.charge({ cardNumber: input.cardNumber });
    if (status === 'DENIED') return res.status(400).send('Pagamento recusado');

    const { lastID: enrollmentId } = await enrollmentModel.create({ userId, courseId: input.courseId });
    await paymentModel.create({ enrollmentId, amount: course.price, status });
    await auditLogModel.record(`Checkout curso ${input.courseId} por ${userId}`);

    cache.set(`last_checkout_${userId}`, course.title);

    res.status(200).json({ msg: 'Sucesso', enrollment_id: enrollmentId });
  } catch (err) {
    next(err);
  }
}

module.exports = { checkout, parseCheckoutInput, validateCheckoutInput };
```

Every `await` either resolves with a real value or throws, is caught once by the surrounding `try/catch`, and reaches `errorHandler` via `next(err)` — there is no code path left where a failed query is silently treated as a success, which is exactly the failure mode AP-12 described. The nesting depth is now one `try` block instead of five nested callbacks (AP-09). See PB-10 for the report handler's counter-free rewrite.

---

## PB-10 — Replace N+1 Queries with a Single JOIN-Based Report Query

**Resolves:** AP-13 (N+1 Query Pattern), and — together with PB-09 — AP-10 and AP-12 for the report endpoint specifically.

**Before** (`src/AppManager.js:83-125`): one `SELECT * FROM courses`, then one `SELECT ... FROM enrollments WHERE course_id = ?` per course, then one `SELECT ... FROM users` and one `SELECT ... FROM payments` per enrollment — `1 + C + 2E` queries, coordinated by the `coursesPending`/`enrPending` counters described in AP-10.

**After** (`src/models/reportModel.js`):
```js
const { dbAll } = require('../database');

const REPORT_QUERY = `
  SELECT
    c.id     AS course_id,
    c.title  AS course_title,
    e.id     AS enrollment_id,
    u.name   AS student_name,
    p.amount AS payment_amount,
    p.status AS payment_status
  FROM courses c
  LEFT JOIN enrollments e ON e.course_id = c.id
  LEFT JOIN users u       ON u.id = e.user_id
  LEFT JOIN payments p    ON p.enrollment_id = e.id
  ORDER BY c.id
`;

function groupRowsByCourse(rows) {
  const courseMap = new Map();

  for (const row of rows) {
    if (!courseMap.has(row.course_id)) {
      courseMap.set(row.course_id, { course: row.course_title, revenue: 0, students: [] });
    }
    const courseData = courseMap.get(row.course_id);

    if (row.enrollment_id === null) continue; // course with no enrollments yet

    if (row.payment_status === 'PAID' && row.payment_amount !== null) {
      courseData.revenue += row.payment_amount;
    }

    courseData.students.push({
      student: row.student_name !== null ? row.student_name : 'Unknown',
      paid: row.payment_amount !== null ? row.payment_amount : 0,
    });
  }

  return Array.from(courseMap.values());
}

async function getFinancialReport() {
  const rows = await dbAll(REPORT_QUERY);
  return groupRowsByCourse(rows);
}

module.exports = { getFinancialReport, groupRowsByCourse };
```

One query replaces `1 + C + 2E`. The response shape (`[{ course, revenue, students: [{ student, paid }] }]`) and its field semantics are preserved exactly: `revenue` only sums payments with `status === 'PAID'` (as in the original), `paid` reflects the payment amount whenever a payment row exists regardless of status (as in the original), and a student with no matched user still falls back to `'Unknown'` (as in the original, defensively — in practice every `enrollments.user_id` in this dataset resolves). `groupRowsByCourse` is exported separately from `getFinancialReport` specifically so it can be unit-tested with a hand-built `rows` array, with no database involved — see PB-13.

**After** (`src/controllers/reportController.js`):
```js
const reportModel = require('../models/reportModel');

async function getFinancialReport(req, res, next) {
  try {
    const report = await reportModel.getFinancialReport();
    res.json(report);
  } catch (err) {
    next(err);
  }
}

module.exports = { getFinancialReport };
```

---

## PB-11 — Add Foreign Key Constraints to the Schema

**Resolves:** AP-14 (Missing Referential Integrity)

**Before** (`src/AppManager.js:12-16`):
```js
this.db.run("CREATE TABLE enrollments (id INTEGER PRIMARY KEY, user_id INTEGER, course_id INTEGER)");
this.db.run("CREATE TABLE payments (id INTEGER PRIMARY KEY, enrollment_id INTEGER, amount REAL, status TEXT)");
```

**After** (`src/database.js`'s `initSchema()`, shown in full in PB-09):
```js
db.run(`CREATE TABLE enrollments (
  id INTEGER PRIMARY KEY,
  user_id INTEGER,
  course_id INTEGER,
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (course_id) REFERENCES courses(id)
)`);
db.run(`CREATE TABLE payments (
  id INTEGER PRIMARY KEY,
  enrollment_id INTEGER,
  amount REAL,
  status TEXT,
  FOREIGN KEY (enrollment_id) REFERENCES enrollments(id)
)`);
```

This is an additive, constraint-only schema change (no column removed or renamed), so it does not alter the JSON contract of any endpoint. `sqlite3` does not enforce foreign keys unless `PRAGMA foreign_keys = ON` is issued on the connection — this is why PB-09's `initSchema()` (shown in full above) runs that pragma first, before any `CREATE TABLE`; without it, the constraints below would be documentation only, not an enforced rule. The two `CREATE TABLE` statements shown here are the exact same code already shown in PB-09 — they are not repeated as a second source of truth, only quoted again here so this entry's evidence and fix are readable on their own without cross-referencing PB-09 first.

---

## PB-12 — Strengthen Input Validation in the Checkout Controller

**Resolves:** AP-15 (Minimal Input Validation)

**Before** (`src/AppManager.js:35`):
```js
if (!u || !e || !cid || !cc) return res.status(400).send("Bad Request");
```

**After** (`src/controllers/checkoutController.js`'s `validateCheckoutInput`, shown in full in PB-09):
```js
function validateCheckoutInput({ username, email, courseId, cardNumber }) {
  if (!username || !email || !courseId || !cardNumber) return 'Bad Request';
  if (!/^\S+@\S+\.\S+$/.test(email)) return 'Bad Request';
  if (!Number.isInteger(Number(courseId))) return 'Bad Request';
  if (!/^\d{13,19}$/.test(String(cardNumber))) return 'Bad Request';
  return null;
}
```

Every request that was previously accepted and would have passed the original presence-only check still passes here (the added checks only reject inputs that were already malformed in a way the original code would have mishandled downstream — a non-numeric `c_id` failing the `courses` lookup with a confusing 404, or a non-digit `card` reaching `paymentGateway.charge` and failing `startsWith` in an undefined way). No previously-valid request becomes invalid.

---

## PB-13 — Extract Business Logic into Testable Model/Service Functions

**Resolves:** AP-11 (Business Logic Coupled to the HTTP Layer)

**Before:** every business rule in the original project (course/user lookup, payment approval, enrollment, report aggregation) is anonymous logic inside `app.post/get/delete(...)` closures in `src/AppManager.js:28-137` — none of it can be invoked without a running Express app and a real HTTP request.

**After:** every rule now lives in a plain, exported function that takes explicit arguments and returns a value or a Promise — `paymentGateway.charge({ cardNumber })`, `reportModel.groupRowsByCourse(rows)`, `checkoutController.validateCheckoutInput(input)`, `userModel.hashPassword(password)`/`verifyPassword(password, stored)` are all directly callable and directly assertable with no HTTP layer involved. For example, `groupRowsByCourse` (PB-10) can be unit-tested like this, with no database and no server running:

```js
const { groupRowsByCourse } = require('../src/models/reportModel');

test('does not count a DENIED payment toward revenue', () => {
  const rows = [
    { course_id: 1, course_title: 'Docker', enrollment_id: 10, student_name: 'Ana', payment_amount: 497, payment_status: 'DENIED' },
  ];
  const report = groupRowsByCourse(rows);
  expect(report[0].revenue).toBe(0);
  expect(report[0].students[0].paid).toBe(497);
});
```

No test runner is added to `package.json` as part of this refactoring — introducing one is a project decision beyond what the audit's findings require, and doing so silently would be an unrequested scope change. What this transformation delivers is testability (every rule is now a plain function), not a test suite; the example above illustrates that testability, it is not a file this Skill creates.

---

## PB-14 — Remove Dead Code

**Resolves:** AP-16 (Dead/Unused Code)

**Before** (`src/utils.js:10,25`; `src/AppManager.js:2`):
```js
let totalRevenue = 0;
// ...
module.exports = { config, logAndCache, badCrypto, globalCache, totalRevenue };
// AppManager.js:2 —
const { config, logAndCache, badCrypto, totalRevenue } = require('./utils');
```

**After:** `totalRevenue` does not appear anywhere in the new structure — not declared, not exported, not imported. If real revenue tracking is desired, it is available as a computed value from `reportModel.getFinancialReport()` (summing `revenue` across courses); reintroducing a separate mutable counter for it would recreate AP-06.

---

## PB-15 — Rename Internal Variables for Clarity

**Resolves:** AP-18 (Poor/Abbreviated Variable Naming)

**Before** (`src/AppManager.js:29-33`):
```js
let u = req.body.usr;
let e = req.body.eml;
let p = req.body.pwd;
let cid = req.body.c_id;
let cc = req.body.card;
```

**After** (`src/controllers/checkoutController.js`'s `parseCheckoutInput`, shown in full in PB-09):
```js
function parseCheckoutInput(body) {
  return {
    username: body.usr,
    email: body.eml,
    password: body.pwd,
    courseId: body.c_id,
    cardNumber: body.card,
  };
}
```

The request-body keys (`usr`, `eml`, `pwd`, `c_id`, `card`) are the project's actual wire contract — documented in `api.http` and used by real clients — and are preserved exactly. Only the internal variable names derived from them (`username`, `email`, `password`, `courseId`, `cardNumber`) are renamed; this is a zero-risk change since internal identifiers have no observable effect outside the function.

---

## PB-16 — Eliminate the Need for Manual `this` Juggling

**Resolves:** AP-19 (Inconsistent `this` Binding Strategy)

**Before** (`src/AppManager.js:26,43-64,50,54`):
```js
const self = this;
// ...arrow-function callbacks use `this.db...` directly (lexical `this` from AppManager)...
this.db.run("INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)", [userId, cid], function(err) {
    if (err) return res.status(500).send("Erro Matrícula");
    let enrId = this.lastID; // relies on sqlite3's own `this` binding for this callback
    self.db.run(/* ... */, function(err) { /* uses `self`, not `this`, to reach AppManager again */ });
});
```

**After:** there is no longer a class instance to alias (`self`) or a lexical `this` to close over, because business logic now lives in plain, module-level `async` functions (`checkoutController.checkout`, the model functions in PB-09/PB-10) — none of them are methods on a stateful object, so there is nothing for `this` to ambiguously refer to. The single place that still needs the `sqlite3` driver's own `this.lastID` binding is `database.js`'s `dbRun` (PB-09), which uses one plain `function` expression, documented with a comment explaining exactly why an arrow function would not work there. Every caller of `dbRun` receives `{ lastID, changes }` as an ordinary return value — no caller needs to know that a special `this` binding exists three layers below it.

---

## Supporting model files (complete, referenced by PB-08/PB-09/PB-10 above)

The controllers shown above call several small, single-responsibility model files. They contain no anti-pattern of their own — they are the direct, minimal data-access layer PB-03's split produces — and are included here in full so no file in the target structure is left as an implied-but-unwritten placeholder.

**`src/models/userModel.js`** (combines PB-02's hashing functions with the CRUD used by PB-04/PB-08/PB-09):
```js
const crypto = require('crypto');
const { dbGet, dbRun } = require('../database');

function hashPassword(password) {
  const salt = crypto.randomBytes(16).toString('hex');
  const derivedKey = crypto.scryptSync(password, salt, 64);
  return `${salt}:${derivedKey.toString('hex')}`;
}

function verifyPassword(password, stored) {
  const [salt, storedHex] = stored.split(':');
  const derivedKey = crypto.scryptSync(password, salt, 64);
  const storedBuffer = Buffer.from(storedHex, 'hex');
  return derivedKey.length === storedBuffer.length && crypto.timingSafeEqual(derivedKey, storedBuffer);
}

function findByEmail(email) {
  return dbGet('SELECT * FROM users WHERE email = ?', [email]);
}

function findById(id) {
  return dbGet('SELECT * FROM users WHERE id = ?', [id]);
}

function create({ name, email, hashedPassword }) {
  return dbRun('INSERT INTO users (name, email, pass) VALUES (?, ?, ?)', [name, email, hashedPassword]);
}

function remove(id) {
  return dbRun('DELETE FROM users WHERE id = ?', [id]);
}

module.exports = { hashPassword, verifyPassword, findByEmail, findById, create, remove };
```

**`src/models/courseModel.js`**:
```js
const { dbGet } = require('../database');

function findActiveById(id) {
  return dbGet('SELECT * FROM courses WHERE id = ? AND active = 1', [id]);
}

module.exports = { findActiveById };
```

**`src/models/enrollmentModel.js`**:
```js
const { dbRun } = require('../database');

function create({ userId, courseId }) {
  return dbRun('INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)', [userId, courseId]);
}

module.exports = { create };
```

**`src/models/paymentModel.js`**:
```js
const { dbRun } = require('../database');

function create({ enrollmentId, amount, status }) {
  return dbRun('INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)', [enrollmentId, amount, status]);
}

module.exports = { create };
```

**`src/models/auditLogModel.js`**:
```js
const { dbRun } = require('../database');

function record(action) {
  return dbRun("INSERT INTO audit_logs (action, created_at) VALUES (?, datetime('now'))", [action]);
}

module.exports = { record };
```

**`src/routes/checkoutRoutes.js`** (referenced by PB-03/PB-09, not shown until now):
```js
const express = require('express');
const checkoutController = require('../controllers/checkoutController');

const router = express.Router();

router.post('/', checkoutController.checkout);

module.exports = router;
```

**`src/routes/reportRoutes.js`** (referenced by PB-10, not shown until now):
```js
const express = require('express');
const reportController = require('../controllers/reportController');

const router = express.Router();

router.get('/financial-report', reportController.getFinancialReport);

module.exports = router;
```

**`src/middlewares/errorHandler.js`** (referenced by PB-03/PB-09, not shown until now):
```js
function errorHandler(err, req, res, next) {
  console.error('[ERROR]', err);
  res.status(500).send('Erro interno do servidor');
}

module.exports = errorHandler;
```

With these files, every module named anywhere in this playbook and in `mvc-guidelines.md`'s target tree has a complete, concrete implementation — there is no file left for the executor to improvise from scratch.

---

## Coverage summary

16 entries (PB-01 through PB-16) implement transformations covering all 19 confirmed findings (G-001 through G-019, expressed here as AP-01 through AP-19) plus the general testability improvement AP-11 requires. AP-20 has no playbook entry because it is a verification step (see `anti-pattern-catalog.md`), not a code transformation — at audit time nothing was found to fix.
