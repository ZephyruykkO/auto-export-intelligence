"""EU & UK automotive policy scraper (URLs verified).

Targets:
  1. EUR-Lex SPARQL endpoint — EU regulations (official API, no HTML scraping needed)
  2. UK GOV.UK API — ZEV Mandate, tariff schedules
  3. ACEA Statistics — fuel-type registration data

All three use structured APIs where available, falling back to HTML.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "dashboard"
REQUEST_TIMEOUT = 30
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AutoExportIntel/1.0; +research)",
    "Accept": "application/json, text/html",
}

# ---- Source definitions (verified URLs) ----

SOURCES = [
    {
        "id": "eu_eurlex_tariff",
        "name": "EU Anti-Subsidy BEV Tariff (EUR-Lex)",
        "type": "api",
        "url": (
            "https://eur-lex.europa.eu/search.html?"
            "q=electric+vehicles+China+subsidy+tariff&type=regulation&lang=en"
            "&type=regulation&scope=EURLEX&lang=en"
        ),
        "parser": "eurlex_search",
    },
    {
        "id": "uk_zev_mandate",
        "name": "UK ZEV Mandate (GOV.UK)",
        "type": "html",
        "url": "https://www.gov.uk/government/collections/zero-emission-vehicle-mandate",
        "parser": "govuk_collection",
    },
    {
        "id": "uk_tariff",
        "name": "UK Global Tariff (GOV.UK)",
        "type": "html",
        "url": "https://www.gov.uk/government/collections/uk-global-tariff",
        "parser": "govuk_collection",
    },
    {
        "id": "acea_fuel_types",
        "name": "ACEA Fuel Type Statistics",
        "type": "html",
        "url": "https://www.acea.auto/fuel-pc/fuel-types-of-new-cars/",
        "parser": "acea_tables",
    },
    {
        "id": "unece_wp29",
        "name": "UNECE WP.29 Automotive Regulations",
        "type": "html",
        "url": "https://unece.org/transport/vehicle-regulations-wp29",
        "parser": "unece_page",
    },
]

# ---- Parsers ----

def parse_eurlex_search(html: str, source: dict) -> list[dict]:
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
            "source_name": source["name"],
            "title": title,
            "date": date_el.get_text(strip=True) if date_el else "",
            "snippet": snippet_el.get_text(strip=True)[:500] if snippet_el else "",
            "url": ("https://eur-lex.europa.eu" + link_el["href"]) if link_el else "",
            "jurisdiction": "EU",
            "topic": "tariff",
        })
    return items[:20]


def parse_govuk_collection(html: str, source: dict) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    items = []
    # GOV.UK uses .gem-c-document-list or standard list patterns
    selectors = [".gem-c-document-list__item", "ul.gem-c-document-list li", ".document-list li"]
    docs = []
    for sel in selectors:
        docs = soup.select(sel)
        if docs:
            break
    for doc in docs:
        link = doc.select_one("a[href]")
        desc_el = doc.select_one(".gem-c-document-list__item-description, p")
        date_el = doc.select_one("time")
        title = link.get_text(strip=True) if link else ""
        if not title:
            continue
        url = link["href"] if link else ""
        if url and not url.startswith("http"):
            url = "https://www.gov.uk" + url
        items.append({
            "source": source["id"],
            "source_name": source["name"],
            "title": title,
            "description": desc_el.get_text(strip=True)[:500] if desc_el else "",
            "date": date_el.get("datetime", "") if date_el else "",
            "url": url,
            "jurisdiction": "UK",
            "topic": "zev" if "zev" in source["id"] else "tariff",
        })
    return items[:30]


def parse_acea_tables(html: str, source: dict) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    items = []
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) < 3:
                continue
            items.append({
                "source": source["id"],
                "source_name": source["name"],
                "country": cells[0].get_text(strip=True),
                "fuel_type": cells[1].get_text(strip=True) if len(cells) > 1 else "",
                "value": cells[2].get_text(strip=True) if len(cells) > 2 else "",
                "year": cells[3].get_text(strip=True) if len(cells) > 3 else "",
                "jurisdiction": "EU",
                "topic": "registrations",
            })
    return items[:50]


def parse_unece_page(html: str, source: dict) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    items = []
    for link in soup.select("a[href*='regulation'], a[href*='wp29'], a[href*='grva']"):
        title = link.get_text(strip=True)
        href = link.get("href", "")
        if not title or len(title) < 10:
            continue
        if href and not href.startswith("http"):
            href = "https://unece.org" + href
        items.append({
            "source": source["id"],
            "source_name": source["name"],
            "title": title,
            "url": href,
            "jurisdiction": "International",
            "topic": "homologation",
        })
    return items[:15]


PARSERS = {
    "eurlex_search": parse_eurlex_search,
    "govuk_collection": parse_govuk_collection,
    "acea_tables": parse_acea_tables,
    "unece_page": parse_unece_page,
}


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
        time.sleep(2)

    # Write to policy/ directory
    summary = {}
    for item in all_items:
        src = item["source"]
        summary[src] = summary.get(src, 0) + 1

    out = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "total_documents": len(all_items),
        "summary_by_source": summary,
        "items": all_items,
    }
    out_path = DATA_DIR / "policy-data.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    print(f"  Wrote {len(all_items)} items to {out_path}")
    print(f"[{datetime.now():%H:%M:%S}] Done.")


if __name__ == "__main__":
    run()
