# Adversarial Consensus Mining Engine

## Purpose

The Adversarial Consensus Mining Engine is the primary technical differentiator of Bản Đồ Tin. Instead of summarizing information once, the system uses multiple specialized agents to surface agreement, contradiction, uncertainty, source bias, and missing context.

The goal is not to classify claims as simply true or false. The goal is to compute a transparent, explainable **Consensus Confidence Score** and expose where sources agree or disagree.

---

## Core Concepts

| Concept | Definition |
|---|---|
| Claim | A factual statement extracted from one or more sources. |
| Event | A cluster of related articles or artifacts referring to the same civic occurrence. |
| Debate | The structured outputs of media, policy, and skeptic agents. |
| Consensus | The set of facts supported by agent analysis and source corroboration. |
| Dispute | A claim where sources or agents disagree, or where evidence is weak. |
| CCS | Consensus Confidence Score, a 0–100 measure of reliability. |

---

## Consensus Confidence Score

The CCS should be computed from several dimensions:

```text
CCS = (Agreement_Rate × 0.4)
    + (Source_Diversity × 0.3)
    + (Temporal_Consistency × 0.2)
    + (Corroboration_Evidence × 0.1)
```

The final score is expressed on a 0–100 scale.

---

## Score Components

### 1. Agreement Rate

Measures whether extracted factual claims are consistent across agents and sources.

Recommended scoring:

- `1.0` — all major agents and sources align,
- `0.7` — minor disagreement but core facts align,
- `0.4` — significant unresolved contradiction,
- `0.1` — most claims are disputed.

### 2. Source Diversity

Measures whether independent sources support the same claim.

Recommended scoring:

- `1.0` — three or more independent sources,
- `0.5` — two independent sources,
- `0.2` — single source,
- `0.1` — anonymous or unverified source only.

### 3. Temporal Consistency

Checks whether timestamps and sequence of events align.

This prevents old news, recycled screenshots, or delayed reports from being treated as current facts.

### 4. Corroboration Evidence

Measures whether there is primary evidence:

- official government announcement,
- images or video with metadata,
- named eyewitness report,
- emergency hotline or agency confirmation,
- legal document or administrative record.

---

## Conflict Heatmap

For each event, the system should generate a conflict heatmap that identifies specific disputed claims.

Conceptual structure:

```json
{
  "topic": "Bão số 3 đổ bộ",
  "consensus_score": 87,
  "agreed_facts": [
    "Bão số 3 đã đổ bộ vào Đà Nẵng lúc 14:00 ngày 20/9",
    "Sức gió tối đa đo được là 120km/h"
  ],
  "disputed_points": [
    {
      "claim": "3 người chết",
      "sources_pro": ["VNExpress", "Tuổi Trẻ"],
      "sources_con": ["Dân Trí"],
      "confidence": "medium"
    },
    {
      "claim": "Sập cầu Phong Châu",
      "sources_pro": ["Zalo screenshot"],
      "sources_con": ["VNExpress", "Chính phủ portal"],
      "confidence": "low",
      "note": "Single unverified source contradicts official reports"
    }
  ]
}
```

---

## User Interface Representation

The conflict heatmap should be visible in the Consensus Panel.

Recommended visual treatment:

- green for agreed facts,
- amber for partially supported claims,
- red for unresolved contradictions,
- gray for insufficient information,
- source badges for provenance,
- expandable debate transcript for transparency.

---

## Event Confidence States

| State | CCS Range | UI Treatment | Meaning |
|---|---:|---|---|
| Verified | 80–100 | Strong color, smooth texture | Multiple sources and agents align. |
| High Confidence | 70–79 | Strong color, minor caution badge | Good evidence with minor uncertainty. |
| Developing | 50–69 | Moderate color, amber badge | Some agreement but still incomplete. |
| Disputed | 30–49 | Jagged/noisy texture | Contradictions or weak corroboration. |
| Unverified | 0–29 | Gray/red warning texture | Single or unreliable source; do not act as fact. |

---

## Agent Debate Flow

1. **Extract claims** with Agent Truyền thông.
2. **Identify legal/policy context** with Agent Chính sách.
3. **Challenge assumptions** with Agent Hoài nghi.
4. **Cluster and compare claims** across sources.
5. **Compute CCS** using deterministic scoring plus synthesis explanation.
6. **Generate dispute heatmap** for UI transparency.
7. **Trigger action protocol** only if confidence threshold is met.

---

## Safeguards

- A single social media screenshot should never produce a high CCS alone.
- The system must distinguish source disagreement from agent disagreement.
- The UI must show uncertainty instead of hiding it.
- Time-sensitive crisis information should show last-updated timestamps prominently.
- Generated summaries must not amplify unsupported casualty counts, accusations, or emergency claims.

---

## Demo Scenario Recommendation

A strong demo event should include:

- at least three web articles,
- one conflicting claim,
- one official or government-related source,
- one action card generated after consensus,
- one archaeology precedent.

This lets judges see the system's value beyond summarization.
