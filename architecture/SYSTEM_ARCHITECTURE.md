# System Architecture

## Executive Overview

Bản Đồ Tin is architected as a three-tier civic intelligence platform with an asynchronous processing backbone. Its purpose is not only to aggregate Vietnamese information sources, but to construct a living and navigable knowledge topology from fragmented civic signals.

The platform follows a Lambda-style pattern:

- **Speed layer:** near-real-time ingestion and event updates,
- **Batch layer:** deeper analysis, historical context, and periodic reprocessing,
- **Serving layer:** API and terrain interface for exploration.

The architecture prioritizes modularity so that a 48-hour hackathon build can focus on integration and demo impact rather than excessive invention.

---

## High-Level Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                            PRESENTATION TIER                               │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │ Terrain Map  │  │ Consensus    │  │ Action Cards │  │ Archaeology    │  │
│  │ Mapbox/      │  │ Debate UI    │  │ GCAP         │  │ Timeline       │  │
│  │ Three.js     │  │              │  │              │  │                │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────────┘  │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────────┐
│                            API GATEWAY TIER                                 │
│                                                                             │
│                  FastAPI — Async REST + WebSocket                           │
│                                                                             │
│  /ingest/multi-modal     /terrain/stream      /debate/consensus             │
│  /action/generate        /archaeology/drill   /search/semantic              │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────────┐
│                         INTELLIGENCE WORKER TIER                            │
│                                                                             │
│                  Celery + Redis — Distributed Task Queue                     │
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────────────┐ │
│  │ Crawl       │  │ Extract &   │  │ Agent       │  │ Synthesis &        │ │
│  │ Workers     │  │ Embed       │  │ Debate      │  │ Action Engine      │ │
│  │ Local       │  │ Local       │  │ Workers     │  │ Cloud LLM          │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └────────────────────┘ │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │              Local LLM Inference Engine — Qwen2.5-14B                 │  │
│  │              vLLM or llama.cpp, OpenAI-compatible API                 │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────────┐
│                                DATA TIER                                    │
│                                                                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │ PostgreSQL +     │  │ MongoDB          │  │ FAISS / pgvector         │  │
│  │ pgvector         │  │ Raw artifacts    │  │ Semantic deduplication   │  │
│  │ Structured data  │  │                  │  │ and retrieval            │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Presentation Tier

The presentation tier converts civic intelligence into an explorable visual environment.

### Core Modules

- **Terrain Map:** 2.5D/3D visualization of event clusters.
- **Consensus Panel:** agent debate transcript, agreed facts, disputed points, and confidence score.
- **Action Cards:** practical GCAP outputs for high-confidence events.
- **Archaeology Timeline:** historical and legal context layers.
- **Cross-Modal Uploader:** drag-and-drop input for PDF, image, audio, and URL content.

### Responsibilities

- Render civic events spatially and semantically.
- Let users filter by category, severity, time, source, and confidence.
- Stream new urgent events through WebSocket updates.
- Preserve transparency by showing why the system believes or doubts a claim.

---

## API Gateway Tier

The API gateway should be implemented with FastAPI because it supports asynchronous request handling, Python-native AI tooling, and WebSocket endpoints.

### Representative Endpoints

| Endpoint | Purpose |
|---|---|
| `/ingest/multi-modal` | Accept direct uploads and user-submitted URLs. |
| `/terrain/stream` | Stream terrain events and critical updates. |
| `/debate/consensus` | Return agent debate and consensus score for an event. |
| `/action/generate` | Generate or retrieve GCAP action cards. |
| `/archaeology/drill` | Retrieve historical, legal, and simulation layers. |
| `/search/semantic` | Search events, articles, documents, and historical corpus semantically. |

### Design Principles

- Keep API contracts stable and structured.
- Return confidence and provenance with every AI-derived answer.
- Treat long-running processing as async jobs.
- Use WebSockets for live terrain changes instead of polling-heavy UI behavior.

---

## Intelligence Worker Tier

The worker tier is responsible for all high-latency and compute-heavy work.

### Worker Categories

| Worker Type | Responsibility |
|---|---|
| Crawl workers | Fetch RSS feeds, web pages, direct URLs, and source metadata. |
| Extraction workers | Clean text, parse PDFs, run OCR, transcribe audio, normalize metadata. |
| Embedding workers | Generate multilingual embeddings for deduplication and retrieval. |
| Agent debate workers | Execute media, policy, and skeptic prompts against the local model. |
| Synthesis workers | Call cloud reasoning model for consensus and action protocol generation. |
| Maintenance workers | Rebuild FAISS index, refresh source lists, clean expired cache entries. |

### Queue Model

Redis backs Celery queues with separate priority levels:

- `priority_ingest` for user-submitted URLs,
- `realtime_news` for RSS/news updates,
- `batch_documents` for government PDFs and historical corpus,
- `agent_analysis` for local AI debate,
- `cloud_synthesis` for Claude-based reasoning,
- `dead_letter_queue` for failed tasks.

---

## Data Tier

The data tier separates structured application state from raw artifacts and fast vector operations.

| Store | Responsibility |
|---|---|
| PostgreSQL | Canonical structured records for articles, events, debates, protocols, and metadata. |
| pgvector | Persistent semantic embeddings for retrieval and historical context. |
| MongoDB | Raw HTML, PDFs, OCR output, audio transcripts, and other reprocessable artifacts. |
| FAISS | In-memory near-duplicate detection and fast clustering support. |
| Redis | Celery broker/backend, cache for LLM responses, WebSocket pub/sub. |

---

## Architectural Rules

1. **Raw artifacts must remain separable from normalized records.**
2. **All AI outputs must be auditable through stored prompts, inputs, and outputs.**
3. **Consensus score must not be hidden behind a single summary.**
4. **Social media screenshots begin as unverified until corroborated.**
5. **Cloud LLM calls must be cached and reserved for high-value reasoning.**
6. **The frontend must never present low-confidence claims as verified facts.**
7. **All repositories integrated into the project must be adapted behind unified models and interfaces.**

---

## Recommended Implementation Order

1. Scaffold FastAPI, PostgreSQL, Redis, MongoDB, and frontend shell.
2. Integrate Vietnamese news crawling for a small number of sources.
3. Normalize article records and event clusters.
4. Add embeddings and deduplication.
5. Build the basic terrain map.
6. Add local AI agents.
7. Add cloud synthesis and consensus scoring.
8. Add GCAP cards.
9. Add cross-modal ingestion and archaeology layers.
10. Polish the demo scenario and visual storytelling.
