# Analysis Heuristics — `ecommerce-api-legacy` (Phase 1)

Guide for **Phase 1 (Project Analysis)**. Every heuristic below is specific to what this project actually contains — these are not generic rules for an arbitrary stack. This file is independent from any equivalent file used for another project; do not import or reference another project's Skill.

## Language

**Signal:** presence of `.js` files under `src/`, a `package.json` at the project root, and `require(...)`/`module.exports` (CommonJS) syntax in every source file.
**Expected result:** `JavaScript (Node.js, CommonJS modules)`.

## Framework

**Signal:** `package.json` → `dependencies.express`; `src/app.js` contains `require('express')` and `express()`.
**Expected result:** `Express <exact version read from package.json>` (at audit time: Express `^4.18.2`).

## Relevant dependencies

**Signal:** read every key under `package.json` → `dependencies` (except `express` itself).
**Expected result at audit time:** `sqlite3 ^5.1.6` — a callback-based SQLite driver (not promise-based, no ORM). Also check `devDependencies` and `scripts` for a test runner (e.g., `jest`, `mocha`, `ava`); at audit time none is present — only a `start` script exists, confirming there is no automated test suite (relevant to AP-11).

## Application domain

**Signal:** table names created in `AppManager.js` → `initDb()` (`CREATE TABLE`), the route paths registered in `setupRoutes(app)`, and the boot log message in `app.js`.
**Expected result:** `LMS (course platform) with a checkout/payment flow` — evidenced by `src/AppManager.js:12-16` (tables `users`, `courses`, `enrollments`, `payments`, `audit_logs`) and the routes `/api/checkout`, `/api/admin/financial-report`, `/api/users/:id`.

## Project structure

**Signal:** list `.js` files under `src/` (ignoring `node_modules/`, `.claude/`).
**Expected result at audit time:** 3 source files — `src/app.js`, `src/AppManager.js`, `src/utils.js` — all at the same level, with no subfolders. Report the exact count observed at execution time (do not assume it will always be 3, in case the project has already been partially refactored by a previous Phase 3 run).

## Current architecture

**Signal:** absence of source subfolders (`models/`, `routes/`, `controllers/`) combined with the responsibility distribution observed in the 3 files.
**Expected result:** `Monolithic — a single God Class owns everything, no layer separation`. Briefly describe the observed role of each file (e.g., "`app.js`: bootstrap, creates the Express app and the `AppManager` instance; `AppManager.js`: a single class that owns the DB connection, schema definition, seed data, all 3 routes, checkout business logic, payment decision, and report aggregation; `utils.js`: hardcoded configuration, a module-level mutable cache, and a fake hashing function").

## Database

**Signal:** `require('sqlite3')` in `AppManager.js`; the connection string passed to `new sqlite3.Database(...)`; `CREATE TABLE` statements inside `initDb()`.
**Expected result:** `SQLite, in-memory (":memory:")` — data does not persist across restarts and is reseeded on every boot. Extract the table list directly from the `CREATE TABLE` statements found at execution time (do not copy the list from this document without confirming against the file — the schema may already have been changed by a previous Phase 3 run).

## Phase 1 summary — output format

Use the format defined in `report-template.md`, "Phase 1" section. Every value above must be extracted from the code at execution time, never copied from this document as if it were the result — this file describes **where to look and what to expect to find**, it does not replace actually reading the code on every run.
