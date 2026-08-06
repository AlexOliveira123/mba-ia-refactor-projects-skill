from database import get_db


def _serialize_product(row):
    return {
        "id": row["id"],
        "nome": row["nome"],
        "descricao": row["descricao"],
        "preco": row["preco"],
        "estoque": row["estoque"],
        "categoria": row["categoria"],
        "ativo": row["ativo"],
        "criado_em": row["criado_em"],
    }


def list_products():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM produtos")
    return [_serialize_product(row) for row in cursor.fetchall()]


def get_product_by_id(product_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM produtos WHERE id = ?", (product_id,))
    row = cursor.fetchone()
    return _serialize_product(row) if row else None


def search_products(term, category=None, min_price=None, max_price=None):
    db = get_db()
    cursor = db.cursor()
    query = "SELECT * FROM produtos WHERE 1=1"
    params = []
    if term:
        query += " AND (nome LIKE ? OR descricao LIKE ?)"
        params.extend([f"%{term}%", f"%{term}%"])
    if category:
        query += " AND categoria = ?"
        params.append(category)
    if min_price:
        query += " AND preco >= ?"
        params.append(min_price)
    if max_price:
        query += " AND preco <= ?"
        params.append(max_price)
    cursor.execute(query, params)
    return [_serialize_product(row) for row in cursor.fetchall()]


def create_product(name, description, price, stock, category):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
        (name, description, price, stock, category),
    )
    db.commit()
    return cursor.lastrowid


def update_product(product_id, name, description, price, stock, category):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, categoria = ? WHERE id = ?",
        (name, description, price, stock, category, product_id),
    )
    db.commit()
    return True


def delete_product(product_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM produtos WHERE id = ?", (product_id,))
    db.commit()
    return True
