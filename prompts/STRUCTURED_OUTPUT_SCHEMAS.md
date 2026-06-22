# Structured Output Schemas

## Purpose

This document defines conceptual JSON output contracts for Bản Đồ Tin agents and processing stages. These schemas are documentation contracts, not executable code.

All AI-generated outputs should be validated before storage or display.

---

## Media Claims Output

```json
{
  "claims": [
    {
      "subject": "string",
      "action": "string",
      "object": "string",
      "time": "string",
      "location": "string",
      "source_attribution": "string",
      "type": "factual|subjective|prediction|unverified",
      "confidence": "low|medium|high"
    }
  ]
}
```

---

## Policy Analysis Output

```json
{
  "relevant_documents": [
    {
      "title": "string",
      "number": "string",
      "relevant_articles": ["string"],
      "applicability_score": 0,
      "reason": "string",
      "source_reference": "string"
    }
  ]
}
```

---

## Skeptic Critique Output

```json
{
  "critiques": [
    {
      "type": "missing_context|logical_issue|unverified_source|source_conflict|bias|temporal_issue|other",
      "severity": "low|medium|high",
      "explanation": "string",
      "affected_claim": "string"
    }
  ],
  "overall_trust_score": 0
}
```

---

## Consensus Synthesis Output

```json
{
  "event_title": "string",
  "consensus_score": 0,
  "confidence_state": "verified|high_confidence|developing|disputed|unverified",
  "neutral_summary_vi": "string",
  "agreed_facts": ["string"],
  "disputed_points": [
    {
      "claim": "string",
      "sources_pro": ["string"],
      "sources_con": ["string"],
      "confidence": "low|medium|high",
      "note": "string"
    }
  ],
  "score_breakdown": {
    "agreement_rate": 0,
    "source_diversity": 0,
    "temporal_consistency": 0,
    "corroboration_evidence": 0
  },
  "confidence_explanation": "string"
}
```

---

## Action Protocol Output

```json
{
  "event_id": "string",
  "protocol_type": "natural_disaster|consumer_scam|policy_change|traffic|public_health|general",
  "immediate_actions": [
    {
      "action": "string",
      "urgency": "low|medium|high",
      "reason": "string"
    }
  ],
  "verification_steps": ["string"],
  "legal_tools": [
    {
      "name": "string",
      "description": "string",
      "url_or_contact": "string",
      "verification_required": true
    }
  ],
  "community_sharing": {
    "zalo_message_vi": "string",
    "sms_message_vi": "string"
  },
  "historical_context": ["string"],
  "expires_at": "string"
}
```

---

## Conflict Heatmap Output

```json
{
  "topic": "string",
  "consensus_score": 0,
  "agreed_facts": ["string"],
  "disputed_points": [
    {
      "claim": "string",
      "sources_pro": ["string"],
      "sources_con": ["string"],
      "confidence": "low|medium|high",
      "note": "string"
    }
  ],
  "visual_encoding": {
    "texture": "smooth|mixed|jagged",
    "color_state": "green|amber|red|gray",
    "warning_badges": ["string"]
  }
}
```

---

## Terrain Event Output

```json
{
  "event_id": "string",
  "title": "string",
  "category": "string",
  "severity_level": "critical|warning|information",
  "confidence_state": "verified|high_confidence|developing|disputed|unverified",
  "consensus_score": 0,
  "cluster_size": 0,
  "coordinates": {
    "latitude": 0,
    "longitude": 0,
    "precision": "exact|city|province|national|semantic"
  },
  "terrain_encoding": {
    "elevation": 0,
    "color": "string",
    "texture": "string",
    "opacity": 0
  },
  "last_updated_at": "string"
}
```

---

## Temporal Archaeology Output

```json
{
  "event_id": "string",
  "surface": {
    "current_summary": "string",
    "latest_updates": ["string"]
  },
  "precedent": {
    "similar_events": [
      {
        "title": "string",
        "date": "string",
        "similarity_reason": "string",
        "outcome": "string"
      }
    ]
  },
  "framework": {
    "legal_references": [
      {
        "title": "string",
        "number": "string",
        "relevant_articles": ["string"],
        "explanation": "string"
      }
    ]
  },
  "simulation": {
    "possible_consequences": ["string"],
    "time_horizon": "string",
    "uncertainty_note": "string"
  }
}
```

---

## Validation Rules

- Required fields must be present.
- Scores must stay between 0 and 100.
- Confidence states must use approved enum values.
- Generated actions must not appear if consensus is too low.
- Unverified source claims must preserve their unverified status.
- Missing information should be written explicitly rather than hallucinated.
