from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.schemas import ArticleIngestRequest, EventDetail, EventOut, IngestResponse
from app.core.config import get_settings
from app.core.database import init_db
from app.services import news_ingestion, pipeline, repository
from app.services.llm_enrichment import (
    cached_insights_match_event,
    enrich_event_with_llm,
    generate_deterministic_insights,
    llm_status,
)


settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()
    if settings.demo_mode and settings.seed_data_path.exists():
        pipeline.load_seed_data()


app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(Path(settings.static_dir) / "index.html")


@app.head("/")
def index_head() -> Response:
    return Response(status_code=200)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@app.get("/api/events", response_model=list[EventOut])
def events(
    date_range: str = Query("recent", description="recent, all, today, week, month, or year"),
    start_date: str | None = Query(None, description="Inclusive ISO date or datetime, e.g. 2026-06-10"),
    end_date: str | None = Query(None, description="Inclusive ISO date or datetime, e.g. 2026-06-21"),
    category: str = Query("all"),
    read_state: str = Query("all", description="all, read, or unread"),
    q: str | None = Query(None),
) -> list[dict]:
    return repository.list_events(
        date_range=date_range,
        start_date=start_date,
        end_date=end_date,
        category=category,
        read_state=read_state,
        query=q,
    )


@app.get("/api/events/{event_id}", response_model=EventDetail)
def event_detail(event_id: str) -> dict:
    detail = repository.event_detail(event_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if detail.get("action_protocol") is None or _is_stale_generated_action(detail["action_protocol"]):
        detail["action_protocol"] = repository.upsert_action_protocol(
            pipeline.build_action_protocol(detail["event"], detail["articles"])
        )
    return detail


def _is_stale_generated_action(protocol: dict) -> bool:
    legal_tools = protocol.get("legal_tools") or []
    has_current_parser = any("Phiên bản phân tích hành động: v2" in str(item) for item in legal_tools)
    has_auto_marker = any(str(item).startswith("Loại hành động:") for item in legal_tools)
    return any(str(item).startswith(("Priority Level:", "Official Sources:")) for item in legal_tools) or (
        has_auto_marker and not has_current_parser
    )


@app.post("/api/ingest/multi-modal", response_model=IngestResponse)
def ingest_multi_modal(payload: ArticleIngestRequest) -> dict:
    try:
        return pipeline.ingest_article(payload.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Ingest failed: {exc}") from exc


@app.patch("/api/events/{event_id}/read", response_model=EventOut)
def set_event_read(event_id: str, is_read: bool = Query(True)) -> dict:
    event = repository.set_event_read_state(event_id, is_read)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@app.delete("/api/events/{event_id}")
def delete_event(event_id: str) -> dict[str, str]:
    if not repository.soft_delete_event(event_id):
        raise HTTPException(status_code=404, detail="Event not found")
    return {"status": "deleted", "event_id": event_id}


@app.post("/api/ingest/live-news")
def ingest_live_news(
    source: str = Query("vnexpress", description="RSS source key from /api/news/sources, or all"),
    limit: int = Query(10, ge=1, le=50),
    fetch_full_text: bool = Query(True, description="Fetch article HTML after reading the RSS feed."),
    start_date: str | None = Query(None, description="Optional inclusive article start date."),
    end_date: str | None = Query(None, description="Optional inclusive article end date."),
) -> dict:
    try:
        if source == "all":
            return news_ingestion.fetch_many_sources(
                source_key=source,
                limit_per_source=limit,
                fetch_full_text=fetch_full_text,
                start_date=start_date,
                end_date=end_date,
            )
        return news_ingestion.fetch_live_news(
            source_key=source,
            limit=limit,
            fetch_full_text=fetch_full_text,
            start_date=start_date,
            end_date=end_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Live news fetch failed: {exc}") from exc


@app.get("/api/news/sources")
def news_sources() -> dict:
    sources = news_ingestion.load_configured_sources()
    return {
        "sources": [
            {
                "key": key,
                "name": source["name"],
                "base_url": source.get("base_url"),
                "feed_url": source.get("feed_url"),
            }
            for key, source in sorted(sources.items())
        ]
    }


@app.get("/api/debate/consensus/{event_id}")
def debate_consensus(event_id: str) -> dict:
    debate = repository.get_debate(event_id)
    if debate is None:
        raise HTTPException(status_code=404, detail="Debate not found")
    return debate


@app.post("/api/action/generate/{event_id}")
def generate_action(event_id: str) -> dict:
    detail = repository.event_detail(event_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Event not found")
    existing = repository.get_action_protocol(event_id)
    if existing and not _is_stale_generated_action(existing):
        return existing
    protocol = pipeline.build_action_protocol(detail["event"], detail["articles"])
    return repository.upsert_action_protocol(protocol)


@app.get("/api/archaeology/drill/{event_id}")
def archaeology_drill(event_id: str) -> dict:
    archaeology = repository.get_archaeology(event_id)
    if archaeology is None:
        raise HTTPException(status_code=404, detail="Archaeology result not found")
    return archaeology


@app.get("/api/llm/status")
async def get_llm_status() -> dict:
    return await llm_status()


@app.get("/api/events/{event_id}/llm-deepdive")
async def llm_deepdive(event_id: str) -> dict:
    """Lazily enrich a single event with a local LLM.

    Returns cached insights instantly if the event was already enriched;
    otherwise calls Ollama for this one event, persists the result, and returns
    it. If the LLM is disabled or unreachable, returns the deterministic
    fallback so the UI always has analysis to show.
    """
    detail = repository.event_detail(event_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Event not found")
    event = detail["event"]
    articles = detail["articles"]

    if event.get("llm_enriched") and cached_insights_match_event(event.get("llm_insights"), event, articles):
        return {"enriched": True, "source": event["llm_insights"].get("enrichment_source", "ollama"),
                "data": event["llm_insights"]}
    if event.get("llm_enriched"):
        repository.clear_llm_insights(event_id)

    fallback = generate_deterministic_insights(
        event, articles, detail.get("debate"), detail.get("action_protocol")
    )
    if not settings.llm_enabled:
        return {"enriched": False, "source": "deterministic_fallback",
                "error_code": "llm_disabled",
                "error": "LLM enrichment is disabled.",
                "hint": "Set LLM_ENABLED=true and start Ollama to enable AI enrichment.",
                "data": fallback}

    try:
        insights = await enrich_event_with_llm(event, articles)
        repository.save_llm_insights(event_id, insights)
        return {"enriched": True, "source": "ollama", "data": insights}
    except Exception as exc:
        error_code = getattr(exc, "code", "llm_unknown_error")
        hint = getattr(exc, "hint", "Check /api/llm/status for LLM connectivity details.")
        return {"enriched": False, "source": "deterministic_fallback",
                "error_code": error_code, "error": str(exc), "hint": hint, "data": fallback}


@app.websocket("/terrain/stream")
async def terrain_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            await websocket.send_json({"type": "terrain_snapshot", "events": repository.list_events()})
            await asyncio.sleep(8)
    except WebSocketDisconnect:
        return
