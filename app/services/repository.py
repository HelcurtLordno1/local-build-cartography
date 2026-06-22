from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.database import db_connection, decode_row, encode_json, utcnow


def stable_id(prefix: str, text: str) -> str:
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def _range_start(date_range: str | None) -> str | None:
    if not date_range or date_range == "all":
        return None
    now = datetime.now(timezone.utc)
    ranges = {
        "recent": (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0),
        "today": now.replace(hour=0, minute=0, second=0, microsecond=0),
        "week": now - timedelta(days=7),
        "month": now - timedelta(days=30),
        "year": now - timedelta(days=365),
    }
    start = ranges.get(date_range)
    return start.isoformat() if start else None


def _parse_date_boundary(value: str | None, end_of_day: bool = False) -> str | None:
    if not value:
        return None
    try:
        if "T" in value:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            parsed = datetime.fromisoformat(value)
            parsed = parsed.replace(
                hour=23 if end_of_day else 0,
                minute=59 if end_of_day else 0,
                second=59 if end_of_day else 0,
                microsecond=999999 if end_of_day else 0,
                tzinfo=timezone.utc,
            )
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.isoformat()


def _event_date_filter_clause(start_date: str | None, end_date: str | None, params: list[Any]) -> str | None:
    start = _parse_date_boundary(start_date)
    end = _parse_date_boundary(end_date, end_of_day=True)
    if not start and not end:
        return None
    article_date = "COALESCE(articles.published_at, articles.ingested_at)"
    date_clauses = []
    if start:
        date_clauses.append(f"{article_date} >= ?")
        params.append(start)
    if end:
        date_clauses.append(f"{article_date} <= ?")
        params.append(end)
    return (
        "EXISTS (SELECT 1 FROM event_articles "
        "JOIN articles ON articles.id = event_articles.article_id "
        "WHERE event_articles.event_id = events.id AND "
        + " AND ".join(date_clauses)
        + ")"
    )


def list_events(
    date_range: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    category: str | None = None,
    read_state: str | None = None,
    query: str | None = None,
) -> list[dict[str, Any]]:
    clauses = ["deleted_at IS NULL"]
    params: list[Any] = []
    start = _range_start(date_range)
    if start:
        clauses.append("last_updated_at >= ?")
        params.append(start)
    custom_date_clause = _event_date_filter_clause(start_date, end_date, params)
    if custom_date_clause:
        clauses.append(custom_date_clause)
    if category and category != "all":
        clauses.append("category = ?")
        params.append(category)
    if read_state == "read":
        clauses.append("is_read = 1")
    elif read_state == "unread":
        clauses.append("is_read = 0")
    if query:
        clauses.append("(canonical_title LIKE ? OR generated_summary LIKE ? OR category LIKE ?)")
        like = f"%{query}%"
        params.extend([like, like, like])
    where = " AND ".join(clauses)
    with db_connection() as conn:
        rows = conn.execute(
            f"SELECT * FROM events WHERE {where} ORDER BY last_updated_at DESC, consensus_score DESC",
            params,
        ).fetchall()
    return [decode_row(row) for row in rows if row is not None]


def get_event(event_id: str) -> dict[str, Any] | None:
    with db_connection() as conn:
        row = conn.execute("SELECT * FROM events WHERE id = ? AND deleted_at IS NULL", (event_id,)).fetchone()
    return decode_row(row)


def get_articles_for_event(event_id: str) -> list[dict[str, Any]]:
    with db_connection() as conn:
        rows = conn.execute(
            """
            SELECT articles.*, sources.name AS source_name, sources.base_url AS source_base_url
            FROM articles
            JOIN event_articles ON event_articles.article_id = articles.id
            LEFT JOIN sources ON sources.id = articles.source_id
            WHERE event_articles.event_id = ?
            ORDER BY event_articles.is_primary_source DESC, articles.published_at DESC
            """,
            (event_id,),
        ).fetchall()
    return [decode_row(row) for row in rows if row is not None]


def _title_tokens(title: str) -> set[str]:
    text = re.sub(r"[^\w\sÀ-ỹ]", " ", title.lower(), flags=re.UNICODE)
    stopwords = {
        "the",
        "and",
        "for",
        "with",
        "from",
        "trong",
        "cua",
        "của",
        "cho",
        "voi",
        "với",
        "cac",
        "các",
        "mot",
        "một",
        "nhung",
        "những",
        "tin",
        "moi",
        "mới",
    }
    return {token for token in text.split() if len(token) > 2 and token not in stopwords}


def _title_similarity(left: str, right: str) -> float:
    left_tokens = _title_tokens(left)
    right_tokens = _title_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def find_similar_event(title: str, category: str, threshold: float = 0.45) -> dict[str, Any] | None:
    with db_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM events
            WHERE deleted_at IS NULL AND category = ?
            ORDER BY last_updated_at DESC
            LIMIT 200
            """,
            (category,),
        ).fetchall()
    best: tuple[float, dict[str, Any]] | None = None
    for row in rows:
        event = decode_row(row)
        if not event:
            continue
        score = _title_similarity(title, event["canonical_title"])
        if score >= threshold and (best is None or score > best[0]):
            best = (score, event)
    return best[1] if best else None


def get_debate(event_id: str) -> dict[str, Any] | None:
    with db_connection() as conn:
        row = conn.execute("SELECT * FROM debates WHERE event_id = ?", (event_id,)).fetchone()
    return decode_row(row)


def get_action_protocol(event_id: str) -> dict[str, Any] | None:
    with db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM action_protocols WHERE event_id = ?", (event_id,)
        ).fetchone()
    return decode_row(row)


def get_archaeology(event_id: str) -> dict[str, Any] | None:
    with db_connection() as conn:
        row = conn.execute("SELECT * FROM archaeology WHERE event_id = ?", (event_id,)).fetchone()
    return decode_row(row)


def event_detail(event_id: str) -> dict[str, Any] | None:
    event = get_event(event_id)
    if not event:
        return None
    return {
        "event": event,
        "articles": get_articles_for_event(event_id),
        "debate": get_debate(event_id),
        "action_protocol": get_action_protocol(event_id),
        "archaeology": get_archaeology(event_id),
    }


def upsert_source(source: dict[str, Any]) -> dict[str, Any]:
    source_id = source.get("id") or stable_id("src", source["name"])
    payload = {
        "id": source_id,
        "name": source["name"],
        "source_type": source.get("source_type", "web"),
        "base_url": source.get("base_url"),
        "credibility_base_score": source.get("credibility_base_score", 0.65),
        "metadata": source.get("metadata", {}),
    }
    with db_connection() as conn:
        conn.execute(
            """
            INSERT INTO sources (id, name, source_type, base_url, credibility_base_score, metadata)
            VALUES (:id, :name, :source_type, :base_url, :credibility_base_score, :metadata)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                source_type = excluded.source_type,
                base_url = excluded.base_url,
                credibility_base_score = excluded.credibility_base_score,
                metadata = excluded.metadata
            """,
            {**payload, "metadata": encode_json(payload["metadata"])},
        )
    return payload


def upsert_article(article: dict[str, Any]) -> dict[str, Any]:
    article_id = article.get("id") or stable_id(
        "art", f"{article.get('title')}:{article.get('url')}:{article.get('clean_text')[:80]}"
    )
    payload = {
        "id": article_id,
        "source_id": article.get("source_id"),
        "title": article["title"],
        "url": str(article["url"]) if article.get("url") else None,
        "modality_type": article.get("modality_type", "direct_url"),
        "published_at": article.get("published_at"),
        "ingested_at": article.get("ingested_at") or utcnow(),
        "clean_text": article["clean_text"],
        "category": article.get("category", "thoi-su"),
        "extraction_confidence": article.get("extraction_confidence", 0.75),
        "metadata": article.get("metadata", {}),
    }
    with db_connection() as conn:
        conn.execute(
            """
            INSERT INTO articles (
                id, source_id, title, url, modality_type, published_at, ingested_at,
                clean_text, category, extraction_confidence, metadata
            )
            VALUES (
                :id, :source_id, :title, :url, :modality_type, :published_at, :ingested_at,
                :clean_text, :category, :extraction_confidence, :metadata
            )
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                clean_text = excluded.clean_text,
                category = excluded.category,
                metadata = excluded.metadata
            """,
            {**payload, "metadata": encode_json(payload["metadata"])},
        )
    return payload


def upsert_event(event: dict[str, Any]) -> dict[str, Any]:
    event = {**event, "is_read": event.get("is_read", 0), "deleted_at": event.get("deleted_at")}
    with db_connection() as conn:
        conn.execute(
            """
            INSERT INTO events (
                id, canonical_title, generated_summary, category, severity_level,
                confidence_state, consensus_score, geographic_scope, latitude, longitude,
                cluster_size, first_seen_at, last_updated_at, status, sources, is_read, deleted_at
            )
            VALUES (
                :id, :canonical_title, :generated_summary, :category, :severity_level,
                :confidence_state, :consensus_score, :geographic_scope, :latitude, :longitude,
                :cluster_size, :first_seen_at, :last_updated_at, :status, :sources, :is_read, :deleted_at
            )
            ON CONFLICT(id) DO UPDATE SET
                generated_summary = excluded.generated_summary,
                severity_level = excluded.severity_level,
                confidence_state = excluded.confidence_state,
                consensus_score = excluded.consensus_score,
                cluster_size = excluded.cluster_size,
                last_updated_at = excluded.last_updated_at,
                sources = excluded.sources,
                deleted_at = NULL,
                llm_enriched = CASE
                    WHEN events.generated_summary = excluded.generated_summary
                         AND events.sources = excluded.sources
                    THEN events.llm_enriched
                    ELSE 0
                END,
                llm_insights = CASE
                    WHEN events.generated_summary = excluded.generated_summary
                         AND events.sources = excluded.sources
                    THEN events.llm_insights
                    ELSE NULL
                END
            """,
            {**event, "sources": encode_json(event.get("sources", []))},
        )
    return event


def set_event_read_state(event_id: str, is_read: bool) -> dict[str, Any] | None:
    with db_connection() as conn:
        conn.execute(
            "UPDATE events SET is_read = ? WHERE id = ? AND deleted_at IS NULL",
            (1 if is_read else 0, event_id),
        )
    return get_event(event_id)


def soft_delete_event(event_id: str) -> bool:
    with db_connection() as conn:
        cursor = conn.execute(
            "UPDATE events SET deleted_at = ? WHERE id = ? AND deleted_at IS NULL",
            (utcnow(), event_id),
        )
    return cursor.rowcount > 0


def save_llm_insights(event_id: str, insights: dict[str, Any]) -> None:
    """Cache LLM enrichment permanently against an event.

    Idempotent: once enriched, subsequent deep-dive requests read straight from
    the row without calling the LLM again.
    """
    with db_connection() as conn:
        conn.execute(
            "UPDATE events SET llm_enriched = 1, llm_insights = ? WHERE id = ?",
            (encode_json(insights), event_id),
        )


def clear_llm_insights(event_id: str) -> None:
    with db_connection() as conn:
        conn.execute(
            "UPDATE events SET llm_enriched = 0, llm_insights = NULL WHERE id = ?",
            (event_id,),
        )


def link_article(event_id: str, article_id: str, relationship_type: str, score: float = 0.76) -> None:
    with db_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO event_articles (
                event_id, article_id, similarity_score, relationship_type, is_primary_source, added_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (event_id, article_id, score, relationship_type, 1 if relationship_type == "primary_report" else 0, utcnow()),
        )


def upsert_debate(debate: dict[str, Any]) -> dict[str, Any]:
    with db_connection() as conn:
        conn.execute(
            """
            INSERT INTO debates (
                id, event_id, agreed_facts, disputed_points, agent_outputs, synthesis_output, created_at
            )
            VALUES (:id, :event_id, :agreed_facts, :disputed_points, :agent_outputs, :synthesis_output, :created_at)
            ON CONFLICT(event_id) DO UPDATE SET
                agreed_facts = excluded.agreed_facts,
                disputed_points = excluded.disputed_points,
                agent_outputs = excluded.agent_outputs,
                synthesis_output = excluded.synthesis_output
            """,
            {
                **debate,
                "agreed_facts": encode_json(debate.get("agreed_facts", [])),
                "disputed_points": encode_json(debate.get("disputed_points", [])),
                "agent_outputs": encode_json(debate.get("agent_outputs", {})),
            },
        )
    return debate


def upsert_action_protocol(protocol: dict[str, Any]) -> dict[str, Any]:
    with db_connection() as conn:
        conn.execute(
            """
            INSERT INTO action_protocols (
                id, event_id, protocol_type, immediate_actions, verification_steps,
                legal_tools, community_sharing, historical_context, status, created_at, expires_at
            )
            VALUES (
                :id, :event_id, :protocol_type, :immediate_actions, :verification_steps,
                :legal_tools, :community_sharing, :historical_context, :status, :created_at, :expires_at
            )
            ON CONFLICT(event_id) DO UPDATE SET
                immediate_actions = excluded.immediate_actions,
                verification_steps = excluded.verification_steps,
                legal_tools = excluded.legal_tools,
                community_sharing = excluded.community_sharing,
                historical_context = excluded.historical_context,
                status = excluded.status
            """,
            {
                **protocol,
                "immediate_actions": encode_json(protocol.get("immediate_actions", [])),
                "verification_steps": encode_json(protocol.get("verification_steps", [])),
                "legal_tools": encode_json(protocol.get("legal_tools", [])),
                "community_sharing": encode_json(protocol.get("community_sharing", [])),
                "historical_context": encode_json(protocol.get("historical_context", [])),
            },
        )
    return protocol


def upsert_archaeology(archaeology: dict[str, Any]) -> dict[str, Any]:
    with db_connection() as conn:
        conn.execute(
            """
            INSERT INTO archaeology (id, event_id, layers, created_at)
            VALUES (:id, :event_id, :layers, :created_at)
            ON CONFLICT(event_id) DO UPDATE SET layers = excluded.layers
            """,
            {**archaeology, "layers": json.dumps(archaeology.get("layers", {}), ensure_ascii=False)},
        )
    return archaeology
