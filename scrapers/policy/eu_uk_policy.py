"""EU & UK automotive policy scraper.

Targets:
  1. EUR-Lex: EU anti-subsidy tariff regulations (BEV from China)
  2. UK Gov: ZEV Mandate updates, BIK rates, tariff schedules
  3. ACEA: European auto industry statistics & policy positions

All three sources are HTML-first and crawlable without JS rendering.
"""

import json
import re
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "policy"
REQUEST_TIMEOUT = 30
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AutoExportIntel/1.0; +research)",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-GB,en;q=0.9,de;q=0.8",
}

# ---- Sources ----

SOURCES = [
    {
        "id": "eu_eurlex_bev_tariff",
        "name": "EU Anti-Subsidy BEV Tariff",
        "url": "https://eur-lex.europa.eu/search.html?q=electric+vehicles+China+subsidy+tariff",
        "parser": "eurlex",
    },
    {
        "id": "uk_zev_mandate",
        "name": "UK ZEV Mandate",
        "url": "https://www.gov.uk/government/collections/zero-emission-vehicle-mandate",
        "parser": "govuk",
    },
    {
        "id": "acea_stats",
        "name": "ACEA Statistics",
        "url": "https://www.acea.auto/fuel-pc/fuel-types-of-new-cars/",
        "parser": "acea",
    },
]

# ---- Parsers ----

def parse_eurlex(html: str, source: dict) -> list[dict]:
    """Extract regulation titles and dates from EUR-Lex search results."""
    soup = BeautifulSoup(html, "lxml")
    items = []
    for result in soup.select(".SearchResult"):
        title_el = result.select_one(".SearchResult-title")
        date_el = result.select_one(".SearchResult-date")
        snippet_el = result.select_one(".SearchResult-snippet")
        link_el = result.select_one("a[href]")

        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            continue

        items.append({
            "source": source["id"],
            "title": title,
            "date": date_el.get_text(strip=True) if date_el else "",
            "snippet": snippet_el.get_text(strip=True)[:500] if snippet_el else "",
            "url": "https://eur-lex.europa.eu" + link_el["href"] if link_el else "",
        })
    return items[:20]  # Keep recent 20


def parse_govuk(html: str, source: dict) -> list[dict]:
    """Extract policy document links from GOV.UK collection pages."""
    soup = BeautifulSoup(html, "lxml")
    items = []
    for doc in soup.select(".gem-c-document-list__item"):
        title_el = doc.select_one(".gem-c-document-list__item-title a")
        desc_el = doc.select_one(".gem-c-document-list__item-description")
        date_el = doc.select_one(".gem-c-document-list__item-metadata time")

        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            continue

        items.append({
            "source": source["id"],
            "title": title,
            "description": desc_el.get_text(strip=True)[:500] if desc_el else "",
            "date": date_el.get("datetime", "") if date_el else "",
            "url": "https://www.gov.uk" + title_el["href"] if title_el else "",
        })
    return items[:30]


def parse_acea(html: str, source: dict) -> list[dict]:
    """Extract fuel-type registration data tables from ACEA."""
    soup = BeautifulSoup(html, "lxml")
    items = []
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows[1:]:  # Skip header
            cells = row.find_all(["td", "th"])
            if len(cells) < 3:
                continue
            items.append({
                "source": source["id"],
                "country": cells[0].get_text(strip=True),
                "fuel_type": cells[1].get_text(strip=True) if len(cells) > 1 else "",
                "value": cells[2].get_text(strip=True) if len(cells) > 2 else "",
                "year": cells[3].get_text(strip=True) if len(cells) > 3 else "",
            })
    return items[:50]


PARSERS = {
    "eurlex": parse_eurlex,
    "govuk": parse_govuk,
    "acea": parse_acea,
}


# ---- Fetcher ----

def fetch_page(url: str) -> str | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        print(f"[ERROR] {url}: {e}")
        return None


def run():
    print(f"[{datetime.now():%H:%M:%S}] Starting policy scraper...")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    all_items = []
    for source in SOURCES:
        print(f"  Fetching: {source['name']}...")
        html = fetch_page(source["url"])
        if not html:
            continue

        parser = PARSERS.get(source["parser"])
        if parser:
            items = parser(html, source)
            print(f"    Parsed {len(items)} items")
            all_items.extend(items)
        time.sleep(2)  # Polite delay

    out_path = DATA_DIR / "policy_documents.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(all_items, fh, ensure_ascii=False, indent=2)
    print(f"  Wrote {len(all_items)} policy items to {out_path}")

    # Also generate a human-readable summary
    summary = {}
    for item in all_items:
        src = item["source"]
        if src not in summary:
            summary[src] = 0
        summary[src] += 1

    print(f"
  Summary by source:")
    for src, count in summary.items():
        print(f"    {src}: {count} documents")
    print(f"[{datetime.now():%H:%M:%S}] Done.")


if __name__ == "__main__":
    run()
