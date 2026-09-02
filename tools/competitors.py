"""Competitor price intelligence for Israstore."""
from tools.web_search import fetch_page, web_search
from tools.woocommerce import _AUTH, _HEADERS, _get

COMPETITORS = [
    "jerseyniho.com",
    "liberokits.com",
    "sportcity.co.il",
]


def compare_prices(product_query: str) -> str:
    """For a jersey query: Israstore's price + what each competitor shows. Agent reads and compares."""
    out = [f"השוואת מחירים ל: {product_query}", ""]

    # Israstore's own listing
    try:
        mine = _get("products", {"search": product_query, "per_page": 3})
        if mine:
            out.append("**Israstore:**")
            for p in mine:
                out.append(f"  {p['name']} — {p.get('price','')}₪ ({p.get('permalink','')})")
        else:
            out.append("**Israstore:** לא נמצא מוצר תואם")
    except Exception as e:  # noqa: BLE001
        out.append(f"**Israstore:** שגיאה — {e}")
    out.append("")

    # Competitors
    for dom in COMPETITORS:
        out.append(f"**{dom}:**")
        try:
            results = web_search(f"{product_query} {dom}", max_results=3)
            url = None
            for line in results.splitlines():
                line = line.strip()
                if line.startswith("http") and dom in line:
                    url = line
                    break
            if url:
                page = fetch_page(url, max_chars=2500)
                out.append(f"  מקור: {url}")
                out.append(f"  {page[:1200]}")
            else:
                out.append(f"  {results[:600]}")
        except Exception as e:  # noqa: BLE001
            out.append(f"  שגיאה — {e}")
        out.append("")

    out.append(
        "נתח: מה המחיר של Israstore מול כל מתחרה? האם אנחנו יקרים/זולים משמעותית? "
        "המלץ מהלך (להוריד/להעלות/מבצע) רק אם יש פער אמיתי."
    )
    return "\n".join(out)


def israstore_top_sellers(limit: int = 5) -> list[str]:
    prods = _get(
        "products",
        {"orderby": "popularity", "order": "desc", "per_page": limit, "status": "publish"},
    )
    return [p["name"] for p in prods]


TOOLS = {
    "compare_competitor_prices": {
        "schema": {
            "name": "compare_competitor_prices",
            "description": (
                "משווה מחיר של מוצר בין Israstore לבין המתחרים "
                "(jerseyniho, liberokits, sportcity). קלט: תיאור המוצר, למשל 'חולצת ריאל מדריד בית'."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "product_query": {"type": "string", "description": "שם/תיאור המוצר להשוואה"}
                },
                "required": ["product_query"],
            },
        },
        "fn": compare_prices,
    }
}
