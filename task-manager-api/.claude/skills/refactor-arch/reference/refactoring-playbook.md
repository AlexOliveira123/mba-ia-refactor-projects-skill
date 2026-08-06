# Refactoring Playbook — `task-manager-api`

Concrete transformations for **Phase 3 (MVC Refactoring)**, mapped to `anti-pattern-catalog.md`. Every "Before" snippet is the real, current content of the project's files at the audit's line numbers. Re-read the current file before applying a transformation — if a prior partial refactor already changed something cited here, adapt to the current state rather than applying this blindly.

---

## PB-01 — Extract Configuration (secrets, debug, host) via `config.py` + `python-dotenv`

**Resolves:** AP-01 (`SECRET_KEY` half), AP-02, AP-12 (`python-dotenv` half)

**Before** (`app.py:9-13,34`):
```python
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'super-secret-key-123'
...
app.run(debug=True, host='0.0.0.0', port=5000)
```

**After** (`config.py`, new file):
```python
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-only-change-me')
SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///tasks.db')
DEBUG = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
HOST = os.environ.get('FLASK_HOST', '0.0.0.0')
PORT = int(os.environ.get('FLASK_PORT', '5000'))
CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000').split(',')
```

**After** (`app.py`, usage):
```python
import config

app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = config.SECRET_KEY
...
app.run(debug=config.DEBUG, host=config.HOST, port=config.PORT)
```

`DEBUG` now defaults to `False` (resolves AP-02); `python-dotenv`, already installed and previously unused (AP-12), is now the actual source of these values when a `.env` file is present. The fallback literals only allow an unconfigured local boot to keep working unchanged. This `app.run(...)` line also moves inside `create_tables()`'s `if __name__` guard in PB-13 below — the two entries touch the same few lines of `app.py` from different angles (configuration values here, initialization side effect there); apply both, the final file reflects both changes together.

---

## PB-02 — Restrict CORS to an Explicit Origin List

**Resolves:** AP-17

**Before** (`app.py:15`):
```python
CORS(app)
```

**After:**
```python
CORS(app, origins=config.CORS_ORIGINS)
```

No origin is documented anywhere in this project at audit time; `CORS_ORIGINS` defaults to `http://localhost:3000` in `config.py` (PB-01) as the most defensible local-development default. Document this default explicitly in the Phase 3 summary as a decision the project owner should confirm or adjust for their real client origin.

---

## PB-03 — Real Signed Login Token + Auth Guard on Destructive/Privilege-Altering Routes

**Resolves:** AP-03

**Before** (`routes/user_routes.py:185-211`, `/login`, no verification anywhere in the project; `routes/user_routes.py:134-151`, `DELETE /users/<id>`, no check; `:119-122`, `role` accepted with no check):
```python
return jsonify({
    'message': 'Login realizado com sucesso',
    'user': user.to_dict(),
    'token': 'fake-jwt-token-' + str(user.id)
}), 200
```

**After** (`middlewares/auth.py`, new file — `itsdangerous` is already an installed transitive dependency of Flask, no new library is added):
```python
from functools import wraps
from flask import request, jsonify, current_app
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

def generate_token(user_id):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps({'user_id': user_id})

def verify_token(token):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        data = serializer.loads(token, max_age=86400)
        return data.get('user_id')
    except (BadSignature, SignatureExpired):
        return None

def _extract_bearer_token():
    auth_header = request.headers.get('Authorization', '')
    return auth_header[len('Bearer '):] if auth_header.startswith('Bearer ') else ''

def get_authenticated_user_id():
    """Single place that turns the current request's Authorization header into a
    verified user_id (or None). Used by both require_auth and any controller that
    needs to inspect *who* is calling, not just *whether* they are authenticated —
    reusing this instead of re-parsing the header inline avoids duplicating the
    exact kind of logic this Skill's own catalog (AP-08) flags when duplicated."""
    return verify_token(_extract_bearer_token())

def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user_id = get_authenticated_user_id()
        if not user_id:
            return jsonify({'error': 'Autenticação necessária'}), 401
        request.user_id = user_id
        return f(*args, **kwargs)
    return wrapper
```

**After** (`controllers/user_controller.py`, login):
```python
from middlewares.auth import generate_token

def login():
    ...
    return jsonify({
        'message': 'Login realizado com sucesso',
        'user': user.to_dict(),
        'token': generate_token(user.id)
    }), 200
```

**After** (`routes/task_routes.py`, `routes/user_routes.py` — apply `require_auth` only to destructive routes):
```python
from middlewares.auth import require_auth

@task_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@require_auth
def delete_task_route(task_id):
    return task_controller.delete_task(task_id)
```
The same decorator is applied to `DELETE /users/<id>` and `DELETE /categories/<id>`.

**After** (`controllers/user_controller.py`, `update_user` — guard only the `role`-changing branch, not the whole route):
```python
from middlewares.auth import get_authenticated_user_id
from models.user import User

def update_user(user_id):
    ...
    if 'role' in data:
        requester_id = get_authenticated_user_id()
        requester = User.query.get(requester_id) if requester_id else None
        if not requester or not requester.is_admin():
            return jsonify({'error': 'Apenas administradores podem alterar role'}), 403
        if data['role'] not in VALID_ROLES:
            return jsonify({'error': 'Role inválido'}), 400
        user.role = data['role']
    ...
```

**Why this checks `is_admin()`, not just "is authenticated":** a check that only required *some* valid token (as an earlier draft of this entry did) would not actually close H-003's most severe named consequence — any logged-in user, not just an admin, could still call `PUT /users/<id>` with `{"role": "admin"}` and it would pass a "some valid token exists" check. The fix must specifically require the **caller** to already hold the `admin` role, which is exactly what `User.is_admin()` (`models/user.py:34-38`, simplified by PB-14) is for — this is also the first real call site that method gets in this refactoring; it had none before.

**Documented contract changes:** `POST /login` now returns a real signed token instead of a predictable string. `DELETE /tasks/<id>`, `DELETE /users/<id>`, and `DELETE /categories/<id>` now require `Authorization: Bearer <token>` from any authenticated user, returning `401` without one. `PUT /users/<id>` when changing `role` now additionally requires the authenticated caller to already be an admin, returning `403` if authenticated-but-not-admin (`401` if not authenticated at all). Every other route (all reads, task/category create/update, ordinary user profile fields) is unchanged — see `mvc-guidelines.md` for why comprehensive authentication on every route is deliberately out of scope.

---

## PB-04 — Proper Password Hashing

**Resolves:** AP-04

**Before** (`models/user.py:27-32`):
```python
def set_password(self, pwd):
    self.password = hashlib.md5(pwd.encode()).hexdigest()

def check_password(self, pwd):
    return self.password == hashlib.md5(pwd.encode()).hexdigest()
```

**After** (`werkzeug.security` is already a Flask dependency, no new library added):
```python
from werkzeug.security import generate_password_hash, check_password_hash

def set_password(self, pwd):
    self.password = generate_password_hash(pwd)

def check_password(self, pwd):
    return check_password_hash(self.password, pwd)
```

`password = db.Column(db.String(255), ...)` (`models/user.py:11`) is already wide enough for the resulting hash format — no schema/migration change needed. Existing seed calls (`seed.py:19,26,33`, `u.set_password('1234')`, etc.) automatically use the new algorithm with no change to `seed.py` required for this specific fix.

---

## PB-05 — Remove Password from Serialization

**Resolves:** AP-05

**Before** (`models/user.py:16-25`):
```python
def to_dict(self):
    return {
        'id': self.id, 'name': self.name, 'email': self.email,
        'password': self.password, 'role': self.role,
        'active': self.active, 'created_at': str(self.created_at)
    }
```

**After:**
```python
def to_dict(self):
    return {
        'id': self.id, 'name': self.name, 'email': self.email,
        'role': self.role, 'active': self.active,
        'created_at': str(self.created_at)
    }
```

Both call sites that previously leaked the hash (`GET /users/<id>`, `POST /login`) now go through this same method — no separate fix needed at either call site.

---

## PB-06 — Remove Dead Service Layer

**Resolves:** AP-06, AP-01 (SMTP-credential half)

**Before:** `services/notification_service.py` (49 lines, `NotificationService`, including the hardcoded SMTP credential at lines 9-10) and the `services/` package.

**After:** the file and the package are deleted. No route, model, or controller referenced it (confirmed by the same reachability search behind AP-06), so nothing else changes. Do not reintroduce email sending as part of this refactoring — that would be new observable behavior, out of scope for a change that must preserve behavior.

---

## PB-07 — Trim and Wire Up `utils/helpers.py`

**Resolves:** AP-07, AP-08, AP-09

**Before** (`utils/helpers.py`, 9 functions + 7 constants, only 2 functions ever imported and neither ever called) and duplicated inline logic at `routes/user_routes.py:61,106` (email regex) and `:64,115` (password length):
```python
if not re.match(r'^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$', email):
    return jsonify({'error': 'Email inválido'}), 400
if len(password) < 4:
    return jsonify({'error': 'Senha deve ter no mínimo 4 caracteres'}), 400
```

**After** (`utils/helpers.py` trimmed to the 4 functions and 7 constants with a confirmed real caller; `sanitize_string`, `generate_id`, `log_action`, `is_valid_color`, `process_task_data` are removed — see `mvc-guidelines.md` for why):
```python
def format_date(date_obj):
    return str(date_obj) if date_obj else None

def calculate_percentage(part, total):
    return round((part / total) * 100, 2) if total else 0

def validate_email(email):
    return bool(re.match(r'^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$', email))

def parse_date(date_string):
    try:
        return datetime.strptime(date_string, '%Y-%m-%d')
    except ValueError:
        try:
            return datetime.strptime(date_string, '%d/%m/%Y')
        except ValueError:
            return None

VALID_STATUSES = ['pending', 'in_progress', 'done', 'cancelled']
VALID_ROLES = ['user', 'admin', 'manager']
MAX_TITLE_LENGTH = 200
MIN_TITLE_LENGTH = 3
MIN_PASSWORD_LENGTH = 4
DEFAULT_PRIORITY = 3
DEFAULT_COLOR = '#000000'
```

**After** (`controllers/user_controller.py`, actually calling the helper instead of duplicating it):
```python
from utils.helpers import validate_email, MIN_PASSWORD_LENGTH, VALID_ROLES

if not validate_email(email):
    return jsonify({'error': 'Email inválido'}), 400
if len(password) < MIN_PASSWORD_LENGTH:
    return jsonify({'error': f'Senha deve ter no mínimo {MIN_PASSWORD_LENGTH} caracteres'}), 400
if role not in VALID_ROLES:
    return jsonify({'error': 'Role inválido'}), 400
```

**After** (`controllers/task_controller.py`, same pattern for status/title/priority):
```python
from utils.helpers import VALID_STATUSES, MIN_TITLE_LENGTH, MAX_TITLE_LENGTH, DEFAULT_PRIORITY

title = (data.get('title') or '').strip()
if len(title) < MIN_TITLE_LENGTH or len(title) > MAX_TITLE_LENGTH:
    return None, f'Título deve ter entre {MIN_TITLE_LENGTH} e {MAX_TITLE_LENGTH} caracteres'

status = data.get('status', 'pending')
if status not in VALID_STATUSES:
    return None, 'Status inválido'
```

**After** (`controllers/report_controller.py`, `format_date`/`calculate_percentage` actually called, not just imported):
```python
from utils.helpers import calculate_percentage, format_date

completion_rate = calculate_percentage(done, total)
task_data['due_date'] = format_date(t.due_date)
```

`parse_date`'s dual-format support (`%Y-%m-%d` and `%d/%m/%Y`) is strictly more permissive than the single-format `strptime` calls it replaces in `task_routes.py:136,203` — this is a safe, non-breaking widening (accepts every input the original accepted, plus one more format), not a contract change requiring separate documentation.

---

## PB-08 — Reuse `Task.is_overdue()` Instead of Reimplementing It

**Resolves:** AP-10

**Before** (repeated at `routes/task_routes.py:30-39,71-80`, `routes/user_routes.py:171-180`, `routes/report_routes.py:34-37,132-135`):
```python
if t.due_date:
    if t.due_date < datetime.utcnow():
        if t.status != 'done' and t.status != 'cancelled':
            task_data['overdue'] = True
        else:
            task_data['overdue'] = False
    else:
        task_data['overdue'] = False
else:
    task_data['overdue'] = False
```

**After** (every one of the 5 sites):
```python
task_data['overdue'] = t.is_overdue()
```

`models/task.py:50-60` is unchanged — this transformation only changes call sites to use the method that already existed and was already correct.

---

## PB-09 — Fix N+1 Queries with Eager Loading

**Resolves:** AP-11

**Before** (`routes/task_routes.py:11-63`, `get_tasks`):
```python
tasks = Task.query.all()
for t in tasks:
    ...
    if t.user_id:
        user = User.query.get(t.user_id)
        ...
    if t.category_id:
        cat = Category.query.get(t.category_id)
        ...
```

**After** (`controllers/task_controller.py`, using the `user`/`category` relationships `models/task.py:20-21` already declares — no schema change, no new dependency, `joinedload` ships with SQLAlchemy):
```python
from sqlalchemy.orm import joinedload

def list_tasks():
    tasks = Task.query.options(joinedload(Task.user), joinedload(Task.category)).all()
    result = []
    for t in tasks:
        task_data = t.to_dict()
        task_data['overdue'] = t.is_overdue()
        task_data['user_name'] = t.user.name if t.user else None
        task_data['category_name'] = t.category.name if t.category else None
        result.append(task_data)
    return result
```

**Before** (`routes/report_routes.py:53-68`, `summary_report`):
```python
users = User.query.all()
for u in users:
    user_tasks = Task.query.filter_by(user_id=u.id).all()
    ...
```

**After** (`controllers/report_controller.py`, using the existing `backref='tasks'` from `models/task.py:20`):
```python
users = User.query.options(joinedload(User.tasks)).all()
for u in users:
    user_tasks = u.tasks  # already loaded by the eager query above, no additional query per user
    ...
```

---

## PB-10 — Remove Unused `marshmallow` Dependency

**Resolves:** AP-12 (`marshmallow` half)

**Before** (`requirements.txt`):
```
flask==3.0.0
flask-sqlalchemy==3.1.1
flask-cors==4.0.0
marshmallow==3.20.1
requests==2.31.0
python-dotenv==1.0.0
```

**After:**
```
flask==3.0.0
flask-sqlalchemy==3.1.1
flask-cors==4.0.0
requests==2.31.0
python-dotenv==1.0.0
```

Adopting `marshmallow` for real would mean designing new `Schema` classes — new validation infrastructure, not a reorganization of logic that already exists — which is out of scope for this refactoring (see PB-01/PB-07 for the `python-dotenv` case, which was wired in for real instead, because doing so required no new design, only using the tool for the purpose its presence already implied).

---

## PB-11 — Centralize Error Handling

**Resolves:** AP-13

**Before:** bare `except:` at `routes/task_routes.py:62-63`, `routes/report_routes.py:186-188,207-209,221-223`; inconsistent `except Exception as e:` with `print(...)` elsewhere (e.g., `routes/user_routes.py:87-89`).

**After** (`middlewares/error_handler.py`, new file):
```python
import logging
from flask import jsonify

logger = logging.getLogger('task_manager_api')

def register_error_handlers(app):
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        logger.exception('Unhandled error: %s', error)
        return jsonify({'error': 'Erro interno'}), 500
```

**After** (`app.py`):
```python
from middlewares.error_handler import register_error_handlers
register_error_handlers(app)
```

**After** (controllers, replacing every bare `except:`/`except Exception as e:` around a database write with a narrow, typed catch that still rolls back, then lets the real error propagate to the handler above):
```python
from sqlalchemy.exc import SQLAlchemyError

try:
    db.session.add(task)
    db.session.commit()
except SQLAlchemyError:
    db.session.rollback()
    raise
```

Business-rule outcomes that already have a defined status in the original contract (not found → 404, invalid input → 400) remain explicit `if`/`return` statements in the controller — that is not the same thing as catching a generic exception, and is preserved exactly as today.

---

## PB-12 — Consistent Validation on Sibling Routes

**Resolves:** AP-14

**Before** (`routes/report_routes.py:190-202`, `update_category`, missing the guard `create_category` has):
```python
def update_category(cat_id):
    cat = Category.query.get(cat_id)
    if not cat:
        return jsonify({'error': 'Categoria não encontrada'}), 404

    data = request.get_json()
    if 'name' in data:
        ...
```

**After:**
```python
def update_category(cat_id):
    cat = Category.query.get(cat_id)
    if not cat:
        return jsonify({'error': 'Categoria não encontrada'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Dados inválidos'}), 400

    if 'name' in data:
        ...
```

---

## PB-13 — Fix the Module-Level `db.create_all()` Side Effect (and Keep `seed.py` Working)

**Resolves:** AP-15

**Before** (`app.py:30-34`):
```python
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

**After** (`app.py`):
```python
def create_tables():
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    create_tables()
    app.run(debug=config.DEBUG, host=config.HOST, port=config.PORT)
```

**Required coupled change** (`seed.py:1-9`, otherwise `python seed.py` on a fresh database would break — this is not optional):
```python
# Before
from app import app, db
from models.task import Task
...
def seed_data():
    with app.app_context():
        Task.query.delete()
        ...

# After
from app import app, db, create_tables
from models.task import Task
...
def seed_data():
    create_tables()
    with app.app_context():
        Task.query.delete()
        ...
```

---

## PB-14 — Simplify Redundant Conditional

**Resolves:** AP-16

**Before** (`models/user.py:34-38`):
```python
def is_admin(self):
    if self.role == 'admin':
        return True
    else:
        return False
```

**After:**
```python
def is_admin(self):
    return self.role == 'admin'
```

---

## Coverage

14 entries (PB-01 through PB-14) implement all 17 evidence-backed catalog entries with a required transformation (AP-01 through AP-17). AP-18, AP-19, and AP-20 have no playbook entry because they are verification steps (see `anti-pattern-catalog.md`) — at audit time, none of them found a defect to fix.
