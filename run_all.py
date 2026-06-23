#!/usr/bin/env python3
"""Master runner — runs all scrapers and regenerates dashboard data.

Usage: python run_all.py

Runs all stages in sequence, updates dashboard JSON files,
and prints a summary of results.
"""

import subprocess, sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STAGES = [
    ("Stage 1: UK Sales", f"{ROOT}/scrapers/sales/uk_smmt.py"),
    ("Stage 1: DE Sales", f"{ROOT}/scrapers/sales/de_kba.py"),
    ("Stage 2: Policy", f"{ROOT}/scrapers/policy/eu_uk_policy.py"),
    ("Stage 3: Charging Infra", f"{ROOT}/scrapers/infra/openchargemap.py"),
    ("Stage 4a: Media Reviews", f"{ROOT}/scrapers/media/media_reviews.py"),
    ("Stage 4b: YouTube", f"{ROOT}/scrapers/social/youtube.py"),
    ("Stage 5: Sentiment", f"{ROOT}/analysis/sentiment/brand_sentiment.py"),
    ("Stage 6: TCO", f"{ROOT}/analysis/tco/tco_calculator.py"),
    ("Stage 6: Forecast", f"{ROOT}/analysis/forecasting/sales_forecast.py"),
]


def run_stage(name, script):
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")
    result = subprocess.run([sys.executable, script], capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(f"  [ERROR] {result.stderr}")
        return False
    return True


def main():
    print("=" * 60)
    print("  Auto Export Intelligence — Full Data Pipeline")
    print("=" * 60)

    ok = 0
    fail = 0
    for name, script in STAGES:
        if not Path(script).exists():
            print(f"\n  [SKIP] {name} — script not found: {script}")
            continue
        if run_stage(name, script):
            ok += 1
        else:
            fail += 1

    print(f"\n{'='*60}")
    print(f"  Done: {ok} OK, {fail} failed, {len(STAGES)-ok-fail} skipped")
    print(f"{'='*60}")

    # Quick data check
    dashboard = ROOT / "dashboard"
    stats = {}
    for f in dashboard.glob("*.json"):
        try:
            data = json.loads(f.read_text())
            stats[f.name] = len(json.dumps(data))
        except Exception:
            stats[f.name] = "ERROR"
    print(f"\n  Dashboard JSON files:")
    for name, size in sorted(stats.items()):
        print(f"    {name}: {size}")


if __name__ == "__main__":
    main()
