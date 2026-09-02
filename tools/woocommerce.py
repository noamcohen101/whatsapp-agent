"""WooCommerce tool for Israstore: orders, products, stock, sales, customers, coupons."""
import httpx

from config import WOO_KEY, WOO_SECRET, WOO_URL

_TIMEOUT = 25
# israstore.shop's nginx WAF blocks the Basic-Auth header from non-browser clients,
# so authenticate via query params (fine over HTTPS) and send browser-ish headers.
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}
_AUTH = {"consumer_key": WOO_KEY, "consumer_secret": WOO_SECRET}


def _get(path: str, params: dict | None = None):
    r = httpx.get(
        f"{WOO_URL}/wp-json/wc/v3/{path}",
        params={**(params or {}), **_AUTH},
        headers=_HEADERS,
        timeout=_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def _get_with_headers(path: str, params: dict | None = None):
    r = httpx.get(
        f"{WOO_URL}/wp-json/wc/v3/{path}",
        params={**(params or {}), **_AUTH},
        headers=_HEADERS,
        timeout=_TIMEOUT,
    )
    r.raise_for_status()
    return r.json(), r.headers


def _put(path: str, body: dict):
    r = httpx.put(
        f"{WOO_URL}/wp-json/wc/v3/{path}",
        params=_AUTH,
        json=body,
        headers=_HEADERS,
        timeout=_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def _post(path: str, body: dict):
    r = httpx.post(
        f"{WOO_URL}/wp-json/wc/v3/{path}",
        params=_AUTH,
        json=body,
        headers=_HEADERS,
        timeout=_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def orders_overview() -> str:
    """Exact counts per order status + exact total order count. Real data, no estimation."""
    totals = _get("reports/orders/totals")
    lines = ["מספרי הזמנות מדויקים לפי סטטוס:"]
    grand = 0
    for t in totals:
        grand += t.get("total", 0)
        lines.append(f"  {t.get('name')} ({t.get('slug')}): {t.get('total')}")
    lines.append(f"סה\"כ הזמנות בכל הזמנים: {grand}")
    return "\n".join(lines)


def list_orders(status: str = "", search: str = "", limit: int = 10) -> str:
    params = {"per_page": min(limit, 25), "orderby": "date", "order": "desc"}
    if status:
        params["status"] = status
    if search:
        params["search"] = search
    orders, headers = _get_with_headers("orders", params)
    total = headers.get("X-WP-Total", "?")
    if not orders:
        return f"אין הזמנות שתואמות (סה\"כ תואמות: {total})."
    lines = [
        f"סה\"כ הזמנות שתואמות לחיפוש: {total}. מוצגות {len(orders)} האחרונות:"
    ]
    for o in orders:
        b = o.get("billing", {})
        name = f"{b.get('first_name','')} {b.get('last_name','')}".strip()
        items = ", ".join(f"{li['quantity']}x {li['name']}" for li in o.get("line_items", []))
        lines.append(
            f"#{o['id']} · {o['status']} · {o['total']} {o['currency']} · {name}\n"
            f"  {o['date_created'][:10]} · {items}"
        )
    if str(total).isdigit() and int(total) > len(orders):
        lines.append(
            f"(יש עוד {int(total) - len(orders)} הזמנות תואמות שלא מוצגות — "
            f"אל תשער מה יש בהן, בקש עוד או השתמש ב-woo_orders_overview / woo_sales_summary)"
        )
    return "\n\n".join(lines)


def get_order(order_id: str) -> str:
    o = _get(f"orders/{order_id}")
    b = o.get("billing", {})
    s = o.get("shipping", {})
    items = "\n".join(
        f"  - {li['quantity']}x {li['name']} = {li['total']}" for li in o.get("line_items", [])
    )
    return (
        f"הזמנה #{o['id']} · {o['status']}\n"
        f"לקוח: {b.get('first_name','')} {b.get('last_name','')} · {b.get('phone','')} · {b.get('email','')}\n"
        f"משלוח: {s.get('address_1','')} {s.get('city','')}\n"
        f"תאריך: {o['date_created'][:16]}\n"
        f"פריטים:\n{items}\n"
        f"סה\"כ: {o['total']} {o['currency']} (משלוח {o.get('shipping_total','0')})\n"
        f"הערת לקוח: {o.get('customer_note','') or '-'}"
    )


def list_products(search: str = "", low_stock_only: bool = False, limit: int = 15) -> str:
    params = {"per_page": min(limit, 30), "orderby": "title", "order": "asc"}
    if search:
        params["search"] = search
    prods = _get("products", params)
    rows = []
    for p in prods:
        stock = p.get("stock_quantity")
        managed = p.get("manage_stock")
        stock_txt = (
            f"{stock} במלאי" if managed and stock is not None
            else p.get("stock_status", "")
        )
        low = managed and stock is not None and stock <= 3
        if low_stock_only and not low:
            continue
        flag = "⚠️ " if low else ""
        rows.append(f"{flag}[{p['id']}] {p['name']} · {p.get('price','')}₪ · {stock_txt}")
    if not rows:
        return "אין מוצרים שתואמים." if not low_stock_only else "אין מוצרים במלאי נמוך. 👍"
    return "\n".join(rows)


def get_product(product_id: str) -> str:
    p = _get(f"products/{product_id}")
    return (
        f"[{p['id']}] {p['name']}\n"
        f"מחיר: {p.get('price','')}₪ (רגיל {p.get('regular_price','')}, מבצע {p.get('sale_price','') or '-'})\n"
        f"מלאי: {p.get('stock_quantity') if p.get('manage_stock') else p.get('stock_status')}\n"
        f"SKU: {p.get('sku','') or '-'} · קטגוריות: {', '.join(c['name'] for c in p.get('categories', []))}\n"
        f"קישור: {p.get('permalink','')}"
    )


def update_product(
    product_id: str, price: str = "", stock_quantity: str = "", sale_price: str = ""
) -> str:
    body: dict = {}
    if price:
        body["regular_price"] = str(price)
    if sale_price:
        body["sale_price"] = str(sale_price)
    if stock_quantity != "":
        body["stock_quantity"] = int(stock_quantity)
        body["manage_stock"] = True
    if not body:
        return "לא צוין מה לעדכן."
    p = _put(f"products/{product_id}", body)
    return f"עודכן [{p['id']}] {p['name']}: מחיר {p.get('price')}₪, מלאי {p.get('stock_quantity')}"


def sales_summary(period: str = "week") -> str:
    data = _get("reports/sales", {"period": period})
    if not data:
        return "אין נתונים."
    d = data[0]
    return (
        f"מכירות ({period}):\n"
        f"סה\"כ מכירות: {d.get('total_sales')}₪\n"
        f"מכירות נטו: {d.get('net_sales')}₪\n"
        f"הזמנות: {d.get('total_orders')} · פריטים: {d.get('total_items')}\n"
        f"משלוחים: {d.get('total_shipping')}₪ · הנחות: {d.get('total_discount')}₪"
    )


def list_customers(search: str = "", limit: int = 10) -> str:
    params = {"per_page": min(limit, 20), "orderby": "registered_date", "order": "desc"}
    if search:
        params["search"] = search
    cs = _get("customers", params)
    if not cs:
        return "אין לקוחות תואמים."
    return "\n".join(
        f"[{c['id']}] {c.get('first_name','')} {c.get('last_name','')} · {c.get('email','')} · "
        f"הזמנות: {c.get('orders_count','?')} · הוציא: {c.get('total_spent','?')}₪"
        for c in cs
    )


def create_coupon(code: str, amount: str, discount_type: str = "percent") -> str:
    body = {"code": code, "amount": str(amount), "discount_type": discount_type}
    c = _post("coupons", body)
    return f"נוצר קופון '{c['code']}' — {c['amount']} ({c['discount_type']})"


def _sch(name, desc, props, required):
    return {"schema": {"name": name, "description": desc,
            "input_schema": {"type": "object", "properties": props, "required": required}}}


TOOLS = {
    "woo_orders_overview": {**_sch(
        "woo_orders_overview",
        "מספרי הזמנות מדויקים לפי סטטוס (completed/processing/pending/cancelled/refunded) + סה\"כ. השתמש בזה לכל שאלה על 'כמה הזמנות'.",
        {}, []), "fn": orders_overview},
    "woo_list_orders": {**_sch(
        "woo_list_orders",
        "מציג הזמנות מ-Israstore. status: pending/processing/on-hold/completed/cancelled/refunded. השאר ריק לכל ההזמנות האחרונות.",
        {"status": {"type": "string"}, "search": {"type": "string", "description": "שם/מייל/טלפון לקוח"},
         "limit": {"type": "integer"}}, []), "fn": list_orders},
    "woo_get_order": {**_sch("woo_get_order", "פרטים מלאים של הזמנה לפי מספר.",
        {"order_id": {"type": "string"}}, ["order_id"]), "fn": get_order},
    "woo_list_products": {**_sch(
        "woo_list_products",
        "מציג מוצרים ומלאי. low_stock_only=true מציג רק מוצרים שעומדים להיגמר (<=3).",
        {"search": {"type": "string"}, "low_stock_only": {"type": "boolean"}, "limit": {"type": "integer"}},
        []), "fn": list_products},
    "woo_get_product": {**_sch("woo_get_product", "פרטי מוצר בודד לפי id.",
        {"product_id": {"type": "string"}}, ["product_id"]), "fn": get_product},
    "woo_update_product": {**_sch(
        "woo_update_product",
        "מעדכן מחיר/מלאי/מחיר מבצע של מוצר. דורש אישור מפורש מנועם לפני קריאה.",
        {"product_id": {"type": "string"}, "price": {"type": "string"},
         "stock_quantity": {"type": "string"}, "sale_price": {"type": "string"}},
        ["product_id"]), "fn": update_product},
    "woo_sales_summary": {**_sch("woo_sales_summary", "סיכום מכירות. period: week/month/last_month/year.",
        {"period": {"type": "string"}}, []), "fn": sales_summary},
    "woo_list_customers": {**_sch("woo_list_customers", "רשימת לקוחות עם מספר הזמנות וסכום שהוציאו.",
        {"search": {"type": "string"}, "limit": {"type": "integer"}}, []), "fn": list_customers},
    "woo_create_coupon": {**_sch(
        "woo_create_coupon",
        "יוצר קופון הנחה. discount_type: percent/fixed_cart/fixed_product. דורש אישור מפורש מנועם.",
        {"code": {"type": "string"}, "amount": {"type": "string"}, "discount_type": {"type": "string"}},
        ["code", "amount"]), "fn": create_coupon},
}
