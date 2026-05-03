# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## MedPhys PhD Board

Static site hosted on GitHub Pages. A Python scraper runs daily via GitHub Actions and writes to `data/positions.json`, which the frontend reads at load time — no build step, no backend.

## Architecture

```
index.html              ← entire frontend (vanilla JS, no framework)
data/positions.json     ← scraped data; read by index.html via fetch()
scraper/scrape.py       ← pulls from RSS feeds, writes positions.json
scraper/requirements.txt
.github/workflows/update.yml  ← daily cron + manual trigger
.nojekyll               ← disables Jekyll so GitHub Pages serves files as-is
```

## Common tasks

- **Edit UI/styles** → `index.html`
- **Add a new job source** → `scraper/scrape.py`, add an entry to `SOURCES`
- **Add a new skill keyword** → `scraper/scrape.py`, add to `SKILLS_KEYWORDS`
- **Change scrape frequency** → `.github/workflows/update.yml`, edit `cron`
- **Test scraper locally** → `cd scraper && python scrape.py`
- **Trigger scraper manually** → GitHub → Actions → "Update PhD Positions" → Run workflow

## Scraper logic

Each source in `SOURCES` is an RSS feed. For each entry the scraper:
1. Filters with `is_phd_related()` — must match both a PhD term and a medical physics term
2. Extracts deadline, skills, professor via regex on the description text
3. Deduplicates by `md5(url + title)`

Results are sorted: known deadlines first (ascending), then unknown.

## GitHub Pages setup (one-time)

Repo Settings → Pages → Source: **Deploy from branch** → branch `main`, folder `/` (root).
