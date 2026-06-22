# Bản Đồ Tin — Civic Intelligence Cartography

Bản Đồ Tin ("News Map") is a runnable civic-news intelligence prototype for Vietnam-focused public information. It turns publisher RSS items, article URLs, and pasted source text into an interactive event terrain — with source links, conservative confidence scoring, citizen action guidance, an audit trail, and original-source preservation.

This is not a concept document. It is a working **FastAPI + SQLite + browser UI** application: it seeds demo data, fetches live RSS news from real Vietnamese publishers, extracts article text, clusters related reports, scores confidence conservatively, generates civic action cards, and shows exactly where every item came from.

> Live RSS ingestion was verified against VnExpress on **2026-06-21** (see `How_get_data.md`).

---

## What The App Does Now

- Serves a browser UI at `http://127.0.0.1:8000` with a rotating 3D-style news terrain on an HTML canvas.
- Stores all data locally in SQLite at `app/data/ban_do_tin.db`.
- Loads repeatable demo records from `app/data/demo_seed.json` (works fully offline).
- Fetches **live** Vietnamese publisher RSS feeds and parses real entries (title, URL, GUID, publish time).
- Optionally opens each article page and extracts readable HTML body text with BeautifulSoup.
- Accepts quick ingest from a direct article URL or pasted source text (OCR/transcripts accepted as normalized text).
- Groups similar articles into civic event clusters by title-token similarity.
- Assigns category, severity, confidence state, and a 10–98 consensus score.
- Builds a detailed multi-section news summary (executive summary, key takeaways, per-story breakdown, sentiment).
- Generates a **v2 citizen action card (GCAP)**: extracts real action/verification sentences from the article text, falls back to curated per-category defaults, and routes users to the correct official source for each category.
- Produces a debate trace (agreed facts, disputed points, agent roles) and archaeology layers (current context, precedent, legal framework, risk simulation).
- Shows original source URLs, source names, timestamps, extraction confidence, and provenance markers in every event.
- Provides read/unread tracking and soft delete from the UI.
- Streams terrain refreshes through `WS /terrain/stream` and auto-refreshes on a 30s interval.

Architecture notes in `architecture/` describe larger production targets such as OCR, audio extraction, Celery/Redis workers, PostgreSQL/pgvector, object storage, and LLM-based adversarial agents. Those are **roadmap items**, not required services for the current local prototype.

---

## How A News Item Is Processed

This is the pipeline every ingested item runs through (`app/services/news_ingestion.py` and `app/services/pipeline.py`):

1. **Ingest** — read the RSS feed (or a pasted URL/text), preserving the publisher name, feed URL, article URL, RSS GUID, publish timestamp, and retrieval timestamp.
2. **Extract** — optionally fetch the article HTML and pull the readable body; record extraction confidence and any fetch error.
3. **Classify** — assign a civic category (weather, traffic, legal, policy, business, health, education, tech, etc.) using deterministic Vietnamese keyword rules.
4. **Locate** — detect a city hint (Hà Nội, TP.HCM, Đà Nẵng, …) when present; otherwise default to Vietnam scope.
5. **Cluster** — match against recent events in the same category by title-token similarity (Jaccard, threshold 0.45); corroboration raises the score.
6. **Score** — compute a conservative consensus score from source count, extraction confidence, official-source presence, and disputed state.
7. **Summarize** — generate an executive summary, key takeaways, per-story details, and inferred sentiment.
8. **Debate** — separate agreed facts from disputed points, with a media/policy/skeptic agent trace.
9. **Action (GCAP v2)** — extract citizen-facing immediate actions and verification steps directly from the text, fall back to curated category defaults, and point at the right official channel.
10. **Archaeology** — add current context, precedent prompts, legal-framework prompts, and a 24h risk simulation.
11. **Persist** — store source, article, event, debate, action protocol, and archaeology as auditable records.

---

## How Users Use It

1. Start the server and open `http://127.0.0.1:8000`.
2. Use the left panel to filter by date, section, source, read state, severity, confidence, or search text.
3. The center canvas shows news as a rotating civic terrain:
   - click a **section ball** to enter that category,
   - click a **titled news neuron** to open the event,
   - drag or throw the graph to rotate it.
4. The right panel shows four tabs:
   - **Consensus** — agreed facts, disputed points, and agent trace,
   - **Action** — immediate actions, verification steps, and community-sharing guidance,
   - **Archaeology** — current context, precedent, legal framework, and risk simulation,
   - **Sources** — original article links, source names, timestamps, extracted text, and extraction confidence.
5. Use **Live Sources** to fetch current news from configured RSS feeds.
6. Use **Quick Ingest** to submit your own article URL or pasted source text.
7. Use **Mark read** and **Delete** to manage the local event list.

On startup the browser UI loads configured live sources and attempts a live fetch for all of them. If internet access is unavailable, the seeded demo data still works.

---

## News Sources & Credibility

The app separates **demo data** (offline, hand-built) from **live data** (real publisher RSS). It never invents titles, URLs, dates, or source names. Every live item links back to the original publisher page.

### Why these sources are credible and reliable

The live sources are the highest-traffic, most authoritative mainstream Vietnamese news portals — major licensed electronic newspapers, the official government newspaper, the national news agency, the Party central organ, and national television. Each carries a `credibility_base_score` used by the consensus engine; **official / government-style sources are weighted higher** and can lift an event toward `verified`, while a single social screenshot is treated as unverified.

The full source list with categorization and strategy notes lives in `data/websites_scrape.md`.

### Built-in live sources (fetched by default)

Defined in `app/services/news_ingestion.py`:

| Key | Publisher | Website | RSS feed | Credibility |
| --- | --- | --- | --- | --- |
| `vnexpress` | VnExpress — the most-read online-only newspaper in Vietnam | https://vnexpress.net | https://vnexpress.net/rss/tin-moi-nhat.rss | 0.82 |
| `tuoitre` | Tuổi Trẻ Online — major breaking-news publisher | https://tuoitre.vn | https://tuoitre.vn/rss/tin-moi-nhat.rss | 0.80 |

### Additional sources (enabled via `data/websites_scrape.md`)

The ingestion service also knows the RSS feeds for these domains. When a domain is listed in `websites_scrape.md`, it becomes available in the UI's **Live Sources** dropdown and through `POST /api/ingest/live-news?source=<key>`. Sources without a known feed URL are auto-discovered from the site's HTML or common feed paths.

**General & Breaking News (the Big 4):**

| Publisher | Website | Known RSS feed |
| --- | --- | --- |
| Dân Trí | https://dantri.com.vn | https://dantri.com.vn/rss/home.rss |
| Thanh Niên | https://thanhnien.vn | https://thanhnien.vn/rss/home.rss |

**Business, Finance & Economics:**

| Publisher | Website | Known RSS feed |
| --- | --- | --- |
| CafeF | https://cafef.vn | https://cafef.vn/thi-truong-chung-khoan.rss |
| VietNamNet | https://vietnamnet.vn | https://vietnamnet.vn/rss/tin-moi-nhat.rss |
| VnEconomy (Vietnam Economic Times) | https://vneconomy.vn | https://vneconomy.vn/rss/tin-moi.rss |
| Báo Đầu tư | https://baodautu.vn | https://baodautu.vn/rss/home.rss |

**Official State & National Media** (highest credibility tier — government / national agency):

| Publisher | Website | Known RSS feed |
| --- | --- | --- |
| Báo Chính phủ (Government of the SRV) | https://baochinhphu.vn | https://baochinhphu.vn/rss/trang-chu.rss |
| VietnamPlus (Vietnam News Agency) | https://www.vietnamplus.vn | https://www.vietnamplus.vn/rss/home.rss |
| Nhân Dân (Party central organ) | https://nhandan.vn | https://nhandan.vn/rss/home.rss |
| VTV Online (Vietnam Television) | https://vtv.vn | https://vtv.vn/trang-chu.rss |

**Tech, Youth & Entertainment:**

| Publisher | Website | Known RSS feed |
| --- | --- | --- |
| Kênh 14 | https://kenh14.vn | https://kenh14.vn/home.rss |
| Znews | https://znews.vn | https://znews.vn/rss.html |
| Soha News | https://soha.vn | https://soha.vn/rss.htm |

> **Strategy note:** the app prefers structured RSS feeds over HTML scraping, because RSS avoids rate limits and Cloudflare blocks and gives clean, minute-by-minute updates. Aggregators such as Báo Mới (`baomoi.com`) are deliberately avoided — scraping an aggregator causes deduplication headaches, so the app goes straight to the primary publishers listed above.

### Demo seed data

`app/data/demo_seed.json` contains hand-built records for offline judging and repeatable UI testing. Some demo records use placeholder URLs such as `example.local`; those are **not** live publisher pages and should be treated as curated sample data, not real-time news.

---

## Why The Information Is Auditable

For every live RSS item, the app preserves:

- publisher / source name,
- source website,
- feed URL,
- article URL,
- RSS entry id or GUID,
- RSS publish / update timestamp,
- local retrieval timestamp,
- feed HTTP status,
- article fetch error if full-text extraction fails,
- provenance marker such as `publisher_rss`, `publisher_rss_and_article_html`, or `direct_url_article_html`.

The app does not claim that a single RSS item is verified truth. RSS proves that a publisher posted an item; it does not independently verify every claim inside that article. For this reason, confidence scoring is intentionally conservative, especially for single-source items or screenshot-style submissions.

---

## Confidence And Event Logic

Each event receives a `consensus_score` from 10 to 98 and one readable state:

| Score | State |
| --- | --- |
| 80+ | `verified` |
| 70–79 | `high_confidence` |
| 50–69 | `developing` |
| 30–49 | `disputed` |
| below 30 | `unverified` |

The current prototype uses deterministic rules. It considers source count, extraction confidence, official/government-style source presence, and whether the input is disputed or weakly evidenced. A single disputed screenshot is capped at `disputed` (≤49). Similar reports in the same category are clustered by title-token similarity, and corroboration raises the score.

---

## Run Locally

Requirements:

- Python 3.11 or newer.
- Internet access for dependency installation and live RSS fetching.
- No Node.js, Docker, Redis, PostgreSQL, or separate frontend server is required.

Fastest run (assuming setup is mostly done):

```bash
cd /mnt/d/Desktop_informations/Competitions_2026/CIVIC_INTELLIGENCE_CARTOGRAPHY
.venv/bin/python scripts/seed_demo.py
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

First-time setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/seed_demo.py
python -m pytest -q          # 7 tests should pass
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok","service":"Bản Đồ Tin"}
```

Detailed step-by-step setup is in `How_to_run.md`; a copy-paste fast-run guide is in `SETUP_done_fast_run_whole.md`.

---

## Fetch Live News

Fetch VnExpress RSS only (fast, no article HTML):

```bash
source .venv/bin/activate
python scripts/fetch_live_news.py --source vnexpress --limit 2 --rss-only
```

Fetch RSS **and** article HTML (full-text extraction):

```bash
python scripts/fetch_live_news.py --source vnexpress --limit 1
```

Use the API while the server is running:

```bash
# One source
curl -X POST "http://127.0.0.1:8000/api/ingest/live-news?source=vnexpress&limit=5&fetch_full_text=true"

# All configured sources
curl -X POST "http://127.0.0.1:8000/api/ingest/live-news?source=all&limit=5&fetch_full_text=false"

# List configured sources
curl http://127.0.0.1:8000/api/news/sources
```

> The `scripts/fetch_live_news.py` CLI accepts the built-in keys `vnexpress` and `tuoitre`. To fetch from the additional sources above, use the running API with `source=<key>` or `source=all` — the API loads every domain listed in `data/websites_scrape.md`.

More data-source details are in `How_get_data.md`.

---

## Local AI Enrichment

The AI Analysis tab uses a local Ollama server by default:

```bash
ollama pull qwen3.5:9b
OLLAMA_HOST=0.0.0.0:11434 ollama serve
```

When the API runs inside WSL and Ollama runs on the Windows host, the app
automatically resolves WSL's default gateway and uses
`http://<gateway-ip>:11434`. Outside WSL it defaults to
`http://127.0.0.1:11434`.

Then open:

```bash
curl http://127.0.0.1:8000/api/llm/status
```

If `ready` is `true`, event deep dives will call Ollama and cache the result in SQLite. If Ollama is not installed, not running, or missing the configured model, the app keeps working and shows deterministic civic analysis with a setup hint instead of a raw connection error.

Useful environment overrides:

```bash
LLM_ENABLED=false .venv/bin/uvicorn app.main:app --reload
LLM_MODEL=qwen3.5:9b .venv/bin/uvicorn app.main:app --reload
LLM_BASE_URL=http://127.0.0.1:11434 .venv/bin/uvicorn app.main:app --reload
OLLAMA_BASE_URL=http://127.0.0.1:11434 .venv/bin/uvicorn app.main:app --reload
```

LLM responses are tagged with the selected event id, source title, source article ids, and model name before being cached. If a cached response was generated for another model/event, or the model returns analysis that does not match the selected event, the backend rejects it and falls back to deterministic analysis instead of showing unrelated news.

---

## API Surface

- `GET /` — browser UI.
- `GET /health` — service health check.
- `GET /api/llm/status` — inspect local Ollama readiness, configured model, and setup hints.
- `GET /api/events` — list terrain-ready events.
- `GET /api/events?date_range=today|week|month|year|all|recent` — filter by date window.
- `GET /api/events?start_date=2026-06-10&end_date=2026-06-21` — filter by article dates.
- `GET /api/events?category=thoi-tiet&read_state=unread&q=mua` — filter by category, read state, and query.
- `GET /api/events/{event_id}` — event, articles, debate, action protocol, and archaeology.
- `GET /api/events/{event_id}/llm-deepdive` — lazily generate or read cached AI civic analysis for one event; falls back to deterministic analysis if the local LLM is disabled or unavailable.
- `PATCH /api/events/{event_id}/read?is_read=true` — mark an event read or unread.
- `DELETE /api/events/{event_id}` — soft-delete an event.
- `POST /api/ingest/multi-modal` — ingest normalized article/source text or URL.
- `POST /api/ingest/live-news` — fetch publisher RSS and ingest results.
- `GET /api/news/sources` — list configured news sources.
- `GET /api/debate/consensus/{event_id}` — inspect consensus / debate trace.
- `POST /api/action/generate/{event_id}` — generate or refresh action card.
- `GET /api/archaeology/drill/{event_id}` — inspect archaeology layers.
- `WS /terrain/stream` — stream terrain snapshots every 8 seconds.

---

## Project Structure

```text
CIVIC_INTELLIGENCE_CARTOGRAPHY/
├── README.md
├── How_get_data.md            # how demo vs live data works (incl. 2026-06-21 verification)
├── How_to_run.md              # full step-by-step setup
├── SETUP_done_fast_run_whole.md  # copy-paste fast-run guide
├── requirements.txt
├── pyproject.toml
├── app/
│   ├── main.py                # FastAPI routes + startup
│   ├── api/schemas.py         # request/response models
│   ├── core/                  # config + SQLite database
│   ├── data/                  # ban_do_tin.db + demo_seed.json
│   ├── services/
│   │   ├── news_ingestion.py  # RSS loading, parsing, date filter, article extraction, feed discovery
│   │   ├── pipeline.py        # ingest, cluster, score, summary, debate, action (GCAP v2), archaeology
│   │   ├── llm_enrichment.py  # lazy Ollama deep-dive + deterministic fallback
│   │   └── repository.py      # SQLite persistence + event queries
│   └── static/                # browser UI (index.html, app.js, styles.css)
├── scripts/
│   ├── seed_demo.py
│   └── fetch_live_news.py
├── tests/test_pipeline.py     # 7 core behavior tests
├── architecture/              # production-target design docs (roadmap)
├── data/
│   ├── websites_scrape.md     # credible source list with categorization + strategy
│   └── *.md                   # data model, taxonomy, demo plan
├── prompts/                   # AI agent prompts + structured output schemas
└── references/                # third-party news-aggregator reference repos
```

Key implementation files:

- `app/main.py` — FastAPI routes and startup.
- `app/static/` — browser UI: filters, live-fetch controls, terrain graph, and detail tabs.
- `app/services/news_ingestion.py` — RSS source loading, RSS parsing, date filtering, article HTML extraction, and feed discovery.
- `app/services/pipeline.py` — article ingest, URL extraction, clustering, scoring, summary, debate, action cards (GCAP v2), and archaeology.
- `app/services/llm_enrichment.py` — lazy local-Ollama event analysis with a deterministic fallback and cached results.
- `app/services/repository.py` — SQLite persistence and event queries.
- `tests/test_pipeline.py` — core behavior tests.

---

## Current Limitations

- Live source availability depends on publisher RSS feeds and website access.
- Article full-text extraction is best-effort and can break when publisher HTML changes.
- Category detection is keyword-based.
- Location detection uses simple Vietnamese city hints, not full geocoding.
- Event clustering uses title-token similarity, not embeddings yet.
- Background scheduled ingestion is not enabled; live fetch is triggered by the UI, script, or API.
- PDF, screenshot, and audio labels are accepted only as already-normalized text; local OCR, PDF parsing, and speech-to-text are roadmap items.
- The deterministic debate trace is an explainability scaffold, not a full LLM adjudication engine.

---

## Responsible Use

Bản Đồ Tin is a civic news-awareness and triage tool. It preserves provenance, surfaces uncertainty, and encourages users to inspect original publisher links and official channels before making safety, legal, financial, medical, or emergency decisions.

The project becomes more reliable by being transparent about uncertainty, not by hiding it.
