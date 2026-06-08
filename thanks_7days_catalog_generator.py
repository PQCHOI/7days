#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ISSEY MIYAKE THANKS 7 DAYS catalog generator
- Fetches public Shopify products.json from thanks-7days collection
- Generates a local HTML catalog: thanks_catalog.html
- No login required for JSON/product pages that are publicly accessible
"""

import json
import time
import html
from pathlib import Path
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ============================ Easy Settings ============================
COLLECTION_NAME = "thanks-7days"
BASE_URL = "https://www.isseymiyake.com"
PRODUCTS_JSON_URL = f"{BASE_URL}/collections/{COLLECTION_NAME}/products.json?limit=250&page={{page}}"
OUTPUT_HTML = "thanks_catalog.html"
TIMEOUT = 15
SLEEP_BETWEEN_PAGES = 0.8
MAX_PAGES = 20
ONLY_AVAILABLE = False  # True로 바꾸면 재고 있는 상품만 표시

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en;q=0.9,ko;q=0.8",
}


def build_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=0.6,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=8, pool_maxsize=8)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


def yen(value) -> str:
    if value is None or value == "":
        return "-"
    try:
        n = int(float(value))
        return f"¥{n:,}"
    except Exception:
        return str(value)


def product_url(handle: str) -> str:
    return f"{BASE_URL}/products/{handle}" if handle else BASE_URL


def image_url(product: dict) -> str:
    images = product.get("images") or []
    if images:
        return images[0].get("src") or ""
    variants = product.get("variants") or []
    for v in variants:
        img = v.get("featured_image") or {}
        if img.get("src"):
            return img["src"]
    return ""


def availability(product: dict) -> bool:
    return any(bool(v.get("available")) for v in product.get("variants", []))


def min_price(product: dict):
    vals = []
    for v in product.get("variants", []):
        try:
            vals.append(int(float(v.get("price"))))
        except Exception:
            pass
    return min(vals) if vals else None


def max_compare_price(product: dict):
    vals = []
    for v in product.get("variants", []):
        raw = v.get("compare_at_price")
        if raw in (None, ""):
            continue
        try:
            vals.append(int(float(raw)))
        except Exception:
            pass
    return max(vals) if vals else None


def variant_summary(product: dict) -> str:
    parts = []
    for v in product.get("variants", []):
        title = v.get("title") or ""
        sku = v.get("sku") or ""
        avail = "재고있음" if v.get("available") else "품절"
        price = yen(v.get("price"))
        parts.append(f"{title} / {price} / {avail}" + (f" / {sku}" if sku else ""))
    return "\n".join(parts)


def fetch_products() -> list[dict]:
    s = build_session()
    all_products = []
    for page in range(1, MAX_PAGES + 1):
        url = PRODUCTS_JSON_URL.format(page=page)
        print(f"fetch page={page}: {url}")
        r = s.get(url, headers=HEADERS, timeout=TIMEOUT)
        print(f"status={r.status_code}")
        if r.status_code != 200:
            print(f"stop: HTTP {r.status_code}")
            break
        try:
            data = r.json()
        except json.JSONDecodeError:
            print("stop: JSON decode failed")
            break
        products = data.get("products") or []
        if not products:
            print("stop: no products")
            break
        all_products.extend(products)
        if len(products) < 250:
            break
        time.sleep(SLEEP_BETWEEN_PAGES)
    return all_products


def generate_html(products: list[dict]) -> str:
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    rows = []
    visible_products = []
    for p in products:
        if ONLY_AVAILABLE and not availability(p):
            continue
        visible_products.append(p)

    for p in visible_products:
        title = html.escape(p.get("title") or "(no title)")
        handle = html.escape(p.get("handle") or "")
        url = html.escape(product_url(p.get("handle") or ""))
        img = html.escape(image_url(p))
        available = availability(p)
        badge = "재고있음" if available else "품절"
        badge_class = "ok" if available else "soldout"
        price = yen(min_price(p))
        compare = yen(max_compare_price(p))
        product_id = html.escape(str(p.get("id") or ""))
        tags = ", ".join([t for t in p.get("tags", []) if t in ("THANKS7DAYS", "優待")])
        tags = html.escape(tags)
        variants = html.escape(variant_summary(p))

        discount_text = ""
        mp = min_price(p)
        cp = max_compare_price(p)
        if mp and cp and cp > mp:
            rate = round((1 - mp / cp) * 100)
            discount_text = f"<span class='discount'>{rate}% OFF</span>"

        rows.append(f"""
        <article class="card" data-title="{title.lower()}" data-handle="{handle.lower()}" data-available="{str(available).lower()}">
            <a class="image-wrap" href="{url}" target="_blank" rel="noopener">
                {'<img src="' + img + '" alt="' + title + '" loading="lazy">' if img else '<div class="no-image">NO IMAGE</div>'}
            </a>
            <div class="body">
                <div class="topline">
                    <span class="badge {badge_class}">{badge}</span>
                    {discount_text}
                </div>
                <h2><a href="{url}" target="_blank" rel="noopener">{title}</a></h2>
                <div class="price-line">
                    <span class="price">{price}</span>
                    <span class="compare">{compare}</span>
                </div>
                <div class="meta">handle: {handle}</div>
                <div class="meta">id: {product_id}</div>
                <div class="tags">{tags}</div>
                <details>
                    <summary>색상/사이즈/재고 보기</summary>
                    <pre>{variants}</pre>
                </details>
            </div>
        </article>
        """)

    count_all = len(products)
    count_visible = len(visible_products)
    count_available = sum(1 for p in visible_products if availability(p))

    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ISSEY MIYAKE THANKS 7 DAYS Catalog</title>
<style>
:root {{
  --bg:#f6f5f2;
  --card:#ffffff;
  --text:#171717;
  --muted:#777;
  --line:#e7e2da;
  --ok:#0f7b45;
  --sold:#9b1c1c;
}}
* {{ box-sizing: border-box; }}
body {{
  margin:0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans KR", "Noto Sans JP", Arial, sans-serif;
  background:var(--bg);
  color:var(--text);
}}
header {{
  position: sticky;
  top: 0;
  z-index: 10;
  background: rgba(246,245,242,0.94);
  backdrop-filter: blur(10px);
  border-bottom:1px solid var(--line);
  padding:18px 22px;
}}
header h1 {{ margin:0 0 8px; font-size:22px; letter-spacing:-0.03em; }}
.controls {{ display:flex; gap:10px; flex-wrap:wrap; align-items:center; }}
input, select, button {{
  border:1px solid var(--line);
  background:#fff;
  padding:10px 12px;
  border-radius:10px;
  font-size:14px;
}}
button {{ cursor:pointer; }}
.stats {{ color:var(--muted); font-size:13px; margin-top:8px; }}
.grid {{
  padding:22px;
  display:grid;
  grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  gap:18px;
}}
.card {{
  background:var(--card);
  border:1px solid var(--line);
  border-radius:18px;
  overflow:hidden;
  box-shadow:0 8px 20px rgba(0,0,0,0.04);
}}
.image-wrap {{ display:block; aspect-ratio: 5 / 7; background:#eee; overflow:hidden; }}
.image-wrap img {{ width:100%; height:100%; object-fit:cover; display:block; transition: transform .25s; }}
.card:hover img {{ transform:scale(1.03); }}
.no-image {{ height:100%; display:flex; align-items:center; justify-content:center; color:#aaa; }}
.body {{ padding:14px; }}
.topline {{ display:flex; gap:8px; flex-wrap:wrap; align-items:center; min-height:26px; }}
.badge {{ color:white; padding:5px 8px; border-radius:999px; font-size:12px; font-weight:700; }}
.ok {{ background:var(--ok); }}
.soldout {{ background:var(--sold); }}
.discount {{ color:#7b3f00; background:#fff0cf; padding:5px 8px; border-radius:999px; font-size:12px; font-weight:700; }}
h2 {{ font-size:15px; line-height:1.35; margin:10px 0 8px; min-height:42px; }}
a {{ color:inherit; text-decoration:none; }}
a:hover {{ text-decoration:underline; }}
.price-line {{ display:flex; gap:8px; align-items:baseline; margin:8px 0; }}
.price {{ font-size:17px; font-weight:800; }}
.compare {{ color:var(--muted); text-decoration:line-through; font-size:13px; }}
.meta, .tags {{ color:var(--muted); font-size:12px; margin-top:4px; word-break:break-all; }}
details {{ margin-top:10px; font-size:12px; }}
summary {{ cursor:pointer; color:#333; }}
pre {{ white-space:pre-wrap; word-break:break-word; background:#f8f8f8; padding:10px; border-radius:10px; max-height:180px; overflow:auto; }}
footer {{ padding:30px 22px; color:var(--muted); font-size:12px; }}
.hidden {{ display:none !important; }}
</style>
</head>
<body>
<header>
  <h1>ISSEY MIYAKE THANKS 7 DAYS Catalog</h1>
  <div class="controls">
    <input id="q" type="search" placeholder="상품명/handle 검색" autocomplete="off">
    <select id="stock">
      <option value="all">전체</option>
      <option value="true">재고 있음만</option>
      <option value="false">품절만</option>
    </select>
    <button onclick="location.reload()">새로고침</button>
  </div>
  <div class="stats">
    생성시각: {html.escape(now)} / 전체 {count_all}개 / 표시 {count_visible}개 / 재고 있음 {count_available}개<br>
    가격은 products.json 기준입니다. 로그인 후 보이는 실제 우대/회원 가격과 다를 수 있습니다.
  </div>
</header>
<main class="grid" id="grid">
{''.join(rows)}
</main>
<footer>
  Source: {html.escape(PRODUCTS_JSON_URL.format(page=1))}<br>
  Product pages open at www.isseymiyake.com/products/&lt;handle&gt;
</footer>
<script>
const q = document.getElementById('q');
const stock = document.getElementById('stock');
const cards = [...document.querySelectorAll('.card')];
function applyFilter() {{
  const term = q.value.trim().toLowerCase();
  const st = stock.value;
  for (const card of cards) {{
    const text = (card.dataset.title + ' ' + card.dataset.handle).toLowerCase();
    const okText = !term || text.includes(term);
    const okStock = st === 'all' || card.dataset.available === st;
    card.classList.toggle('hidden', !(okText && okStock));
  }}
}}
q.addEventListener('input', applyFilter);
stock.addEventListener('change', applyFilter);
</script>
</body>
</html>"""


def main():
    products = fetch_products()
    print(f"products fetched: {len(products)}")
    html_text = generate_html(products)
    out = Path(OUTPUT_HTML)
    out.write_text(html_text, encoding="utf-8")
    print(f"saved: {out.resolve()}")


if __name__ == "__main__":
    main()
