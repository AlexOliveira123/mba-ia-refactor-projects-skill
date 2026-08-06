from database import get_db


def reset_all_tables():
    db = get_db()
    cursor = db.cursor()
    for table in ("itens_pedido", "pedidos", "produtos", "usuarios"):
        cursor.execute(f"DELETE FROM {table}")
    db.commit()


def execute_admin_query(sql):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(sql)
    if sql.strip().upper().startswith("SELECT"):
        rows = cursor.fetchall()
        return {"rows": [dict(row) for row in rows]}
    db.commit()
    return {"rows": None}


def get_counts():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM produtos")
    products = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM pedidos")
    orders = cursor.fetchone()[0]
    return {"produtos": products, "usuarios": users, "pedidos": orders}
