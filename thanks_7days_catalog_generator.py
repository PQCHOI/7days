import html
from datetime import datetime, timezone, timedelta

import requests

COLLECTION_JSON_URL = "https://www.isseymiyake.com/collections/thanks-7days/products.json?limit=250&page=1"
PRODUCT_BASE_URL = "https://www.isseymiyake.com/products/"
OUTPUT_FILE = "index.html"


def yen(value):
    try:
        return f"{int(value):,}円"
    except Exception:
        return "-"


def fetch_products():
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json,text/plain,*/*",
    }
    response = requests.get(COLLECTION_JSON_URL, headers=headers, timeout=20)
    response.raise_for_status()
    data = response.json()
    return data.get("products", [])


def product_available(product):
    return any(v.get("available") is True for v in product.get("variants", []))


def first_image(product):
    images = product.get("images") or []
    if images:
        return images[0].get("src", "")
    return ""


def first_variant(product):
    variants = product.get("variants") or []
    if variants:
        return variants[0]
    return {}


def build_html(products):
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst).strftime("%Y-%m-%d %H:%M:%S JST")

    cards = []

    for product in products:
        title = html.escape(product.get("title", "No title"))
        handle = product.get("handle", "")
        url = PRODUCT_BASE_URL + handle if handle else "#"
        image = first_image(product)
        available = product_available(product)

        variant = first_variant(product)
        price = yen(variant.get("price"))
        compare_price = yen(variant.get("compare_at_price"))

        tags = product.get("tags") or []
        tag_text = ", ".join(tags[:8])
        tag_text = html.escape(tag_text)

        status_class = "available" if available else "soldout"
        status_text = "재고 있음" if available else "품절"

        card = f"""
        <article class="card">
            <a href="{html.escape(url)}" target="_blank" rel="noopener">
                <div class="image-wrap">
                    <img src="{html.escape(image)}" alt="{title}" loading="lazy">
                </div>
            </a>
            <div class="content">
                <div class="status {status_class}">{status_text}</div>
                <h2>{title}</h2>
                <p class="price">가격: {price}</p>
                <p class="compare">정상가: {compare_price}</p>
                <p class="tags">{tag_text}</p>
                <a class="button" href="{html.escape(url)}" target="_blank" rel="noopener">상품 보기</a>
            </div>
        </article>
        """
        cards.append(card)

    total = len(products)
    available_count = sum(1 for p in products if product_available(p))

    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>THANKS 7DAYS Catalog</title>
<style>
    body {{
        margin: 0;
        font-family: Arial, sans-serif;
        background: #f5f5f3;
        color: #222;
    }}
    header {{
        position: sticky;
        top: 0;
        z-index: 10;
        background: rgba(255,255,255,0.94);
        border-bottom: 1px solid #ddd;
        padding: 18px 24px;
        backdrop-filter: blur(8px);
    }}
    h1 {{
        margin: 0 0 8px;
        font-size: 24px;
    }}
    .summary {{
        font-size: 14px;
        color: #555;
    }}
    .grid {{
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
        gap: 18px;
        padding: 22px;
    }}
    .card {{
        background: #fff;
        border: 1px solid #ddd;
        border-radius: 14px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }}
    .image-wrap {{
        background: #eee;
        aspect-ratio: 5 / 7;
        overflow: hidden;
    }}
    img {{
        width: 100%;
        height: 100%;
        object-fit: cover;
        display: block;
    }}
    .content {{
        padding: 14px;
    }}
    h2 {{
        font-size: 15px;
        line-height: 1.35;
        min-height: 42px;
        margin: 10px 0;
    }}
    .status {{
        display: inline-block;
        padding: 4px 9px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: bold;
    }}
    .available {{
        background: #e8f7e8;
        color: #167a2e;
    }}
    .soldout {{
        background: #f7e8e8;
        color: #a82222;
    }}
    .price {{
        font-weight: bold;
        margin: 8px 0 4px;
    }}
    .compare {{
        color: #777;
        font-size: 13px;
        margin: 0 0 8px;
    }}
    .tags {{
        color: #777;
        font-size: 11px;
        line-height: 1.35;
        min-height: 32px;
    }}
    .button {{
        display: block;
        text-align: center;
        margin-top: 12px;
        padding: 9px 10px;
        border-radius: 8px;
        background: #222;
        color: #fff;
        text-decoration: none;
        font-size: 13px;
    }}
    footer {{
        padding: 24px;
        text-align: center;
        color: #777;
        font-size: 12px;
    }}
</style>
</head>
<body>
<header>
    <h1>THANKS 7DAYS Catalog</h1>
    <div class="summary">
        총 상품 {total}개 / 재고 있음 {available_count}개 / 마지막 업데이트 {now}
    </div>
</header>
<main class="grid">
    {''.join(cards)}
</main>
<footer>
    Generated from public products.json
</footer>
</body>
</html>
"""


def main():
    products = fetch_products()
    page = build_html(products)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(page)

    print(f"Generated {OUTPUT_FILE} with {len(products)} products.")


if __name__ == "__main__":
    main()
