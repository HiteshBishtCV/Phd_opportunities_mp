# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## MedPhys PhD Board

Static site hosted on GitHub Pages. A Python scraper runs daily via GitHub Actions and writes to `data/positions.json`, which the frontend reads at load time — no build step, no backend.

## Architecture

```
index.html                    ← entire frontend (vanilla JS, no framework)
data/positions.json           ← merged scraper + manual output; read by index.html
data/manual_positions.json    ← hand-curated positions added by the user
scraper/scrape.py             ← pulls active RSS feeds, merges manual_positions.json
scraper/sources.json          ← bank of all sources (active + inactive + to-try)
scraper/requirements.txt
.github/workflows/update.yml  ← daily cron + manual trigger
.nojekyll                     ← disables Jekyll so GitHub Pages serves files as-is
```

## Common tasks

- **Edit UI/styles** → `index.html`
- **Add a new RSS source** → `scraper/sources.json`, add an entry with `"active": true`
- **Disable a broken source** → `scraper/sources.json`, set `"active": false` (keeps it in the bank)
- **Add a position manually** → `data/manual_positions.json`, add to the `"positions"` array
- **Add a new skill keyword** → `scraper/scrape.py`, add to `SKILLS_KEYWORDS`
- **Change scrape frequency** → `.github/workflows/update.yml`, edit `cron`
- **Test scraper locally** → `cd scraper && python scrape.py`
- **Trigger scraper manually** → GitHub → Actions → "Update PhD Positions" → Run workflow

## Source bank (`scraper/sources.json`)

Each entry has:
- `name` — display name
- `type` — `"rss"` (only type currently supported)
- `url` — feed URL
- `region` — `"USA"` / `"Europe"` / `"International"`
- `active` — `true` = scraped daily; `false` = kept as reference, skipped
- `notes` — why a source is inactive, last-checked status, etc.

Active sources are loaded at runtime. Inactive sources stay in the bank so they can be re-enabled when URLs are fixed or sites start returning data.

**Note:** As of 2026, most academic job board RSS feeds are dead or Cloudflare-blocked.
Active sources are tried daily; results depend on what each site exposes at scrape time.

## Manual positions (`data/manual_positions.json`)

Add any position you find by browsing. Required fields: `title`, `link`.
Optional: `institution`, `location`, `region`, `deadline` (YYYY-MM-DD), `description`, `professor`, `skills`, `posted_date`.
The scraper merges these into `positions.json` on every run.

## Scraper logic

1. Loads active sources from `sources.json`
2. For each RSS source: fetches with Firefox User-Agent, filters entries with `is_phd_related()` (must match a PhD term AND a medical physics term)
3. Extracts deadline, skills, professor via regex on description text
4. Deduplicates by `md5(url + title)`
5. Merges `data/manual_positions.json`
6. Sorts: known deadlines first (ascending), then by posted date

## GitHub Pages setup (one-time)

Repo Settings → Pages → Source: **Deploy from branch** → branch `main`, folder `/` (root).
