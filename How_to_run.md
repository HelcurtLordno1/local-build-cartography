# How to run Bản Đồ Tin locally

This guide is written as a terminal checklist. Run the commands in order from the project root unless a step says otherwise.

The project is a local FastAPI prototype. It serves a static browser UI, stores data in SQLite, loads demo seed data, and can optionally fetch current RSS news from Vietnamese news sources.

## What you need before starting

- Python 3.11 or newer.
- A terminal such as WSL Ubuntu, Linux terminal, macOS Terminal, or Git Bash.
- Internet access only if you need to install dependencies or fetch live news.

You do not need Node.js, Docker, PostgreSQL, Redis, or a separate frontend server for the current prototype.

## Stage 1: Open the project folder

Run this command first:

```bash
cd /mnt/d/Desktop_informations/Competitions_2026/CIVIC_INTELLIGENCE_CARTOGRAPHY
```

Check that you are in the correct folder:

```bash
pwd
```

Expected result:

```text
/mnt/d/Desktop_informations/Competitions_2026/CIVIC_INTELLIGENCE_CARTOGRAPHY
```

You can also check that the important files exist:

```bash
ls
```

You should see files and folders such as:

```text
app  scripts  tests  requirements.txt  How_to_run.md
```

After this stage, you can run every command below directly from this folder.

## Stage 2: Check Python

Run:

```bash
python3 --version
```

Expected result: Python 3.11 or newer.

Example from this workspace:

```text
Python 3.12.3
```

If `python3` is not found, try:

```bash
python --version
```

If that works and shows Python 3.11 or newer, use `python` instead of `python3` in the virtual environment creation command in the next stage.

## Stage 3: Create the virtual environment

Only run this command if `.venv` does not already exist:

```bash
python3 -m venv .venv
```

If `.venv` already exists, skip that command.

Now activate the virtual environment:

```bash
source .venv/bin/activate
```

After activation, your terminal prompt usually starts with:

```text
(.venv)
```

Check that the virtual environment Python is being used:

```bash
which python
```

Expected result:

```text
/mnt/d/Desktop_informations/Competitions_2026/CIVIC_INTELLIGENCE_CARTOGRAPHY/.venv/bin/python
```

From this stage onward, you can use either `python ...` after activating `.venv`, or `.venv/bin/python ...` without activating it.

## Stage 4: Install dependencies

Run this after the virtual environment exists:

```bash
pip install -r requirements.txt
```

If you did not activate `.venv`, run this instead:

```bash
.venv/bin/python -m pip install -r requirements.txt
```

This installs:

- `fastapi` for the backend API.
- `uvicorn` for the local web server.
- `pydantic` for validation.
- `httpx`, `feedparser`, and `beautifulsoup4` for live news ingestion.
- `pytest` for tests.

You only need to repeat this stage when dependencies change, `.venv` is deleted, or you are setting up the project on a new machine.

## Stage 5: Seed the local SQLite database

Run this after dependencies are installed:

```bash
python scripts/seed_demo.py
```

If `.venv` is not activated, run:

```bash
.venv/bin/python scripts/seed_demo.py
```

Expected result:

```text
Seeded Bản Đồ Tin demo data.
```

This creates or updates:

```text
app/data/ban_do_tin.db
```

The app can run without live internet data because this seed command loads local demo events from:

```text
app/data/demo_seed.json
```

After this stage, you can run the web app immediately.

## Stage 6: Run tests before starting the app

Run:

```bash
python -m pytest -q
```

If `.venv` is not activated, run:

```bash
.venv/bin/python -m pytest -q
```

Verified result in this workspace:

```text
7 passed
```

If tests pass, the core pipeline and API behavior are working.

## Stage 7: Start the web server

Run this command and leave it running:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If `.venv` is not activated, run:

```bash
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Expected startup output includes:

```text
Uvicorn running on http://127.0.0.1:8000
Application startup complete.
```

At this stage, the project is running.

Open this URL in your browser:

```text
http://127.0.0.1:8000
```

Important: keep this terminal open. If you close it or press `CTRL+C`, the server stops.

## Stage 8: Verify the running app from a second terminal

Open a second terminal, then go to the project folder again:

```bash
cd /mnt/d/Desktop_informations/Competitions_2026/CIVIC_INTELLIGENCE_CARTOGRAPHY
```

Check the health endpoint:

```bash
curl http://127.0.0.1:8000/health
```

Expected result:

```json
{"status":"ok","service":"Bản Đồ Tin"}
```

Check that the homepage responds:

```bash
curl -I http://127.0.0.1:8000/
```

Expected result includes:

```text
HTTP/1.1 200 OK
```

Check that event data is available:

```bash
curl http://127.0.0.1:8000/api/events
```

Expected result: a JSON list of event objects. The output is long. If you only want to check that events exist, use:

```bash
curl -s http://127.0.0.1:8000/api/events | python -m json.tool | head
```

If you see JSON event data, the backend and database are working.

## Stage 9: Use the app

With the server still running, open:

```text
http://127.0.0.1:8000
```

The browser UI loads from:

```text
app/static/index.html
app/static/app.js
app/static/styles.css
```

The UI talks to the FastAPI backend in:

```text
app/main.py
```

Main useful endpoints:

```text
GET  /health
GET  /api/events
GET  /api/events/{event_id}
GET  /api/news/sources
POST /api/ingest/live-news?source=vnexpress&limit=10
POST /api/ingest/live-news?source=all&limit=8
POST /api/ingest/multi-modal
GET  /api/debate/consensus/{event_id}
POST /api/action/generate/{event_id}
GET  /api/archaeology/drill/{event_id}
WS   /terrain/stream
```

## Stage 10: Optional, fetch live RSS news

Only run this after:

1. Dependencies are installed.
2. The database has been seeded at least once.
3. You have internet access.

Fast RSS-only check:

```bash
python scripts/fetch_live_news.py --source vnexpress --limit 1 --rss-only
```

If `.venv` is not activated:

```bash
.venv/bin/python scripts/fetch_live_news.py --source vnexpress --limit 1 --rss-only
```

Verified result in this workspace: the command successfully ingested one current VnExpress RSS item.

Fetch more from VnExpress:

```bash
python scripts/fetch_live_news.py --source vnexpress --limit 10
```

Fetch from Tuoi Tre:

```bash
python scripts/fetch_live_news.py --source tuoitre --limit 10
```

Use `--rss-only` when you want a faster command that does not fetch each article page:

```bash
python scripts/fetch_live_news.py --source vnexpress --limit 10 --rss-only
```

After live ingestion, refresh:

```text
http://127.0.0.1:8000
```

or check:

```bash
curl http://127.0.0.1:8000/api/events
```

## Stage 11: Optional, ingest live news through the running API

This requires the server from Stage 7 to still be running.

In a second terminal, run:

```bash
curl -X POST "http://127.0.0.1:8000/api/ingest/live-news?source=vnexpress&limit=3&fetch_full_text=false"
```

Fetch all configured sources with a small limit per source:

```bash
curl -X POST "http://127.0.0.1:8000/api/ingest/live-news?source=all&limit=2&fetch_full_text=false"
```

List available source keys:

```bash
curl http://127.0.0.1:8000/api/news/sources
```

Known source keys include:

```text
vnexpress
tuoitre
dantri_com_vn
nhandan_vn
vietnamnet_vn
thanhnien_vn
baochinhphu_vn
```

Use `fetch_full_text=false` for quick demos. Use `fetch_full_text=true` when you want the app to fetch article pages and extract more text.

## Stage 12: Stop the server

Go back to the terminal where `uvicorn` is running.

Press:

```text
CTRL+C
```

The local site at `http://127.0.0.1:8000` will stop responding after the server exits.

## Stage 13: Run the project again later

If the project was already set up before, the short run path is:

```bash
cd /mnt/d/Desktop_informations/Competitions_2026/CIVIC_INTELLIGENCE_CARTOGRAPHY
source .venv/bin/activate
python scripts/seed_demo.py
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Then open:

```text
http://127.0.0.1:8000
```

If you do not want to activate `.venv`, use:

```bash
cd /mnt/d/Desktop_informations/Competitions_2026/CIVIC_INTELLIGENCE_CARTOGRAPHY
.venv/bin/python scripts/seed_demo.py
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Troubleshooting

### `uvicorn: command not found`

The virtual environment is probably not activated.

Run:

```bash
source .venv/bin/activate
```

Then run the server again:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Or bypass activation:

```bash
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### `ModuleNotFoundError`

Install dependencies again:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

Then retry the command that failed.

### Port 8000 is already in use

Run the server on another port:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Then open:

```text
http://127.0.0.1:8001
```

### The browser opens but no events appear

Seed the database:

```bash
python scripts/seed_demo.py
```

Then refresh the browser.

### Live news fetch fails

First verify the local app works with seed data. Live news requires internet access and depends on external RSS websites being reachable.

Use RSS-only mode for a faster check:

```bash
python scripts/fetch_live_news.py --source vnexpress --limit 1 --rss-only
```

### Reset local data

Only do this when you intentionally want to delete locally ingested events and rebuild from the demo seed.

Stop the server first with `CTRL+C`, then run:

```bash
rm app/data/ban_do_tin.db
python scripts/seed_demo.py
```

Then start the server again:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Commands verified in this workspace

These commands were run successfully from:

```text
/mnt/d/Desktop_informations/Competitions_2026/CIVIC_INTELLIGENCE_CARTOGRAPHY
```

Verified setup:

```text
.venv/bin/python --version
.venv/bin/python scripts/seed_demo.py
.venv/bin/python -m pytest -q
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
curl -I http://127.0.0.1:8000/
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/events
.venv/bin/python scripts/fetch_live_news.py --source vnexpress --limit 1 --rss-only
```

Verified results:

```text
Python 3.12.3
Seeded Bản Đồ Tin demo data.
7 passed
Uvicorn running on http://127.0.0.1:8000
HTTP/1.1 200 OK
{"status":"ok","service":"Bản Đồ Tin"}
Live RSS command ingested 1 VnExpress event.
```
