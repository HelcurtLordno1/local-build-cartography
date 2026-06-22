# Worker Pipeline and Orchestration

## Purpose

Bản Đồ Tin depends on asynchronous processing because crawling, OCR, transcription, embeddings, multi-agent analysis, consensus synthesis, and action-card generation are too slow for direct request-response execution.

The worker architecture uses Celery with Redis to coordinate background processing, retries, and priority queues.

---

## Pipeline Overview

```text
Input URL / Feed / Upload
      │
      ▼
Crawl or Extract Raw Content
      │
      ▼
Normalize Text and Metadata
      │
      ▼
Generate Embedding
      │
      ▼
Deduplicate / Cluster
      │
      ▼
Run Local Agent Debate
      │
      ▼
Synthesize Consensus
      │
      ▼
Generate Action Card if CCS > Threshold
      │
      ▼
Publish Terrain Update
```

---

## Conceptual Celery Chain

```text
chain(
    crawl_article,
    extract_content,
    generate_embedding,
    deduplicate_faiss,
    group(
        agent_media,
        agent_policy
    ),
    agent_skeptic,
    synthesize_consensus,
    generate_action_card_if_eligible,
    publish_terrain_update
)
```

The actual implementation may vary, but the dependency order should remain consistent.

---

## Worker Responsibilities

### Crawl Workers

- Fetch RSS feeds.
- Crawl known Vietnamese outlets.
- Handle direct URL submissions.
- Respect robots.txt and crawl-rate limits.
- Store raw HTML or source references.

### Extraction Workers

- Extract article text and metadata.
- Parse PDFs.
- Run OCR on screenshots.
- Transcribe audio.
- Normalize text and source fields.

### Embedding Workers

- Generate multilingual text embeddings.
- Store vectors in pgvector.
- Update FAISS index when appropriate.

### Deduplication Workers

- Compare new content to recent event clusters.
- Link duplicate or related articles to existing events.
- Create new event records if no match is found.

### Agent Debate Workers

- Run media analyst prompt.
- Run policy analyst prompt.
- Run skeptic prompt.
- Store raw and parsed outputs.

### Synthesis Workers

- Call cloud reasoning model for consensus synthesis.
- Compute or validate Consensus Confidence Score.
- Produce neutral summary and dispute heatmap.

### Action Protocol Workers

- Generate GCAP card when CCS is above threshold.
- Attach verification steps, legal tools, sharing templates, and historical context.

### Notification Workers

- Publish updates to Redis pub/sub.
- Trigger WebSocket updates.
- Alert UI when critical events emerge.

---

## Queue Design

| Queue | Purpose | Priority |
|---|---|---:|
| `priority_ingest` | User-submitted URLs/uploads | Highest |
| `realtime_news` | RSS and known news source polling | High |
| `batch_documents` | Government PDFs and historical corpus | Medium |
| `agent_analysis` | Local AI agent processing | High |
| `cloud_synthesis` | Claude synthesis and action generation | Medium/high |
| `maintenance` | FAISS rebuild, cache cleanup, source refresh | Low |
| `dead_letter_queue` | Failed jobs requiring inspection | Special |

---

## Scheduling

### Real-Time News

Poll RSS feeds every 15 minutes.

### Batch Documents

Scan government PDFs and social/media trend inputs every 2 hours.

### User-Submitted URLs

Process immediately through priority queue.

### FAISS Rebuild

Rebuild every 6 hours or before the final demo.

### Cloud Cache Expiration

Cache cloud LLM outputs for at least 10 minutes to avoid repeated calls for identical inputs.

---

## Failure Handling

Each task should support:

- three retry attempts,
- exponential backoff,
- structured failure reason,
- visibility in job status API,
- routing to dead-letter queue after repeated failure.

### Common Failure Codes

| Code | Meaning |
|---|---|
| `source_unreachable` | URL or feed could not be accessed. |
| `extractor_failed` | Content extraction failed. |
| `ocr_low_confidence` | Screenshot text recognition was unreliable. |
| `transcription_failed` | Audio processing failed. |
| `embedding_failed` | Vector generation failed. |
| `local_llm_unavailable` | Qwen/vLLM service unavailable. |
| `cloud_llm_unavailable` | Cloud synthesis unavailable. |
| `safety_quarantine` | Content requires manual review. |

---

## Status Model

Each ingestion or analysis job should expose status values:

- `queued`,
- `running`,
- `waiting_for_dependency`,
- `completed`,
- `retrying`,
- `failed`,
- `quarantined`.

The UI should use this status to show progressive analysis:

1. received,
2. extracting,
3. debating,
4. synthesizing,
5. action-ready.

---

## Real-Time Terrain Updates

When an event changes, the worker pipeline should publish an event update containing:

- event ID,
- category,
- severity,
- consensus score,
- coordinates or semantic position,
- update reason,
- timestamp.

The frontend receives these through WebSocket and updates the terrain without full page reload.

---

## Demo Prioritization

For the hackathon, implement the minimum convincing path first:

1. crawl or load prepared articles,
2. extract text,
3. embed and cluster,
4. run local debate prompts,
5. synthesize consensus,
6. display map update,
7. generate one action card.

Then add cross-modal ingestion and polish.
