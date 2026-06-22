from app.services.pipeline import build_action_protocol, confidence_state, detailed_news_summary, extract_article_html, score_consensus
from app.services.news_ingestion import classify_category, parse_feed_entries
from app.services.llm_enrichment import (
    _extract_json_object,
    _normalise_insights,
    cached_insights_match_event,
    explain_llm_error,
    generate_deterministic_insights,
)
from app.services import repository
from app.core import config
from app.core.database import db_connection, init_db
import httpx


def test_confidence_state_ranges() -> None:
    assert confidence_state(85) == "verified"
    assert confidence_state(72) == "high_confidence"
    assert confidence_state(55) == "developing"
    assert confidence_state(35) == "disputed"
    assert confidence_state(20) == "unverified"


def test_consensus_penalizes_single_screenshot_style_signal() -> None:
    score = score_consensus(source_count=1, extraction_confidence=0.45, has_official=False, disputed=True)
    assert score < 50


def test_action_protocol_is_generated_for_low_score_events() -> None:
    event = {
        "id": "evt_test",
        "canonical_title": "Mưa lớn tại khu vực trung tâm",
        "category": "thoi-tiet",
        "severity_level": "critical",
        "geographic_scope": "Đà Nẵng",
        "consensus_score": 69,
        "confidence_state": "developing",
    }
    protocol = build_action_protocol(event)

    assert protocol is not None
    assert len(protocol["immediate_actions"]) >= 3
    assert any("dự báo" in item.lower() for item in protocol["immediate_actions"])
    assert any("Nguồn chính thức" in item for item in protocol["legal_tools"])


def test_action_protocol_extracts_citizen_actions_from_article_text() -> None:
    event = {
        "id": "evt_action_extract",
        "canonical_title": "Cảnh báo lừa đảo hoàn tiền",
        "category": "cong-nghe",
        "severity_level": "warning",
        "geographic_scope": "Việt Nam",
        "consensus_score": 72,
        "confidence_state": "high_confidence",
        "generated_summary": "Cơ quan chức năng cảnh báo tin nhắn giả mạo.",
    }
    articles = [
        {
            "clean_text": (
                "Cơ quan chức năng khuyến cáo người dùng không bấm liên kết lạ và không nhập OTP. "
                "Người dân nên chụp lại bằng chứng trước khi xóa tin nhắn. "
                "Cần kiểm tra website chính thức của ngân hàng hoặc gọi tổng đài trước khi làm theo hướng dẫn."
            )
        }
    ]

    protocol = build_action_protocol(event, articles)

    assert any("không bấm liên kết lạ" in item.lower() for item in protocol["immediate_actions"])
    assert any("chụp lại bằng chứng" in item.lower() for item in protocol["immediate_actions"])
    assert any("website chính thức" in item.lower() for item in protocol["verification_steps"])
    assert any("extracted_from_news" in item for item in protocol["legal_tools"])


def test_live_news_parser_preserves_provenance() -> None:
    feed = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0"><channel><title>Test feed</title>
      <item>
        <title>Mưa lớn gây ngập tại Đà Nẵng</title>
        <link>https://example.test/news/flood</link>
        <description><![CDATA[Chính quyền khuyến cáo người dân theo dõi mưa lớn và tránh khu vực ngập.]]></description>
        <pubDate>Sun, 21 Jun 2026 09:00:00 +0700</pubDate>
        <guid>flood-1</guid>
      </item>
    </channel></rss>"""
    source = {"name": "Example News", "feed_url": "https://example.test/rss.xml", "source_type": "rss"}

    payloads = parse_feed_entries(feed, source, limit=5)

    assert len(payloads) == 1
    assert payloads[0]["title"] == "Mưa lớn gây ngập tại Đà Nẵng"
    assert payloads[0]["category"] == "thoi-tiet"
    assert payloads[0]["geographic_scope"] == "Đà Nẵng"
    assert payloads[0]["metadata"]["provenance"] == "publisher_rss"
    assert payloads[0]["metadata"]["rss_entry_id"] == "flood-1"


def test_category_classifier_defaults_to_current_affairs() -> None:
    assert classify_category("Tin mới trong ngày", "Một bản tin tổng hợp") == "thoi-su"


def test_url_html_extraction_and_detailed_summary_format() -> None:
    html = """
    <html><head><meta property="og:title" content="Local URL headline"></head>
    <body><article><p>Local article text includes enough content to verify URL extraction,
    summary headings, source date handling, details, context, outlook, and sentiment output.</p></article></body></html>
    """
    title, text = extract_article_html(html)
    event = {"canonical_title": title, "category": "the-thao", "geographic_scope": "Việt Nam"}
    article = {
        "title": title,
        "source_name": "Local source",
        "published_at": "2026-06-21T07:00:00+00:00",
        "ingested_at": "2026-06-21T07:01:00+00:00",
        "clean_text": text,
    }

    summary = detailed_news_summary(event, [article])

    assert title == "Local URL headline"
    assert "Executive Summary" in summary
    assert "Key Takeaways" in summary
    assert "Story 1: Local URL headline" in summary
    assert "Source & Date: Local source · 2026-06-21T07:00:00+00:00" in summary
    assert "Cross-Story Analysis" in summary


def test_llm_insights_are_normalised_to_ui_contract() -> None:
    insights = _normalise_insights(
        {
            "ai_summary": " Tóm tắt civic. ",
            "agreed_facts": ["a", "b", "c", "d", "e", "f"],
            "disputed_points": ["x", "y"],
            "action_advice": ["verify"],
            "sentiment": "invalid",
        },
        "test-model",
    )

    assert insights["ai_summary"] == "Tóm tắt civic."
    assert insights["agreed_facts"] == ["a", "b", "c", "d", "e"]
    assert insights["sentiment"] == "stable"
    assert insights["enrichment_source"] == "ollama"
    assert insights["model"] == "test-model"


def test_llm_insights_are_bound_to_selected_event() -> None:
    event = {
        "id": "evt_weather_guard",
        "canonical_title": "Mưa lớn gây ngập tại Đà Nẵng",
        "generated_summary": "Mưa lớn gây ngập một số tuyến đường tại Đà Nẵng.",
    }
    articles = [{"id": "art_weather_guard", "title": "Mưa lớn tại Đà Nẵng", "clean_text": "Mưa lớn gây ngập đường."}]

    insights = _normalise_insights(
        {
            "event_id": "evt_weather_guard",
            "ai_summary": "Mưa lớn tại Đà Nẵng gây ngập đường và cần theo dõi cập nhật.",
            "agreed_facts": ["Mưa lớn xảy ra tại Đà Nẵng.", "Một số tuyến đường bị ngập."],
            "disputed_points": ["Mức độ ảnh hưởng còn cần xác minh."],
            "action_advice": ["Theo dõi thông báo giao thông địa phương."],
            "sentiment": "concerning",
        },
        "qwen3.5:9b",
        event,
        articles,
    )

    assert insights["event_id"] == "evt_weather_guard"
    assert insights["source_article_ids"] == ["art_weather_guard"]
    assert cached_insights_match_event(insights, event, articles)


def test_llm_rejects_wrong_event_output() -> None:
    event = {
        "id": "evt_weather_guard",
        "canonical_title": "Mưa lớn gây ngập tại Đà Nẵng",
        "generated_summary": "Mưa lớn gây ngập một số tuyến đường tại Đà Nẵng.",
    }

    try:
        _normalise_insights(
            {
                "event_id": "evt_other",
                "ai_summary": "Một bản tin kinh tế không liên quan.",
                "agreed_facts": ["Doanh nghiệp công bố lợi nhuận."],
                "disputed_points": [],
                "action_advice": [],
                "sentiment": "stable",
            },
            "qwen3.5:9b",
            event,
            [],
        )
    except ValueError as exc:
        assert "expected 'evt_weather_guard'" in str(exc)
    else:
        raise AssertionError("wrong-event LLM output should be rejected")


def test_extract_json_object_handles_wrapped_qwen_output() -> None:
    parsed = _extract_json_object("<think>brief</think>\n{\"event_id\":\"evt_1\",\"ai_summary\":\"ok\"}")

    assert parsed["event_id"] == "evt_1"


def test_llm_connection_error_is_actionable() -> None:
    error = explain_llm_error(httpx.ConnectError("All connection attempts failed"))

    assert error.code == "ollama_unreachable"
    assert "Cannot connect to Ollama" in str(error)
    assert "ollama pull" in error.hint


def test_llm_base_url_uses_wsl_gateway_when_available(monkeypatch) -> None:
    monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu")
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.setattr(
        config.subprocess,
        "check_output",
        lambda *args, **kwargs: b"default via 172.26.240.1 dev eth0 proto kernel\n",
    )
    config.get_settings.cache_clear()

    try:
        assert config.get_settings().llm_base_url == "http://172.26.240.1:11434"
    finally:
        config.get_settings.cache_clear()


def test_llm_base_url_falls_back_to_localhost_outside_wsl(monkeypatch) -> None:
    monkeypatch.delenv("WSL_DISTRO_NAME", raising=False)
    monkeypatch.delenv("WSL_INTEROP", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.setattr(config, "is_wsl_environment", lambda: False)
    config.get_settings.cache_clear()

    try:
        assert config.get_settings().llm_base_url == "http://127.0.0.1:11434"
    finally:
        config.get_settings.cache_clear()


def test_llm_base_url_env_override_wins(monkeypatch) -> None:
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://10.0.0.5:11434")
    config.get_settings.cache_clear()

    try:
        assert config.get_settings().llm_base_url == "http://10.0.0.5:11434"
    finally:
        config.get_settings.cache_clear()


def test_deterministic_llm_fallback_matches_deepdive_shape() -> None:
    event = {
        "id": "evt_llm_fallback",
        "canonical_title": "Cảnh báo mưa lớn",
        "generated_summary": "Mưa lớn có thể gây ngập tại một số tuyến đường.",
        "category": "thoi-tiet",
        "severity_level": "critical",
        "geographic_scope": "Việt Nam",
        "consensus_score": 62,
        "confidence_state": "developing",
    }

    insights = generate_deterministic_insights(event, [])

    assert set(["ai_summary", "agreed_facts", "disputed_points", "action_advice", "sentiment"]).issubset(insights)
    assert insights["sentiment"] == "urgent"
    assert insights["enrichment_source"] == "deterministic_fallback"


def test_repository_saves_and_reads_llm_insights(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "ban_do_tin_test.db"
    init_db(db_path)

    def _tmp_connection():
        return db_connection(db_path)

    monkeypatch.setattr(repository, "db_connection", _tmp_connection)

    now = "2026-06-21T07:00:00+00:00"
    repository.upsert_event(
        {
            "id": "evt_llm_cache",
            "canonical_title": "Cached LLM Event",
            "generated_summary": "Summary",
            "category": "thoi-su",
            "severity_level": "information",
            "confidence_state": "developing",
            "consensus_score": 55,
            "geographic_scope": "Việt Nam",
            "latitude": None,
            "longitude": None,
            "cluster_size": 1,
            "first_seen_at": now,
            "last_updated_at": now,
            "status": "active",
            "sources": [],
        }
    )
    insights = {
        "ai_summary": "Cached summary",
        "agreed_facts": ["fact"],
        "disputed_points": [],
        "action_advice": ["check source"],
        "sentiment": "stable",
    }

    repository.save_llm_insights("evt_llm_cache", insights)
    event = repository.get_event("evt_llm_cache")

    assert event["llm_enriched"] == 1
    assert event["llm_insights"] == insights
