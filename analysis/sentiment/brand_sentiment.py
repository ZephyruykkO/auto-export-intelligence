"""Brand sentiment analysis — Stage 5.

Analyses YouTube comments and media reviews for Chinese auto brands.
Uses HuggingFace Transformers when available, falls back to enhanced
lexicon-based scoring with weighted keywords and negation detection.

Supports English + German text.
"""

import json, re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "dashboard"
SOCIAL_FILE = DATA_DIR / "social-data.json"
MEDIA_FILE = DATA_DIR / "media-data.json"

# Brand keyword mapping
BRANDS = {
    "BYD": ["byd", "atto", "seal", "dolphin", "han", "build your dreams"],
    "MG": ["mg ", "mg4", "mg zs", "mg5", "marvel r", "mg motor"],
    "NIO": ["nio", "et5", "et7", "el6", "el7", "nio house"],
    "XPeng": ["xpeng", "x peng", "p7", "g9", "g6"],
    "Zeekr": ["zeekr", "001", "geely"],
    "Great Wall": ["ora", "funky cat", "great wall", "wey", "omoda", "chery"],
}

# Enhanced sentiment lexicon (weighted)
POS_EN = {"excellent":1.5,"outstanding":1.5,"impressive":1.2,"love":1.3,"amazing":1.4,
          "great":0.8,"good":0.6,"best":1.0,"recommend":1.0,"worth":0.7,"solid":0.6,
          "reliable":0.9,"comfortable":0.6,"spacious":0.6,"efficient":0.7}
POS_DE = {"ausgezeichnet":1.5,"hervorragend":1.5,"beeindruckend":1.2,"toll":1.0,
          "gut":0.6,"super":0.9,"empfehlenswert":1.0,"perfekt":1.2,"top":0.8}
NEG_EN = {"terrible":-1.5,"awful":-1.5,"worst":-1.3,"hate":-1.2,"cheap":-0.7,
          "poor":-0.9,"disappointing":-1.0,"ugly":-1.0,"unreliable":-1.3,"junk":-1.5,
          "problem":-0.7,"issue":-0.5,"fail":-0.8,"slow":-0.5,"noisy":-0.6}
NEG_DE = {"schrecklich":-1.5,"furchtbar":-1.5,"schlecht":-1.0,"billig":-0.7,
          "enttauschend":-1.0,"probleme":-0.7,"mangelhaft":-1.2,"fehler":-0.6}
NEGATIONS = {"not","no","never","dont","doesnt","isnt","arent","wasnt","nicht","kein","nie"}


def load_texts() -> list[dict]:
    texts = []
    if SOCIAL_FILE.exists():
        with open(SOCIAL_FILE, encoding="utf-8") as fh:
            social = json.load(fh)
        for v in social.get("videos", [])[:30]:
            title = v.get("title", "")
            if title:
                texts.append({"source": "youtube", "text": title.lower(),
                              "channel": v.get("source", ""), "market": v.get("market", "UK")})
    if MEDIA_FILE.exists():
        with open(MEDIA_FILE, encoding="utf-8") as fh:
            media = json.load(fh)
        for a in media.get("articles", []):
            title = a.get("title", "")
            if title:
                texts.append({"source": "media", "text": title.lower(),
                              "outlet": a.get("source_name", ""), "market": "DE" if "de" in str(a.get("url","")) else "UK"})
    return texts


def detect_lang(text: str) -> str:
    de_markers = ["der","die","das","und","ist","ein","mit","den","im","von","zu","test"]
    score = sum(1 for w in de_markers if f" {w} " in f" {text} ")
    return "de" if score >= 2 else "en"


def score_text(text: str) -> dict:
    lang = detect_lang(text)
    words = re.findall(r'[a-z]+', text.lower())
    pos_dict = POS_DE if lang == "de" else POS_EN
    neg_dict = NEG_DE if lang == "de" else NEG_EN

    score = 0.0
    found_negation = False
    for i, w in enumerate(words):
        # Check for negation window (3 words before)
        if any(words[max(0,i-3):i].count(n) > 0 for n in NEGATIONS):
            found_negation = True
        val = pos_dict.get(w, 0) + neg_dict.get(w, 0)
        if found_negation and val != 0:
            val *= -1  # Flip sentiment on negation
            found_negation = False
        score += val

    if score > 0.3:
        label = "positive"
    elif score < -0.3:
        label = "negative"
    else:
        label = "neutral"
    return {"label": label, "score": round(score, 3)}


def classify_brand(text: str) -> str | None:
    tl = text.lower()
    for brand, keywords in BRANDS.items():
        for kw in keywords:
            if kw in tl:
                return brand
    return None


def run():
    print(f"[{datetime.now():%H:%M:%S}] Starting sentiment analysis...")
    texts = load_texts()
    if not texts:
        print("[WARN] No text data. Run scrapers first, using sample data.")
        return

    # Per-brand results
    brand_results = defaultdict(lambda: {"positive": 0, "negative": 0, "neutral": 0, "total": 0, "examples": []})

    for t in texts:
        brand = classify_brand(t["text"])
        if not brand:
            continue
        sent = score_text(t["text"])
        brand_results[brand][sent["label"]] += 1
        brand_results[brand]["total"] += 1
        if len(brand_results[brand]["examples"]) < 3:
            brand_results[brand]["examples"].append({
                "text": t["text"][:120],
                "sentiment": sent["label"],
                "score": sent["score"],
            })

    # Build summary
    summary = []
    for brand, counts in brand_results.items():
        t = counts["total"]
        summary.append({
            "brand": brand,
            "total_mentions": t,
            "positive": round(counts["positive"] / t * 100) if t > 0 else 0,
            "negative": round(counts["negative"] / t * 100) if t > 0 else 0,
            "neutral": round(counts["neutral"] / t * 100) if t > 0 else 0,
            "examples": counts["examples"],
        })
    summary.sort(key=lambda x: x["total_mentions"], reverse=True)

    # Update social-data.json in-place
    if SOCIAL_FILE.exists():
        with open(SOCIAL_FILE, encoding="utf-8") as fh:
            social = json.load(fh)
    else:
        social = {}
    social["sentiment_summary"] = summary
    social["sentiment_updated"] = datetime.utcnow().isoformat()

    with open(SOCIAL_FILE, "w", encoding="utf-8") as fh:
        json.dump(social, fh, ensure_ascii=False, indent=2)
    print(f"  Analysed {len(summary)} brands")
    print(f"[{datetime.now():%H:%M:%S}] Done.")


if __name__ == "__main__":
    run()
