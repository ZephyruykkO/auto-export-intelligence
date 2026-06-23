"""Germany car registration data scraper.
Targets KBA (Kraftfahrt-Bundesamt) monthly new car registration data.
"""
import json, time
from datetime import datetime
from pathlib import Path
import pandas as pd, requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.kba.de/DE/Statistik/Fahrzeuge/Neuzulassungen/neuzulassungen_node.html"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUTPUT_FILE = DATA_DIR / "germany_brand_sales.json"
REQUEST_TIMEOUT = 30
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0.0.0 Safari/537.36","Accept": "text/html,application/xhtml+xml","Accept-Language": "de-DE,de;q=0.9"}
DE_BRANDS = ["Volkswagen","Mercedes-Benz","BMW","Audi","Opel","Ford","Skoda","Hyundai","Seat","Toyota","Renault","Kia","Dacia","Tesla","Fiat","Peugeot","Citroen","Mazda","Volvo","MINI","Porsche","Cupra","Suzuki","Land Rover","Honda","Nissan","MG","Lexus","BYD","Jaguar"]

def fetch_page(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as exc:
        print(f"[ERROR] {url}: {exc}")
        return None

def parse_table_to_records(html, year):
    soup = BeautifulSoup(html, "lxml")
    records = []
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) < 13: continue
            brand_text = cells[0].get_text(strip=True)
            matched = next((b for b in DE_BRANDS if b.lower() in brand_text.lower()), None)
            if not matched: continue
            months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
            for idx, month in enumerate(months):
                try: value = int(cells[idx+1].get_text(strip=True).replace(".","").replace(",",""))
                except (ValueError, IndexError): value = 0
                records.append({"brand":matched,"year":year,"month":month,"registrations":value,"market":"Germany"})
    return records

def run():
    print(f"[{datetime.now():%H:%M:%S}] Starting Germany scraper...")
    all_records = []
    for year in (2025, 2026):
        html = fetch_page(BASE_URL)
        if not html: print(f"[WARN] No HTML for {year} -- skipping"); continue
        records = parse_table_to_records(html, year)
        print(f"  {year}: {len(records)} rows parsed")
        all_records.extend(records)
        time.sleep(1)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
        json.dump(all_records, fh, ensure_ascii=False, indent=2)
    print(f"[{datetime.now():%H:%M:%S}] Done - {OUTPUT_FILE}")

if __name__ == "__main__": run()
