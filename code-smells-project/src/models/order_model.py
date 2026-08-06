from database import get_db

DISCOUNT_TIERS = [
    (10000, 0.10),
    (5000, 0.05),
    (1000, 0.02),
]


def _calculate_discount(revenue):
    for threshold, rate in DISCOUNT_TIERS:
        if revenue > threshold:
            return revenue * rate
    return 0


def _validate_and_calculate(cursor, items):
    total = 0
    for item in items:
        cursor.execute("SELECT * FROM produtos WHERE id = ?", (item["produto_id"],))
        product = cursor.fetchone()
        if product is None:
            return None, f"Produto {item['produto_id']} não encontrado"
        if product["estoque"] < item["quantidade"]:
            return None, f"Estoque insuficiente para {product['nome']}"
        total += product["preco"] * item["quantidade"]
    return total, None


def create_order(user_id, items):
    db = get_db()
    cursor = db.cursor()

    total, error = _validate_and_calculate(cursor, items)
    if error:
        return {"erro": error}

    try:
        cursor.execute(
            "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, 'pendente', ?)",
            (user_id, total),
        )
        order_id = cursor.lastrowid

        for item in items:
            cursor.execute("SELECT preco FROM produtos WHERE id = ?", (item["produto_id"],))
            price = cursor.fetchone()["preco"]
            cursor.execute(
                "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
                (order_id, item["produto_id"], item["quantidade"], price),
            )
            cursor.execute(
                "UPDATE produtos SET estoque = estoque - ? WHERE id = ?",
                (item["quantidade"], item["produto_id"]),
            )

        db.commit()
        return {"pedido_id": order_id, "total": total}
    except Exception:
        db.rollback()
        return {"erro": "Falha ao processar pedido, nenhuma alteração foi salva"}


def _fetch_orders(where_clause="", params=()):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        f"""
        SELECT p.id, p.usuario_id, p.status, p.total, p.criado_em,
               i.produto_id, i.quantidade, i.preco_unitario, pr.nome AS produto_nome
        FROM pedidos p
        LEFT JOIN itens_pedido i ON i.pedido_id = p.id
        LEFT JOIN produtos pr ON pr.id = i.produto_id
        {where_clause}
        ORDER BY p.id
        """,
        params,
    )
    orders = {}
    for row in cursor.fetchall():
        oid = row["id"]
        if oid not in orders:
            orders[oid] = {
                "id": oid,
                "usuario_id": row["usuario_id"],
                "status": row["status"],
                "total": row["total"],
                "criado_em": row["criado_em"],
                "itens": [],
            }
        if row["produto_id"] is not None:
            orders[oid]["itens"].append({
                "produto_id": row["produto_id"],
                "produto_nome": row["produto_nome"] or "Desconhecido",
                "quantidade": row["quantidade"],
                "preco_unitario": row["preco_unitario"],
            })
    return list(orders.values())


def get_user_orders(user_id):
    return _fetch_orders("WHERE p.usuario_id = ?", (user_id,))


def list_orders():
    return _fetch_orders()


def update_order_status(order_id, new_status):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE pedidos SET status = ? WHERE id = ?", (new_status, order_id))
    db.commit()
    return True


def sales_report():
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT COUNT(*) FROM pedidos")
    total_orders = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(total) FROM pedidos")
    revenue = cursor.fetchone()[0]
    if revenue is None:
        revenue = 0

    cursor.execute("SELECT COUNT(*) FROM pedidos WHERE status = 'pendente'")
    pending = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM pedidos WHERE status = 'aprovado'")
    approved = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM pedidos WHERE status = 'cancelado'")
    cancelled = cursor.fetchone()[0]

    discount = _calculate_discount(revenue)

    return {
        "total_pedidos": total_orders,
        "faturamento_bruto": round(revenue, 2),
        "desconto_aplicavel": round(discount, 2),
        "faturamento_liquido": round(revenue - discount, 2),
        "pedidos_pendentes": pending,
        "pedidos_aprovados": approved,
        "pedidos_cancelados": cancelled,
        "ticket_medio": round(revenue / total_orders, 2) if total_orders > 0 else 0,
    }
