"""Automotive media review scraper — Stage 4a.

Targets major UK + German car review sites for Chinese brand coverage.
Uses Playwright for JS-rendered pages.

Targets (verified URLs):
  - What Car? (UK): https://www.whatcar.com/
  - Auto Express (UK): https://www.autoexpress.co.uk/
  - Auto Bild (DE): https://www.autobild.de/
  - Auto Motor und Sport (DE): https://www.auto-motor-und-sport.de/
"""

import json, time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "dashboard"
TIMEOUT = 30
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AutoExportIntel/1.0; +research)"}

SOURCES = [
    {
        "id": "whatcar",
        "name": "What Car? (UK)",
        "search_url": "https://www.whatcar.com/search?q=",
        "queries": ["BYD", "MG", "Chinese car", "NIO"],
        "parser": "generic",
    },
    {
        "id": "autoexpress",
        "name": "Auto Express (UK)",
        "search_url": "https://www.autoexpress.co.uk/search?search=",
        "queries": ["BYD", "MG", "Chinese EV", "NIO"],
        "parser": "generic",
    },
    {
        "id": "autobild",
        "name": "Auto Bild (DE)",
        "search_url": "https://www.autobild.de/suche/?query=",
        "queries": ["BYD", "MG", "NIO", "chinesische Autos"],
        "parser": "generic",
    },
    {
        "id": "ams",
        "name": "Auto Motor und Sport (DE)",
        "search_url": "https://www.auto-motor-und-sport.de/suche/?q=",
        "queries": ["BYD", "MG", "NIO", "China Elektroauto"],
        "parser": "generic",
    },
]


def fetch(url: str) -> str | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"  [WARN] {url[:60]}: {e}")
        return None


def parse_generic(html: str, source: dict, query: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    items = []
    # Generic: find <article>, <a> with href containing "/review/", "/news/"
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        text = a.get_text(strip=True)
        mark = text[:200] if text else (a.get("title", "") or a.get("aria-label", ""))[:200]
        if not mark or len(mark) < 10:
            continue
        # Check if relevant to our brands
        relevant = any(b.lower() in (href + mark).lower() for b in ["byd","mg ","nio","chinese","china","elektro"])
        if relevant:
            url = href if href.startswith("http") else "https://" + source["id"].replace("whatcar","www.whatcar.com").replace("autoexpress","www.autoexpress.co.uk").replace("autobild","www.autobild.de").replace("ams","www.auto-motor-und-sport.de") + href
            items.append({"source":source["id"],"source_name":source["name"],"query":query,"title":mark,"url":url})
    return items[:15]


def run():
    print(f"[{datetime.now():%H:%M:%S}] Starting media review scraper...")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    all_items = []
    for src in SOURCES:
        for q in src["queries"]:
            import urllib.parse
            url = src["search_url"] + urllib.parse.quote(q)
            html = fetch(url)
            if not html:
                continue
            items = parse_generic(html, src, q)
            if items:
                print(f"  {src['name']} / '{q}': {len(items)} articles")
            all_items.extend(items)
            time.sleep(1.5)

    with open(DATA_DIR / "media-data.json", "w", encoding="utf-8") as fh:
        json.dump({
            "updated": datetime.now(timezone.utc).isoformat(),
            "total_articles": len(all_items),
            "articles": all_items,
        }, fh, ensure_ascii=False)
    print(f"[{datetime.now():%H:%M:%S}] Done — {len(all_items)} articles")


if __name__ == "__main__":
    run()
