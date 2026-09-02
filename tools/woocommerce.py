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


def failed_payments(days: int = 7, limit: int = 20) -> str:
    """Orders where payment actually failed (card declined etc) — high-intent, ready to buy."""
    from datetime import datetime, timedelta, timezone

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    orders = _get(
        "orders",
        {"status": "failed", "per_page": min(limit, 30), "orderby": "date", "order": "desc"},
    )
    rows = []
    for o in orders:
        created = datetime.fromisoformat(o["date_created_gmt"] + "+00:00")
        if created < cutoff:
            continue
        b = o.get("billing", {})
        items = ", ".join(f"{li['quantity']}x {li['name']}" for li in o.get("line_items", []))
        rows.append(
            f"#{o['id']} · {o['total']} {o['currency']} · {b.get('first_name','')} · "
            f"{b.get('phone','') or b.get('email','') or 'אין קשר'}\n"
            f"  {o['date_created'][:16]} · {items}"
        )
    if not rows:
        return "אין תשלומים שנכשלו בטווח הזה. 👍"
    return (
        f"תשלומים שנכשלו ({len(rows)}) — לקוחות שרצו לקנות והכרטיס נדחה:\n\n"
        + "\n\n".join(rows)
    )


def abandoned_checkouts(hours_old: int = 2, limit: int = 15) -> str:
    """Pending/failed orders older than `hours_old` with customer contact = likely abandoned carts."""
    from datetime import datetime, timedelta, timezone

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_old)
    found = []
    for status in ("pending", "failed"):
        orders = _get(
            "orders",
            {"status": status, "per_page": min(limit, 25), "orderby": "date", "order": "desc"},
        )
        for o in orders:
            b = o.get("billing", {})
            if not (b.get("email") or b.get("phone")):
                continue
            created = datetime.fromisoformat(o["date_created_gmt"] + "+00:00")
            if created > cutoff:
                continue
            items = ", ".join(
                f"{li['quantity']}x {li['name']}" for li in o.get("line_items", [])
            )
            found.append(
                f"#{o['id']} · {status} · {o['total']} {o['currency']} · "
                f"{b.get('first_name','')} · {b.get('phone','') or b.get('email','')}\n"
                f"  נוצר {o['date_created'][:16]} · {items}"
            )
    if not found:
        return "אין עגלות נטושות פתוחות. 👍"
    return f"עגלות נטושות ({len(found)}):\n\n" + "\n\n".join(found)


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
    product_id: str,
    price: str = "",
    stock_quantity: str = "",
    sale_price: str = "",
    status: str = "",
    description: str = "",
) -> str:
    body: dict = {}
    if price:
        body["regular_price"] = str(price)
    if sale_price:
        body["sale_price"] = str(sale_price)
    if stock_quantity != "":
        body["stock_quantity"] = int(stock_quantity)
        body["manage_stock"] = True
    if status:
        body["status"] = status  # 'publish' / 'draft' / 'private'
    if description:
        body["description"] = description
    if not body:
        return "לא צוין מה לעדכן."
    p = _put(f"products/{product_id}", body)
    return (
        f"עודכן [{p['id']}] {p['name']}: מחיר {p.get('price')}₪, "
        f"מלאי {p.get('stock_quantity')}, סטטוס {p.get('status')}"
    )


def create_product(
    name: str,
    price: str,
    description: str = "",
    category: str = "",
    stock_quantity: str = "",
    image_url: str = "",
    sku: str = "",
) -> str:
    body: dict = {
        "name": name,
        "type": "simple",
        "regular_price": str(price),
        "status": "draft",  # created as draft — Noam publishes when ready
    }
    if description:
        body["description"] = description
        body["short_description"] = description[:300]
    if sku:
        body["sku"] = sku
    if stock_quantity != "":
        body["manage_stock"] = True
        body["stock_quantity"] = int(stock_quantity)
    if image_url:
        body["images"] = [{"src": image_url}]
    if category:
        cats = _get("products/categories", {"search": category, "per_page": 1})
        if cats:
            body["categories"] = [{"id": cats[0]["id"]}]
        else:
            new_cat = _post("products/categories", {"name": category})
            body["categories"] = [{"id": new_cat["id"]}]
    p = _post("products", body)
    return (
        f"נוצר מוצר כטיוטה [{p['id']}]: {p['name']} · {p.get('regular_price')}₪\n"
        f"קישור עריכה: {p.get('permalink','')}\n"
        f"הוא במצב 'טיוטה' — תגיד לי לפרסם אותו כשמוכן (woo_update_product עם status)."
    )


def duplicate_product(
    source_product_id: str,
    new_name: str,
    price: str = "",
    description: str = "",
    sku: str = "",
) -> str:
    """Clone an existing product (images, category, price, attributes) with a new name."""
    src = _get(f"products/{source_product_id}")
    body: dict = {
        "name": new_name,
        "type": src.get("type", "simple"),
        "status": "draft",
        "regular_price": str(price) if price else src.get("regular_price", ""),
        "description": description or src.get("description", ""),
        "short_description": (description or src.get("short_description", ""))[:400],
        "categories": [{"id": c["id"]} for c in src.get("categories", [])],
        "tags": [{"id": t["id"]} for t in src.get("tags", [])],
        "images": [{"src": im["src"]} for im in src.get("images", []) if im.get("src")],
        "attributes": src.get("attributes", []),
        "weight": src.get("weight", ""),
        "dimensions": src.get("dimensions", {}),
    }
    if sku:
        body["sku"] = sku
    p = _post("products", body)
    return (
        f"שוכפל מ-[{source_product_id}] '{src.get('name')}'\n"
        f"מוצר חדש (טיוטה) [{p['id']}]: {p['name']} · {p.get('regular_price')}₪\n"
        f"ירש {len(body['images'])} תמונות ו-{len(body['categories'])} קטגוריות.\n"
        f"עריכה: {p.get('permalink','')}\n"
        f"אמור לי לפרסם כשמוכן."
    )


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
    "woo_abandoned_checkouts": {**_sch(
        "woo_abandoned_checkouts",
        "מציג עגלות נטושות — הזמנות pending/failed ישנות מ-2 שעות עם פרטי קשר של לקוח. השתמש כשנועם רוצה לשחזר עגלות.",
        {"hours_old": {"type": "integer", "description": "מינימום גיל בשעות, ברירת מחדל 2"}}, []),
        "fn": abandoned_checkouts},
    "woo_failed_payments": {**_sch(
        "woo_failed_payments",
        "מציג הזמנות שבהן התשלום נכשל (כרטיס נדחה) — לקוחות עם כוונת קנייה גבוהה. days = כמה ימים אחורה.",
        {"days": {"type": "integer", "description": "כמה ימים אחורה, ברירת מחדל 7"}}, []),
        "fn": failed_payments},
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
        "מעדכן מוצר קיים: מחיר, מלאי, מחיר מבצע, תיאור, או status (publish/draft). דורש אישור מפורש מנועם.",
        {"product_id": {"type": "string"}, "price": {"type": "string"},
         "stock_quantity": {"type": "string"}, "sale_price": {"type": "string"},
         "status": {"type": "string", "description": "publish / draft / private"},
         "description": {"type": "string"}},
        ["product_id"]), "fn": update_product},
    "woo_create_product": {**_sch(
        "woo_create_product",
        "יוצר מוצר חדש ב-Israstore מאפס (כטיוטה, נועם מפרסם). דורש אישור מפורש מנועם.",
        {"name": {"type": "string"}, "price": {"type": "string"},
         "description": {"type": "string"}, "category": {"type": "string"},
         "stock_quantity": {"type": "string"}, "image_url": {"type": "string"},
         "sku": {"type": "string"}},
        ["name", "price"]), "fn": create_product},
    "woo_duplicate_product": {**_sch(
        "woo_duplicate_product",
        "משכפל מוצר קיים (יורש תמונות, קטגוריה, מחיר, מאפיינים) ומשנה שם/מחיר/תיאור. "
        "הדרך הקלה להוסיף וריאציות (למשל אותה חולצה עם פאץ' ליגה אחר). נוצר כטיוטה. דורש אישור מנועם.",
        {"source_product_id": {"type": "string", "description": "id של המוצר לשכפול"},
         "new_name": {"type": "string", "description": "השם החדש"},
         "price": {"type": "string"}, "description": {"type": "string"}, "sku": {"type": "string"}},
        ["source_product_id", "new_name"]), "fn": duplicate_product},
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
