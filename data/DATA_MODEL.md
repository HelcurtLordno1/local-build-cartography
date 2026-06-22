# Data Model

## Purpose

This document defines the conceptual data model for Bản Đồ Tin. It is intended to guide database design, API contracts, AI outputs, and frontend expectations.

The model centers on the transformation from raw source material into verified civic events.

---

## Entity Relationship Overview

```text
Source
  │
  └── Article / Artifact
          │
          ├── ArticleVector
          │
          └── EventArticle
                    │
                    ▼
                  Event
                    │
                    ├── AgentDebate
                    ├── ConflictHeatmap
                    ├── ActionProtocol
                    └── TemporalArchaeologyResult
```

---

## Source

Represents an information origin.

Examples:

- VNExpress,
- Tuổi Trẻ,
- Dân Trí,
- VietnamNet,
- government portal,
- Zalo screenshot upload,
- radio broadcast,
- user-submitted URL.

Conceptual fields:

- `id`,
- `name`,
- `source_type`,
- `base_url`,
- `credibility_base_score`,
- `robots_policy`,
- `last_checked_at`,
- `metadata`.

---

## Article / Artifact

Represents normalized content from any modality.

Conceptual fields:

- `id`,
- `source_id`,
- `title`,
- `url`,
- `modality_type`,
- `published_at`,
- `ingested_at`,
- `clean_text`,
- `raw_artifact_ref`,
- `category`,
- `metadata`,
- `extraction_confidence`.

---

## ArticleVector

Represents embeddings for semantic comparison and retrieval.

Conceptual fields:

- `id`,
- `article_id`,
- `embedding_model`,
- `embedding_dimension`,
- `embedding`,
- `created_at`.

---

## Event

Represents a cluster of related articles/artifacts.

Conceptual fields:

- `id`,
- `canonical_title`,
- `generated_summary`,
- `category`,
- `severity_level`,
- `confidence_state`,
- `consensus_score`,
- `geographic_scope`,
- `latitude`,
- `longitude`,
- `cluster_size`,
- `first_seen_at`,
- `last_updated_at`,
- `status`.

---

## EventArticle

Links articles to events.

Conceptual fields:

- `event_id`,
- `article_id`,
- `similarity_score`,
- `relationship_type`,
- `is_primary_source`,
- `added_at`.

Relationship types:

- `primary_report`,
- `corroborating_report`,
- `conflicting_report`,
- `official_context`,
- `social_signal`,
- `historical_reference`.

---

## AgentDebate

Stores AI analysis and audit trail.

Conceptual fields:

- `id`,
- `event_id`,
- `media_agent_output`,
- `policy_agent_output`,
- `skeptic_agent_output`,
- `synthesis_output`,
- `prompt_versions`,
- `model_versions`,
- `input_hashes`,
- `created_at`,
- `fallback_flags`.

---

## ConflictHeatmap

Represents claim-level agreement and disagreement.

Conceptual fields:

- `id`,
- `event_id`,
- `agreed_facts`,
- `disputed_points`,
- `visual_encoding`,
- `created_at`.

---

## ActionProtocol

Represents a generated GCAP card.

Conceptual fields:

- `id`,
- `event_id`,
- `protocol_type`,
- `immediate_actions`,
- `verification_steps`,
- `legal_tools`,
- `community_sharing`,
- `historical_context`,
- `status`,
- `created_at`,
- `expires_at`.

---

## HistoricalCorpus

Represents seed and long-term knowledge for Temporal Archaeology.

Conceptual fields:

- `id`,
- `title`,
- `corpus_type`,
- `source_reference`,
- `date_reference`,
- `text`,
- `embedding`,
- `metadata`.

---

## Status Enums

### Confidence State

- `verified`,
- `high_confidence`,
- `developing`,
- `disputed`,
- `unverified`.

### Severity Level

- `critical`,
- `warning`,
- `information`.

### Modality Type

- `web`,
- `rss`,
- `pdf`,
- `screenshot`,
- `audio`,
- `direct_url`.

---

## Design Principle

Every user-visible event must be traceable backward:

```text
Event → Debate → Claims → Articles/Artifacts → Sources
```

This traceability is essential for trust, debugging, and responsible civic use.
