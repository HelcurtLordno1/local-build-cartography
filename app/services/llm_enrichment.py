from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.database import utcnow
from app.services import pipeline


# Sentiment values the LLM is asked to return. Anything outside this set is
# normalised to "stable" so the UI always renders a known badge.
VALID_SENTIMENTS = {"stable", "concerning", "urgent"}

INSIGHT_KEYS = ("ai_summary", "agreed_facts", "disputed_points", "action_advice", "sentiment")
OUTPUT_KEYS = (*INSIGHT_KEYS, "event_id")
STOPWORDS = {
    "about",
    "article",
    "bản",
    "các",
    "cho",
    "của",
    "đang",
    "được",
    "from",
    "khi",
    "một",
    "nguồn",
    "news",
    "những",
    "này",
    "the",
    "tin",
    "trong",
    "và",
    "với",
}


class LLMEnrichmentError(RuntimeError):
    def __init__(self, code: str, message: str, hint: str):
        super().__init__(message)
        self.code = code
        self.hint = hint


def explain_llm_error(exc: Exception) -> LLMEnrichmentError:
    settings = get_settings()
    if isinstance(exc, LLMEnrichmentError):
        return exc
    if isinstance(exc, httpx.ConnectError):
        return LLMEnrichmentError(
            "ollama_unreachable",
            f"Cannot connect to Ollama at {settings.llm_base_url}.",
            "Install and start Ollama, then run `ollama pull "
            f"{settings.llm_model}`. On this machine, `ollama serve` must expose port 11434.",
        )
    if isinstance(exc, httpx.TimeoutException):
        return LLMEnrichmentError(
            "ollama_timeout",
            f"Ollama did not respond within {settings.llm_timeout} seconds.",
            "Use a smaller local model, increase LLM_TIMEOUT, or keep using deterministic analysis.",
        )
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        body = exc.response.text[:240]
        if status == 404:
            return LLMEnrichmentError(
                "ollama_model_missing",
                f"Ollama is running, but model `{settings.llm_model}` was not found.",
                f"Run `ollama pull {settings.llm_model}` or set LLM_MODEL to an installed model.",
            )
        return LLMEnrichmentError(
            "ollama_http_error",
            f"Ollama returned HTTP {status}: {body}",
            "Check the Ollama server logs and configured LLM_MODEL.",
        )
    if isinstance(exc, ValueError):
        return LLMEnrichmentError(
            "ollama_invalid_json",
            str(exc),
            "Try a stronger instruction-following model or rerun the deep dive.",
        )
    return LLMEnrichmentError(
        "llm_unknown_error",
        str(exc),
        "Check /api/llm/status for the current LLM configuration and connectivity.",
    )


async def llm_status() -> dict[str, Any]:
    settings = get_settings()
    status = {
        "enabled": settings.llm_enabled,
        "provider": "ollama",
        "base_url": settings.llm_base_url,
        "configured_model": settings.llm_model,
        "ready": False,
        "models": [],
        "error_code": None,
        "message": None,
        "hint": None,
    }
    if not settings.llm_enabled:
        status.update(
            {
                "message": "LLM enrichment is disabled.",
                "hint": "Set LLM_ENABLED=true to enable local Ollama enrichment.",
            }
        )
        return status

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{settings.llm_base_url}/api/tags")
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        friendly = explain_llm_error(exc)
        status.update({"error_code": friendly.code, "message": str(friendly), "hint": friendly.hint})
        return status

    models = [model.get("name") for model in payload.get("models", []) if model.get("name")]
    status["models"] = models
    if settings.llm_model in models:
        status.update({"ready": True, "message": "Ollama is reachable and the configured model is installed."})
    else:
        status.update(
            {
                "error_code": "ollama_model_missing",
                "message": f"Ollama is reachable, but `{settings.llm_model}` is not installed.",
                "hint": f"Run `ollama pull {settings.llm_model}` or set LLM_MODEL to one of: {', '.join(models) or 'none installed'}.",
            }
        )
    return status


def build_prompt(event: dict[str, Any], articles: list[dict[str, Any]]) -> str:
    title = event.get("canonical_title", "")
    excerpts: list[str] = []
    for article in articles:
        text = (article.get("clean_text") or "")[:900]
        if text:
            excerpts.append(
                json.dumps(
                    {
                        "article_id": article.get("id"),
                        "title": article.get("title"),
                        "source": article.get("source_name") or article.get("source_id"),
                        "published_at": article.get("published_at"),
                        "excerpt": text,
                    },
                    ensure_ascii=False,
                )
            )
    if not excerpts:
        excerpts = [event.get("generated_summary", event.get("canonical_title", ""))[:900]]
    event_payload = {
        "event_id": event.get("id"),
        "canonical_title": title,
        "category": event.get("category"),
        "geographic_scope": event.get("geographic_scope"),
        "confidence_state": event.get("confidence_state"),
        "consensus_score": event.get("consensus_score"),
    }
    return f"""You are a civic intelligence analyst for Vietnamese news.
You must analyze ONLY the event and article excerpts below. Do not use memory,
outside news, prior chat context, or any other event. If the excerpts do not
support a claim, mark it as uncertain instead of inventing detail.

Event:
{json.dumps(event_payload, ensure_ascii=False)}

Article excerpts for this exact event:
{chr(10).join(excerpts)}

Return ONLY valid JSON with these exact keys and no markdown:
- "event_id": exactly "{event.get("id")}".
- "ai_summary": a 3-sentence synthesis of the situation in Vietnamese.
- "agreed_facts": a JSON array of 3 to 5 factual claims most sources agree on, in Vietnamese.
- "disputed_points": a JSON array of 2 to 4 points that are uncertain or conflicting, in Vietnamese.
- "action_advice": a JSON array of 2 to 3 concrete, safe actions a citizen could take, in Vietnamese.
- "sentiment": one of ["stable", "concerning", "urgent"].
"""


def _extract_json_object(raw_text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw_text)
        if isinstance(parsed, dict):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass

    match = re.search(r"\{.*\}", raw_text, flags=re.DOTALL)
    if not match:
        raise ValueError("LLM did not return a JSON object.")
    parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("LLM JSON response is not an object.")
    return parsed


def _topic_tokens(value: str) -> set[str]:
    text = re.sub(r"[^\w\sÀ-ỹ]", " ", value.lower(), flags=re.UNICODE)
    return {token for token in text.split() if len(token) >= 4 and token not in STOPWORDS}


def _validate_topic_alignment(raw: dict[str, Any], event: dict[str, Any], articles: list[dict[str, Any]]) -> None:
    event_id = event.get("id")
    if raw.get("event_id") != event_id:
        raise ValueError(
            f"LLM returned event_id {raw.get('event_id')!r}; expected {event_id!r}. "
            "Rejecting response to prevent cross-event analysis."
        )

    source_text = " ".join(
        [
            event.get("canonical_title", ""),
            event.get("generated_summary", "")[:500],
            *[article.get("title", "") for article in articles],
            *[(article.get("clean_text") or "")[:300] for article in articles],
        ]
    )
    output_text = " ".join(
        [
            str(raw.get("ai_summary") or ""),
            *[str(item) for item in raw.get("agreed_facts") or []],
            *[str(item) for item in raw.get("disputed_points") or []],
            *[str(item) for item in raw.get("action_advice") or []],
        ]
    )
    source_tokens = _topic_tokens(source_text)
    output_tokens = _topic_tokens(output_text)
    overlap = source_tokens & output_tokens
    minimum_overlap = min(3, max(1, len(source_tokens) // 12))
    if len(overlap) < minimum_overlap:
        raise ValueError(
            "LLM response did not share enough topic terms with the selected event. "
            "Rejecting response to prevent unrelated news analysis."
        )


def _normalise_insights(
    raw: Any, model: str, event: dict[str, Any] | None = None, articles: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Coerce arbitrary LLM JSON into the expected shape with safe defaults."""
    if not isinstance(raw, dict):
        raw = {}
    if event is not None:
        _validate_topic_alignment(raw, event, articles or [])

    summary = raw.get("ai_summary")
    if not isinstance(summary, str) or not summary.strip():
        summary = "Không tạo được tóm tắt AI cho sự kiện này."

    def _as_str_list(value: Any, limit: int) -> list[str]:
        if isinstance(value, list):
            items = [str(item).strip() for item in value if str(item).strip()]
            return items[:limit]
        return []

    sentiment = raw.get("sentiment")
    if sentiment not in VALID_SENTIMENTS:
        sentiment = "stable"

    return {
        "event_id": event.get("id") if event else raw.get("event_id"),
        "ai_summary": summary.strip(),
        "agreed_facts": _as_str_list(raw.get("agreed_facts"), 5),
        "disputed_points": _as_str_list(raw.get("disputed_points"), 4),
        "action_advice": _as_str_list(raw.get("action_advice"), 3),
        "sentiment": sentiment,
        "enrichment_source": "ollama",
        "model": model,
        "source_title": event.get("canonical_title") if event else None,
        "source_article_ids": [article.get("id") for article in (articles or []) if article.get("id")],
        "enriched_at": utcnow(),
    }


def cached_insights_match_event(
    insights: dict[str, Any] | None, event: dict[str, Any], articles: list[dict[str, Any]]
) -> bool:
    if not isinstance(insights, dict):
        return False
    settings = get_settings()
    if insights.get("model") != settings.llm_model:
        return False
    if insights.get("event_id") != event.get("id"):
        return False
    try:
        _validate_topic_alignment(insights, event, articles)
    except ValueError:
        return False
    return True


async def enrich_event_with_llm(
    event: dict[str, Any], articles: list[dict[str, Any]], timeout: float | None = None
) -> dict[str, Any]:
    """Call a local Ollama instance to enrich a single event.

    Raises on any network/parse error so the caller can fall back to the
    deterministic output. Never blocks ingestion — it is only invoked lazily
    from the deep-dive endpoint.
    """
    settings = get_settings()
    timeout = timeout if timeout is not None else settings.llm_timeout
    prompt = build_prompt(event, articles)
    payload = {
        "model": settings.llm_model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(f"{settings.llm_base_url}/api/generate", json=payload)
            response.raise_for_status()
            result = response.json()

        raw_text = result.get("response") or ""
        parsed = _extract_json_object(raw_text)
        return _normalise_insights(parsed, settings.llm_model, event, articles)
    except Exception as exc:
        raise explain_llm_error(exc) from exc


def _sentiment_from_event(event: dict[str, Any]) -> str:
    severity = event.get("severity_level")
    if severity == "critical":
        return "urgent"
    if severity == "warning":
        return "concerning"
    return "stable"


def generate_deterministic_insights(
    event: dict[str, Any],
    articles: list[dict[str, Any]],
    debate: dict[str, Any] | None = None,
    action_protocol: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the same insight shape from the deterministic pipeline.

    Used as the immediate cache when the LLM is disabled, and as the graceful
    fallback when Ollama is unreachable or returns invalid output.
    """
    if action_protocol is None:
        action_protocol = pipeline.build_action_protocol(event, articles)
    if debate is None:
        disputed = bool(event.get("disputed_points")) or event.get("confidence_state") == "disputed"
        debate = pipeline.build_debate(event, articles, disputed)

    agreed = debate.get("agreed_facts") or []
    disputes = [item.get("claim", str(item)) for item in (debate.get("disputed_points") or [])]
    actions = (action_protocol or {}).get("immediate_actions") or []

    return {
        "event_id": event.get("id"),
        "ai_summary": pipeline.summarize_text(event.get("generated_summary") or event.get("canonical_title", "")),
        "agreed_facts": list(agreed),
        "disputed_points": disputes,
        "action_advice": actions[:3],
        "sentiment": _sentiment_from_event(event),
        "enrichment_source": "deterministic_fallback",
        "model": None,
        "source_title": event.get("canonical_title"),
        "source_article_ids": [article.get("id") for article in articles if article.get("id")],
        "enriched_at": utcnow(),
    }
