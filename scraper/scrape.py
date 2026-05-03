#!/usr/bin/env python3
"""
Scrapes Medical Physics PhD positions from RSS feeds.

Sources are configured in sources.json (active=true entries are scraped daily).
Manual positions can be added to data/manual_positions.json.

Run locally: cd scraper && python scrape.py
"""

import json
import re
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

FETCH_TIMEOUT = 15  # seconds per source

SCRAPER_DIR = Path(__file__).parent
REPO_ROOT = SCRAPER_DIR.parent

FEEDPARSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"
)

SKILLS_KEYWORDS = [
    "Python", "MATLAB", "Monte Carlo", "Geant4", "GATE", "EGSnrc", "FLUKA",
    "radiation therapy", "radiotherapy", "dosimetry", "MRI", "CT", "PET",
    "SPECT", "nuclear medicine", "linac", "treatment planning", "TPS",
    "machine learning", "deep learning", "image processing", "image segmentation",
    "C++", "DICOM", "proton therapy", "brachytherapy", "medical imaging",
    "health physics", "radiation protection", "ultrasound", "x-ray",
    "fluoroscopy", "radiomics", "neural network", "computer vision",
]

PHD_TERMS = [
    "phd", "ph.d", "doctoral", "doctorate", "graduate student",
    "graduate position", "studentship", "dphil", "grad student",
    "research student", "phd studentship", "phd fellowship",
]

PHYSICS_TERMS = [
    "medical physics", "medphys", "med phys", "radiotherapy",
    "dosimetry", "nuclear medicine", "radiation oncology",
    "imaging physics", "health physics", "radiation therapy",
]


def load_sources() -> list:
    path = SCRAPER_DIR / "sources.json"
    sources = json.loads(path.read_text())
    active = [s for s in sources if s.get("active", True)]
    print(f"Loaded {len(active)} active sources (of {len(sources)} total in bank)\n")
    return active


def load_manual_positions() -> list:
    path = REPO_ROOT / "data" / "manual_positions.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    return data.get("positions", [])


def extract_skills(text: str) -> list:
    found = []
    text_lower = text.lower()
    for skill in SKILLS_KEYWORDS:
        if skill.lower() in text_lower:
            found.append(skill)
    return list(dict.fromkeys(found))


def extract_deadline(text: str) -> str | None:
    patterns = [
        r"(?:deadline|apply by|application deadline|applications?\s+(?:due|close[sd]?)|closing date)[:\s]+([A-Za-z]+ \d{1,2},?\s*\d{4})",
        r"(?:deadline|apply by|application deadline|applications?\s+(?:due|close[sd]?)|closing date)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"(?:deadline|apply by|application deadline|applications?\s+(?:due|close[sd]?)|closing date)[:\s]+(\d{4}-\d{2}-\d{2})",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                dt = dateparser.parse(m.group(1))
                return dt.strftime("%Y-%m-%d")
            except Exception:
                pass
    return None


def extract_professor(text: str) -> str | None:
    patterns = [
        r"(?:contact|PI|advisor|supervisor|principal investigator)[:\s]+(?:Prof(?:essor)?\.?\s+|Dr\.?\s+)?([A-Z][a-z]+ [A-Z][a-z]+)",
        r"(?:supervised by|led by)[:\s]+(?:Prof(?:essor)?\.?\s+|Dr\.?\s+)([A-Z][a-z]+ [A-Z][a-z]+)",
        r"(?:Prof(?:essor)?\.?|Dr\.?)\s+([A-Z][a-z]+ [A-Z][a-z]+)",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(1)
    return None


def extract_institution(entry) -> str:
    for field in ("source", "author_detail"):
        val = getattr(entry, field, None)
        if isinstance(val, dict) and val.get("title"):
            return val["title"]
    return ""


def is_phd_related(title: str, description: str) -> bool:
    text = (title + " " + description).lower()
    has_phd = any(t in text for t in PHD_TERMS)
    has_physics = any(t in text for t in PHYSICS_TERMS)
    return has_phd and has_physics


def make_id(url: str, title: str) -> str:
    return hashlib.md5(f"{url}{title}".encode()).hexdigest()[:12]


def scrape_rss(source: dict) -> list:
    positions = []
    try:
        resp = requests.get(
            source["url"],
            headers={"User-Agent": FEEDPARSER_UA},
            timeout=FETCH_TIMEOUT,
            allow_redirects=True,
        )
        feed = feedparser.parse(resp.content)
        status = resp.status_code
        if not feed.entries:
            print(f"  No entries (HTTP {status})")
            return positions

        for entry in feed.entries:
            title = entry.get("title", "").strip()
            raw = entry.get("summary", "")
            if not raw and hasattr(entry, "content"):
                raw = entry.content[0].get("value", "")
            if raw and len(raw) < 300 and "/" in raw and not raw.strip().startswith("<"):
                raw = ""
            description = BeautifulSoup(raw, "html.parser").get_text(separator=" ").strip()
            link = entry.get("link", "")

            if not is_phd_related(title, description):
                continue

            pub_date = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    pub_date = datetime(*entry.published_parsed[:6]).strftime("%Y-%m-%d")
                except Exception:
                    pass

            positions.append({
                "id": make_id(link, title),
                "title": title,
                "institution": extract_institution(entry),
                "location": entry.get("location", ""),
                "region": source["region"],
                "deadline": extract_deadline(description),
                "skills": extract_skills(title + " " + description),
                "professor": extract_professor(description),
                "link": link,
                "description": description[:600],
                "source": source["name"],
                "posted_date": pub_date,
                "scraped_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            })
    except requests.exceptions.Timeout:
        print(f"  Timeout after {FETCH_TIMEOUT}s")
    except Exception as e:
        print(f"  Error: {e}")
    return positions


def main():
    sources = load_sources()
    all_positions: list = []
    seen_ids: set = set()

    for source in sources:
        print(f"Scraping {source['name']}...")
        positions = scrape_rss(source) if source["type"] == "rss" else []
        new = [p for p in positions if p["id"] not in seen_ids]
        for p in new:
            seen_ids.add(p["id"])
            all_positions.append(p)
        print(f"  +{len(new)} PhD positions")

    # Merge manual positions (skip duplicates by id or link)
    manual = load_manual_positions()
    manual_new = 0
    for p in manual:
        pid = p.get("id") or make_id(p.get("link", ""), p.get("title", ""))
        p.setdefault("id", pid)
        p.setdefault("source", "Manual")
        p.setdefault("scraped_date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        if pid not in seen_ids:
            seen_ids.add(pid)
            all_positions.append(p)
            manual_new += 1
    if manual:
        print(f"\nManual positions: +{manual_new} (of {len(manual)} in bank)")

    def sort_key(p):
        return (0, p["deadline"]) if p["deadline"] else (1, p.get("posted_date") or "")

    all_positions.sort(key=sort_key)

    out_path = REPO_ROOT / "data" / "positions.json"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps({
        "updated": datetime.now(timezone.utc).isoformat(),
        "count": len(all_positions),
        "positions": all_positions,
    }, indent=2))
    print(f"\nTotal: {len(all_positions)} positions → {out_path}")


if __name__ == "__main__":
    main()
