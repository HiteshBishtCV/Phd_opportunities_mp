# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## MedPhys PhD Job Board

Static site hosted on GitHub Pages. Scraper runs via GitHub Actions daily.

## Architecture

- `index.html` — the entire frontend (one file, no build step)
- `scraper/scrape.py` — Python scraper pulling from RSS feeds
- `data/positions.json` — scraped data read by the frontend
- `.github/workflows/update.yml` — GitHub Actions schedule

## Common Tasks

- Edit UI/styles → `index.html`
- Add a new job source → `scraper/scrape.py`, add to `SOURCES` list
- Change scrape frequency → `.github/workflows/update.yml`, edit cron
- Test scraper locally → `cd scraper && python scrape.py`
