# Fast run whole project

This file is for the case where setup is already mostly done and you do not want to read the full guide.

Project URL after running:

```text
http://127.0.0.1:8000
```

## Fastest run

Paste this in terminal:

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

Keep the terminal open. Press `CTRL+C` to stop the project.

## Fast run without activating `.venv`

Paste this if you do not want to activate the virtual environment:

```bash
cd /mnt/d/Desktop_informations/Competitions_2026/CIVIC_INTELLIGENCE_CARTOGRAPHY
.venv/bin/python scripts/seed_demo.py
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Then open:

```text
http://127.0.0.1:8000
```

## Safer paste-and-run command

Paste this if you are not sure whether `.venv` or dependencies are ready. It creates `.venv` only if missing, installs dependencies, seeds data, runs tests, then starts the server.

```bash
cd /mnt/d/Desktop_informations/Competitions_2026/CIVIC_INTELLIGENCE_CARTOGRAPHY
test -d .venv || python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/seed_demo.py
.venv/bin/python -m pytest -q
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

When you see this, the project is running:

```text
Uvicorn running on http://127.0.0.1:8000
Application startup complete.
```

## If port 8000 is busy

Paste this instead:

```bash
cd /mnt/d/Desktop_informations/Competitions_2026/CIVIC_INTELLIGENCE_CARTOGRAPHY
source .venv/bin/activate
python scripts/seed_demo.py
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Then open:

```text
http://127.0.0.1:8001
```

## Quick check from a second terminal

Keep the server running. Open another terminal and paste:

```bash
curl http://127.0.0.1:8000/health
```

Good result:

```json
{"status":"ok","service":"Bản Đồ Tin"}
```

Check that events exist:

```bash
curl -s http://127.0.0.1:8000/api/events | python -m json.tool | head
```

## Optional: fetch live news before opening the app

Use this only if you have internet access.

Fast RSS-only live news:

```bash
cd /mnt/d/Desktop_informations/Competitions_2026/CIVIC_INTELLIGENCE_CARTOGRAPHY
source .venv/bin/activate
python scripts/fetch_live_news.py --source vnexpress --limit 3 --rss-only
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Then open:

```text
http://127.0.0.1:8000
```

## Optional: fetch live news while the app is already running

Keep the server running. Open a second terminal and paste:

```bash
curl -X POST "http://127.0.0.1:8000/api/ingest/live-news?source=vnexpress&limit=3&fetch_full_text=false"
```

Then refresh:

```text
http://127.0.0.1:8000
```

## Stop project

In the terminal running `uvicorn`, press:

```text
CTRL+C
```

## My usual fastest command

For your current machine, this is probably the command you want most days:

```bash
cd /mnt/d/Desktop_informations/Competitions_2026/CIVIC_INTELLIGENCE_CARTOGRAPHY
.venv/bin/python scripts/seed_demo.py
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
