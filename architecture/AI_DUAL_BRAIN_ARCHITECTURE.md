# AI Dual-Brain Architecture

## Purpose

The AI layer is the technical core of Bản Đồ Tin. It uses a dual-brain architecture to balance speed, cost, privacy, and reasoning depth.

- The **local brain** handles high-volume extraction, classification, critique, and preliminary reasoning.
- The **cloud brain** handles deep synthesis, causal reasoning, structured civic action generation, and narrative explanation.

This avoids overusing expensive cloud models while still using advanced reasoning where it matters most.

---

## Architecture Summary

```text
Raw / Clean Text
      │
      ▼
Local Brain — Qwen2.5-14B-Instruct
      │
      ├── Agent Truyền thông: factual claim extraction
      ├── Agent Chính sách: policy/legal relevance
      └── Agent Hoài nghi: skeptical critique
      │
      ▼
Debate Transcript
      │
      ▼
Cloud Brain — Claude
      │
      ├── Agent Tổng hợp: consensus synthesis
      └── Agent Hành động: civic action protocol generation
      │
      ▼
Consensus Score + Summary + Disputes + Action Card
```

---

## Local Brain

### Model

**Qwen2.5-14B-Instruct** is selected because it fits within a practical local inference envelope while providing strong multilingual performance, including Vietnamese.

### Serving Method

Recommended serving options:

- vLLM with OpenAI-compatible API,
- llama.cpp for constrained environments,
- AWQ or GPTQ quantization if GPU memory is limited.

### Responsibilities

The local model should handle:

- factual claim extraction,
- initial policy relevance matching,
- skeptical critique,
- classification,
- extraction normalization,
- batch processing across many articles.

### Local Brain Advantages

- Lower cost per event.
- Higher throughput for many articles.
- Better privacy for user-uploaded screenshots and documents.
- Reduced dependency on external APIs.
- Faster demo iteration during the hackathon.

---

## Cloud Brain

### Model Role

The cloud model is used only for high-value reasoning tasks that require stronger synthesis and careful instruction following.

### Responsibilities

The cloud brain should handle:

- consensus synthesis from multi-agent debate,
- neutral summary generation,
- causal inference and consequence projection,
- Generative Civic Action Protocols,
- final explanation for user-facing panels.

### Cost Control

Cloud calls must be:

- batched where possible,
- cached for at least 10 minutes for identical inputs,
- skipped for low-importance or duplicate events,
- retried with clear backoff,
- replaced by local fallback when unavailable.

---

## Agent Roles

| Agent | Role | Brain | Main Output |
|---|---|---|---|
| Agent Truyền thông | Media Analyst | Local | Factual claims, 5W1H extraction, source attribution. |
| Agent Chính sách | Policy Analyst | Local | Relevant laws, decrees, circulars, and applicability scores. |
| Agent Hoài nghi | Epistemic Skeptic | Local | Contradictions, missing context, source bias, trust risks. |
| Agent Tổng hợp | Consensus Synthesizer | Cloud | Consensus Confidence Score, agreed facts, disputed points, neutral summary. |
| Agent Hành động | Action Protocol Designer | Cloud | GCAP action card for high-confidence events. |

---

## Debate Protocol

### Round 1 — Parallel Local Analysis

The article or event cluster is sent to:

- Agent Truyền thông,
- Agent Chính sách.

These agents can run independently because they inspect the same source content from different perspectives.

### Round 2 — Skeptical Review

Agent Hoài nghi receives:

- the original source text,
- media claims,
- policy analysis,
- source metadata.

It identifies weaknesses, missing context, unsupported claims, bias, and contradictions.

### Round 3 — Cloud Synthesis

Agent Tổng hợp receives the full debate transcript and produces:

- agreed facts,
- disputed points,
- consensus score,
- neutral Vietnamese summary,
- explanation of confidence.

### Round 4 — Conditional Action Generation

If the Consensus Confidence Score is above the configured threshold, Agent Hành động generates a GCAP action card.

Recommended threshold for demo: `CCS > 70`.

---

## Fallback Behavior

If the cloud model is unavailable:

1. Retry according to exponential backoff.
2. Check cache for prior synthesis.
3. Fall back to local model with `fallback_generated = true`.
4. Display reduced-confidence warning in the UI.

If the local model is unavailable:

1. Queue analysis jobs until the service returns.
2. Allow source ingestion and storage to continue.
3. Display events as unverified pending analysis.

---

## Prompting Principles

All agents should follow these rules:

- output structured JSON,
- use Vietnamese where user-facing,
- avoid hallucinating missing facts,
- distinguish facts from opinions and predictions,
- cite source names or URLs when available,
- preserve uncertainty instead of forcing certainty,
- never present social screenshot claims as verified without corroboration.

---

## Auditability

Every agent run should be auditable through stored records:

- input text hash,
- prompt template version,
- model identifier,
- temperature,
- timestamp,
- raw output,
- parsed structured output,
- fallback or retry flags.

This is critical for explaining results to judges, users, and future partners.
