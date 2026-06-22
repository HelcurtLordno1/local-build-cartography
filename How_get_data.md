# How this project gets data

## Short answer

The project now supports both:

1. Offline demo data from `app/data/demo_seed.json`.
2. Real current internet news from publisher RSS feeds through `scripts/fetch_live_news.py` and `POST /api/ingest/live-news`.

Before this upgrade, the runnable app only loaded curated demo records and accepted manual article submissions. It did not independently fetch real-time internet news. That meant the demo was useful for showing the product concept, but it should not be described as live-data ingestion.

## What is demo data

`app/data/demo_seed.json` contains hand-built prototype records. These records show the intended data model:

- event title and summary,
- source list,
- article text,
- consensus score,
- disputed points,
- civic action protocol,
- archaeology layers.

Some URLs in the demo seed use `example.local`. Those are placeholders, not real publisher pages. Use demo seed data for offline judging, UI testing, and repeatable tests. Do not claim it is a real-time dataset.

## What is real live data

Live news ingestion is implemented in:

- `app/services/news_ingestion.py`
- `scripts/fetch_live_news.py`
- `POST /api/ingest/live-news`

Supported built-in RSS sources:

- `vnexpress`: `https://vnexpress.net/rss/tin-moi-nhat.rss`
- `tuoitre`: `https://tuoitre.vn/rss/tin-moi-nhat.rss`

The ingestion flow is:

1. Fetch the publisher RSS feed with `httpx`.
2. Parse entries with `feedparser`.
3. Preserve real publisher title, URL, RSS entry id, publish timestamp, feed URL, and retrieval timestamp.
4. Classify category using deterministic Vietnamese keyword rules.
5. Detect a basic location hint when the article title/summary mentions known Vietnamese cities.
6. Optionally fetch each article URL and extract readable article text with `BeautifulSoup`.
7. Store the result in SQLite as a source, article, event, debate trace, and archaeology layer.

The system does not invent article titles, URLs, dates, or source names. If an article page cannot be fetched, the record falls back to the RSS title/summary and stores the fetch error in metadata.

## How to prove data is real

Run:

```bash
source .venv/bin/activate
python scripts/fetch_live_news.py --source vnexpress --limit 2 --rss-only
```

Expected output is JSON containing:

- `source`
- `feed_url`
- `fetched_at`
- `ingested_count`
- `events`
- each event's real `canonical_title`
- each event's `sources` array with an article id

For full article extraction, run:

```bash
python scripts/fetch_live_news.py --source vnexpress --limit 1
```

This fetches RSS first, then fetches the linked article HTML and stores the extracted article body when available.

## Verification performed on 2026-06-21

The live RSS command was run against VnExpress and succeeded:

```text
source: VnExpress
feed_url: https://vnexpress.net/rss/tin-moi-nhat.rss
fetched_at: 2026-06-21T07:02:29.972304+00:00
requested_limit: 2
ingested_count: 2
```

Example real titles returned by the feed at that time:

- `Mì ăn liền - món ăn cả thế giới đều mê`
- `Dùng cẩu 200 tấn trục vớt xe container dưới vực đèo Bảo Lộc`

The full-text extraction command also succeeded for one VnExpress article at:

```text
fetched_at: 2026-06-21T07:02:44.700937+00:00
ingested_count: 1
```

## Why consensus stays conservative

A single RSS article is real source data, but it is not automatically verified truth. The current prototype gives single-source RSS events a developing confidence state unless stronger corroboration exists.

This is intentional:

- RSS proves the publisher posted an item.
- RSS does not prove every claim in the item is independently confirmed.
- Civic action cards are generated only when the consensus score is above the confidence threshold.

For stronger real-world reliability, the next upgrade should cluster multiple publishers and official government feeds for the same event before marking it verified.

## Current limitations

- RSS feeds can change or block requests.
- Article HTML extraction is best-effort and depends on publisher page structure.
- Location detection is heuristic, not geocoding.
- Category detection is keyword-based.
- The app does not yet run scheduled background jobs; live fetch is triggered manually by script or API call.
- The app stores current data locally in SQLite, not a production database.

## Real-world upgrade path

To make the project stronger for production:

1. Add more Vietnamese publisher feeds and official government feeds.
2. Add event clustering across multiple sources by title similarity, time, location, and entities.
3. Add source-specific extractors for publishers whose HTML layout needs special handling.
4. Add scheduled ingestion with Celery/Redis or a cron job.
5. Add geocoding for Vietnamese provinces/districts.
6. Store raw fetched RSS and HTML artifacts for auditability.
7. Add a source review UI so users can inspect original URLs before trusting summaries.

## Data ethics note

This project should show source URLs and confidence state clearly. It should not present a single scraped article or social screenshot as verified civic truth. The current implementation preserves provenance metadata and keeps confidence conservative to reduce hallucination and misinformation risk.
