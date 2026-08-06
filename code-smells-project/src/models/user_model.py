from werkzeug.security import check_password_hash, generate_password_hash

from database import get_db


def _serialize_user(row):
    return {
        "id": row["id"],
        "nome": row["nome"],
        "email": row["email"],
        "tipo": row["tipo"],
        "criado_em": row["criado_em"],
    }
    # the "senha" field is never included in a serialization meant for an HTTP response


def list_users():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM usuarios")
    return [_serialize_user(row) for row in cursor.fetchall()]


def get_user_by_id(user_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    return _serialize_user(row) if row else None


def email_already_registered(email):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT 1 FROM usuarios WHERE email = ?", (email,))
    return cursor.fetchone() is not None


def create_user(name, email, password, role="cliente"):
    db = get_db()
    cursor = db.cursor()
    password_hash = generate_password_hash(password)
    cursor.execute(
        "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
        (name, email, password_hash, role),
    )
    db.commit()
    return cursor.lastrowid


def login_user(email, password):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,))
    row = cursor.fetchone()
    if row and check_password_hash(row["senha"], password):
        return {"id": row["id"], "nome": row["nome"], "email": row["email"], "tipo": row["tipo"]}
    return None
