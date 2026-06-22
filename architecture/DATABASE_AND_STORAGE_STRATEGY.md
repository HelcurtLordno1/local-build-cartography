# Database and Storage Strategy

## Purpose

Bản Đồ Tin requires multiple storage systems because it handles structured metadata, raw artifacts, vector retrieval, fast deduplication, cache, queues, and real-time updates. Each storage technology has a clearly defined role.

The key principle is separation of concerns:

- PostgreSQL is the canonical source of structured truth.
- pgvector stores persistent embeddings.
- MongoDB stores raw and semi-structured artifacts.
- FAISS supports fast in-memory similarity operations.
- Redis supports task orchestration, cache, and pub/sub.

---

## Storage Overview

| Storage | Role | Data Examples |
|---|---|---|
| PostgreSQL | Canonical relational store | articles, events, debates, action cards, source records. |
| pgvector | Persistent vector retrieval | article embeddings, historical corpus embeddings, legal document vectors. |
| MongoDB | Raw artifact/data lake | raw HTML, PDF text, OCR output, audio transcripts, extraction diagnostics. |
| FAISS | Fast in-memory deduplication | recent article/event vectors for near-duplicate detection. |
| Redis | Queue/cache/pub-sub | Celery broker, Claude response cache, terrain WebSocket updates. |

---

## PostgreSQL Canonical Tables

### `articles`

Stores normalized records from all modalities.

Conceptual fields:

- `id`
- `title`
- `url`
- `source_name`
- `source_type`
- `published_at`
- `ingested_at`
- `raw_text`
- `clean_text`
- `modality_type`
- `category`
- `language`
- `metadata_json`
- `extraction_confidence`
- `raw_artifact_ref`

---

### `article_vectors`

Stores article-level embeddings for semantic search and deduplication.

Conceptual fields:

- `id`
- `article_id`
- `embedding_model`
- `embedding_dimension`
- `embedding`
- `created_at`

Recommended embedding model for multilingual demo:

`paraphrase-multilingual-MiniLM-L12-v2`

---

### `events`

Represents clustered civic events.

Conceptual fields:

- `id`
- `canonical_title`
- `generated_summary`
- `category`
- `severity_level`
- `consensus_score`
- `latitude`
- `longitude`
- `geographic_scope`
- `cluster_size`
- `first_seen_at`
- `last_updated_at`
- `status`
- `metadata_json`

---

### `event_articles`

Join table between events and source articles.

Conceptual fields:

- `event_id`
- `article_id`
- `relationship_type`
- `similarity_score`
- `is_primary_source`

---

### `agent_debates`

Stores the full audit trail of AI analysis.

Conceptual fields:

- `id`
- `event_id`
- `prompt_version`
- `model_versions_json`
- `media_agent_output_json`
- `policy_agent_output_json`
- `skeptic_agent_output_json`
- `synthesis_output_json`
- `consensus_score`
- `created_at`
- `fallback_flags_json`

---

### `action_protocols`

Stores GCAP cards linked to events.

Conceptual fields:

- `id`
- `event_id`
- `protocol_type`
- `immediate_actions_json`
- `verification_steps_json`
- `legal_tools_json`
- `community_sharing_json`
- `historical_context_json`
- `generated_by_model`
- `created_at`
- `expires_at`

---

### `historical_corpus`

Stores laws, historical events, and reference context for Temporal Archaeology.

Conceptual fields:

- `id`
- `title`
- `corpus_type`
- `source_ref`
- `date_ref`
- `text`
- `metadata_json`
- `embedding`

Corpus types:

- `law`,
- `decree`,
- `circular`,
- `historical_event`,
- `official_guidance`,
- `emergency_protocol`.

---

## MongoDB Raw Artifact Store

MongoDB stores raw and semi-structured artifacts before and after extraction.

Examples:

- raw HTML,
- rendered HTML,
- PDF extracted text,
- OCR raw output,
- OCR confidence maps,
- audio transcripts,
- ingestion diagnostics,
- original metadata from external libraries.

### Rationale

Raw artifacts are useful for:

- reprocessing when extraction improves,
- debugging failed ingestion,
- auditability,
- model evaluation,
- demo preparation.

### Privacy Note

User-uploaded screenshots and sensitive artifacts should be anonymized, time-limited, or excluded from permanent storage unless explicit permission exists.

---

## FAISS Deduplication Strategy

FAISS should be used as a high-speed in-memory index for near-duplicate detection during ingestion.

### Threshold

A cosine similarity above `0.92` should usually link a new article to an existing event rather than create a new event.

### Rebuild Schedule

The FAISS index should be rebuilt from PostgreSQL/pgvector periodically.

Recommended demo schedule:

- rebuild every 6 hours,
- update incrementally during active ingestion,
- force rebuild before final pitch demo.

---

## Redis Responsibilities

Redis has three primary responsibilities:

1. **Celery broker/backend** for distributed task execution.
2. **LLM response cache** with a 10-minute TTL for repeated cloud prompts.
3. **WebSocket pub/sub** for real-time terrain updates.

Recommended logical keys:

- `queue:*`
- `cache:claude:*`
- `cache:local_llm:*`
- `terrain:event_updates`
- `terrain:critical_alerts`
- `job_status:*`

---

## Data Retention Principles

- Keep normalized event metadata long-term.
- Keep raw web content only as legally permitted.
- Treat government documents as public but still preserve attribution.
- Anonymize or expire user-uploaded social screenshots.
- Store enough audit information to reproduce AI outputs.

---

## Implementation Priority

For the hackathon:

1. PostgreSQL tables for articles, events, debates, and action protocols.
2. pgvector or FAISS for deduplication.
3. Redis for Celery and cache.
4. MongoDB for raw artifacts if time allows.
5. Historical corpus seeded manually for demo.
