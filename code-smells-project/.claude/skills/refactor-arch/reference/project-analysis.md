# Analysis Heuristics — `code-smells-project` (Phase 1)

Guide for **Phase 1 (Project Analysis)**. Every heuristic below is specific to what this project actually contains — these are not generic rules for an arbitrary stack.

## Language
**Signal:** presence of `.py` files at the project root and a `requirements.txt`.
**Expected result:** `Python`.

## Framework
**Signal:** `requirements.txt` contains a `flask==<version>` line; `app.py` contains `from flask import Flask`.
**Expected result:** `Flask <exact version read from requirements.txt>` (at audit time: Flask 3.1.1).

## Relevant dependencies
**Signal:** read every line of `requirements.txt` (except `flask` itself).
**Expected result at audit time:** `flask-cors==5.0.1` (enables unrestricted CORS — relevant to the audit, see AP-18 and the catalog's security notes).

## Application domain
**Signal:** table names created in `database.py` (`CREATE TABLE`) and the welcome text returned by the root route (`app.py`, `index` function).
**Expected result:** `E-commerce API (products, orders, users)` — evidenced by `database.py:15-53` (tables `produtos`, `usuarios`, `pedidos`, `itens_pedido`) and `app.py:34-45` ("Bem-vindo à API da Loja").

## Project structure
**Signal:** list `.py` files at the project root (ignoring any `.claude/`, `venv/`, `__pycache__/` directory).
**Expected result at audit time:** 4 source files — `app.py`, `controllers.py`, `models.py`, `database.py` — all at the same level, with no source subfolders. Report the exact count observed at execution time (do not assume it will always be 4, in case the project has already been partially modified).

## Current architecture
**Signal:** absence of source subfolders (`models/`, `routes/`, `controllers/`) combined with the responsibility distribution observed in each of the 4 files.
**Expected result:** `Monolithic — everything in 4 files, no layer separation`. Briefly describe the observed role of each file (e.g., "`app.py`: bootstrap + 4 routes of its own; `controllers.py`: 19 route functions for 5 domains; `models.py`: 16 data-access functions for 4 domains; `database.py`: connection + schema + seed").

## Database
**Signal:** `import sqlite3` in `database.py`; the file name in `db_path`; `CREATE TABLE IF NOT EXISTS` statements inside `get_db()`.
**Expected result:** `SQLite (file loja.db)`, with the table list extracted directly from the `CREATE TABLE` statements found (do not copy the list from this document without confirming against the file — the schema may already have been changed by a previous Phase 3 run).

## Phase 1 summary — output format
Use the format defined in `report-template.md`, "Phase 1" section. Every value above must be extracted from the code at execution time, never copied from this document as if it were the result — this file describes **where to look and what to expect to find**, it does not replace actually reading the code on every run.
