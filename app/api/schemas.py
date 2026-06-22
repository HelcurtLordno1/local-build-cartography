from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator


ConfidenceState = Literal["verified", "high_confidence", "developing", "disputed", "unverified"]
SeverityLevel = Literal["critical", "warning", "information"]
ModalityType = Literal["web", "rss", "pdf", "screenshot", "audio", "direct_url"]


class SourceOut(BaseModel):
    id: str
    name: str
    source_type: str
    base_url: str | None = None
    credibility_base_score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArticleIngestRequest(BaseModel):
    title: str
    source_name: str = "User submission"
    source_type: str = "direct_url"
    url: HttpUrl | None = None
    modality_type: ModalityType = "direct_url"
    clean_text: str | None = None
    category: str = "thoi-su"
    latitude: float | None = None
    longitude: float | None = None
    geographic_scope: str = "Vietnam"

    @model_validator(mode="after")
    def require_text_or_url(self) -> "ArticleIngestRequest":
        if not self.url and (not self.clean_text or len(self.clean_text.strip()) < 20):
            raise ValueError("Provide a URL or at least 20 characters of source text.")
        return self


class ArticleOut(BaseModel):
    id: str
    source_id: str | None
    source_name: str | None = None
    source_base_url: str | None = None
    title: str
    url: str | None = None
    modality_type: str
    published_at: str | None = None
    ingested_at: str
    clean_text: str
    category: str
    extraction_confidence: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class EventOut(BaseModel):
    id: str
    canonical_title: str
    generated_summary: str
    category: str
    severity_level: SeverityLevel
    confidence_state: ConfidenceState
    consensus_score: int
    geographic_scope: str
    latitude: float | None = None
    longitude: float | None = None
    cluster_size: int
    first_seen_at: str
    last_updated_at: str
    status: str
    sources: list[dict[str, Any]] = Field(default_factory=list)
    is_read: int = 0
    deleted_at: str | None = None
    llm_enriched: int = 0
    llm_insights: dict[str, Any] | None = None


class DebateOut(BaseModel):
    id: str
    event_id: str
    agreed_facts: list[str]
    disputed_points: list[dict[str, Any]]
    agent_outputs: dict[str, Any]
    synthesis_output: str
    created_at: str


class ActionProtocolOut(BaseModel):
    id: str
    event_id: str
    protocol_type: str
    immediate_actions: list[str]
    verification_steps: list[str]
    legal_tools: list[str]
    community_sharing: list[str]
    historical_context: list[str]
    status: str
    created_at: str
    expires_at: str | None = None


class ArchaeologyOut(BaseModel):
    id: str
    event_id: str
    layers: dict[str, Any]
    created_at: str


class EventDetail(BaseModel):
    event: EventOut
    articles: list[ArticleOut]
    debate: DebateOut | None = None
    action_protocol: ActionProtocolOut | None = None
    archaeology: ArchaeologyOut | None = None


class IngestResponse(BaseModel):
    job_status: str
    article: ArticleOut
    event: EventOut
    debate: DebateOut
    action_protocol: ActionProtocolOut | None = None
