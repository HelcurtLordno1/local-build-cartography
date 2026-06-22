from __future__ import annotations

import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import feedparser
import httpx
from bs4 import BeautifulSoup

from app.core.database import utcnow
from app.services import pipeline


DEFAULT_RSS_FEEDS: dict[str, dict[str, Any]] = {
    "vnexpress": {
        "name": "VnExpress",
        "source_type": "rss",
        "feed_url": "https://vnexpress.net/rss/tin-moi-nhat.rss",
        "base_url": "https://vnexpress.net",
        "credibility_base_score": 0.82,
    },
    "tuoitre": {
        "name": "Tuoi Tre Online",
        "source_type": "rss",
        "feed_url": "https://tuoitre.vn/rss/tin-moi-nhat.rss",
        "base_url": "https://tuoitre.vn",
        "credibility_base_score": 0.8,
    },
}


KNOWN_RSS_BY_HOST: dict[str, str] = {
    "vnexpress.net": "https://vnexpress.net/rss/tin-moi-nhat.rss",
    "tuoitre.vn": "https://tuoitre.vn/rss/tin-moi-nhat.rss",
    "dantri.com.vn": "https://dantri.com.vn/rss/home.rss",
    "thanhnien.vn": "https://thanhnien.vn/rss/home.rss",
    "cafef.vn": "https://cafef.vn/thi-truong-chung-khoan.rss",
    "vietnamnet.vn": "https://vietnamnet.vn/rss/tin-moi-nhat.rss",
    "vneconomy.vn": "https://vneconomy.vn/rss/tin-moi.rss",
    "baodautu.vn": "https://baodautu.vn/rss/home.rss",
    "baochinhphu.vn": "https://baochinhphu.vn/rss/trang-chu.rss",
    "vietnamplus.vn": "https://www.vietnamplus.vn/rss/home.rss",
    "nhandan.vn": "https://nhandan.vn/rss/home.rss",
    "vtv.vn": "https://vtv.vn/trang-chu.rss",
    "kenh14.vn": "https://kenh14.vn/home.rss",
    "znews.vn": "https://znews.vn/rss.html",
    "soha.vn": "https://soha.vn/rss.htm",
}


CATEGORY_KEYWORDS: list[tuple[str, set[str]]] = [
    ("thoi-tiet", {"mưa", "bão", "lũ", "ngập", "nắng nóng", "sạt lở", "áp thấp"}),
    ("giao-thong", {"giao thông", "tai nạn", "ùn tắc", "cao tốc", "đường sắt", "sân bay"}),
    ("phap-luat", {"lừa đảo", "bắt", "khởi tố", "công an", "tòa án", "vi phạm"}),
    ("chinh-sach", {"nghị định", "chính sách", "quy định", "thủ tục", "bảo hiểm", "thuế"}),
    ("du-lich", {"du lịch", "khách sạn", "tour", "vé máy bay", "điểm đến"}),
    ("van-hoa", {"văn hóa", "lễ hội", "triển lãm", "âm nhạc", "điện ảnh"}),
    ("the-thao", {"thể thao", "bóng đá", "tennis", "v-league", "world cup", "sea games"}),
    ("kinh-doanh", {"kinh doanh", "thị trường", "chứng khoán", "doanh nghiệp", "giá vàng", "lãi suất"}),
    ("suc-khoe", {"sức khỏe", "bệnh viện", "bác sĩ", "dịch bệnh", "vaccine", "y tế"}),
    ("giao-duc", {"giáo dục", "học sinh", "sinh viên", "đại học", "thi tốt nghiệp"}),
    ("cong-nghe", {"công nghệ", "ai", "trí tuệ nhân tạo", "điện thoại", "chip", "phần mềm"}),
]


LOCATION_HINTS: dict[str, tuple[str, float, float]] = {
    "hà nội": ("Hà Nội", 21.0278, 105.8342),
    "tp hcm": ("TP.HCM", 10.8231, 106.6297),
    "tphcm": ("TP.HCM", 10.8231, 106.6297),
    "đà nẵng": ("Đà Nẵng", 16.0471, 108.2068),
    "huế": ("Huế", 16.4637, 107.5909),
    "cần thơ": ("Cần Thơ", 10.0452, 105.7469),
    "hải phòng": ("Hải Phòng", 20.8449, 106.6881),
}


def strip_html(value: str | None) -> str:
    if not value:
        return ""
    text = BeautifulSoup(value, "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", unescape(text)).strip()


def normalize_datetime(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError, OverflowError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.isoformat()


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def parse_date_boundary(value: str | None, end_of_day: bool = False) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if "T" not in value:
        parsed = parsed.replace(
            hour=23 if end_of_day else 0,
            minute=59 if end_of_day else 0,
            second=59 if end_of_day else 0,
            microsecond=999999 if end_of_day else 0,
        )
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def classify_category(title: str, text: str) -> str:
    haystack = f"{title} {text}".lower()
    for category, keywords in CATEGORY_KEYWORDS:
        if any(keyword in haystack for keyword in keywords):
            return category
    return "thoi-su"


def detect_location(title: str, text: str) -> tuple[str, float | None, float | None]:
    haystack = f"{title} {text}".lower()
    for keyword, location in LOCATION_HINTS.items():
        if keyword in haystack:
            return location
    return ("Việt Nam", None, None)


def extract_article_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for selector in ("article", ".fck_detail", ".detail-content", ".content-detail", ".article-body"):
        node = soup.select_one(selector)
        if node:
            text = node.get_text(" ", strip=True)
            if len(text) >= 200:
                return re.sub(r"\s+", " ", text).strip()
    paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    text = " ".join(p for p in paragraphs if p)
    return re.sub(r"\s+", " ", text).strip()


def parse_feed_entries(feed_text: str, source: dict[str, Any], limit: int = 10) -> list[dict[str, Any]]:
    parsed = feedparser.parse(feed_text)
    items: list[dict[str, Any]] = []
    for entry in parsed.entries[:limit]:
        title = strip_html(entry.get("title"))
        link = entry.get("link")
        summary = strip_html(entry.get("summary") or entry.get("description"))
        if not title or not link:
            continue
        published_at = normalize_datetime(entry.get("published") or entry.get("updated"))
        category = classify_category(title, summary)
        geographic_scope, latitude, longitude = detect_location(title, summary)
        items.append(
            {
                "title": title,
                "source_name": source["name"],
                "source_type": source.get("source_type", "rss"),
                "base_url": source.get("base_url"),
                "credibility_base_score": source.get("credibility_base_score", 0.72),
                "url": link,
                "modality_type": "rss",
                "published_at": published_at,
                "clean_text": summary or title,
                "category": category,
                "latitude": latitude,
                "longitude": longitude,
                "geographic_scope": geographic_scope,
                "extraction_confidence": 0.78 if summary else 0.62,
                "metadata": {
                    "feed_url": source["feed_url"],
                    "rss_entry_id": entry.get("id") or entry.get("guid") or link,
                    "rss_published": entry.get("published") or entry.get("updated"),
                    "retrieved_at": utcnow(),
                    "provenance": "publisher_rss",
                },
            }
        )
    return items


def source_key_from_url(url: str) -> str:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    key = re.sub(r"[^a-z0-9]+", "_", host).strip("_")
    return key or "source"


def source_name_from_url(url: str) -> str:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    return host or url


def read_website_urls(path: Path | str = "websites_scrape.md") -> list[str]:
    text = Path(path).read_text(encoding="utf-8")
    urls = re.findall(r"https?://[^\s\]\)]+", text)
    seen: set[str] = set()
    ordered: list[str] = []
    for url in urls:
        cleaned = url.rstrip(".,")
        if cleaned not in seen:
            ordered.append(cleaned)
            seen.add(cleaned)
    return ordered


def load_configured_sources(path: Path | str = "websites_scrape.md") -> dict[str, dict[str, Any]]:
    sources = dict(DEFAULT_RSS_FEEDS)
    if not Path(path).exists():
        return sources
    existing_hosts = {
        urlparse(source.get("base_url") or source.get("feed_url") or "").netloc.lower().removeprefix("www.")
        for source in sources.values()
    }
    for url in read_website_urls(path):
        host = urlparse(url).netloc.lower().removeprefix("www.")
        if host in existing_hosts:
            continue
        key = source_key_from_url(url)
        sources.setdefault(
            key,
            {
                "name": source_name_from_url(url),
                "source_type": "rss",
                "feed_url": KNOWN_RSS_BY_HOST.get(host),
                "base_url": url,
                "credibility_base_score": 0.74,
            },
        )
        existing_hosts.add(host)
    return sources


def discover_feed_url(client: httpx.Client, source: dict[str, Any]) -> str | None:
    if source.get("feed_url"):
        return source["feed_url"]
    base_url = source.get("base_url")
    if not base_url:
        return None
    response = client.get(base_url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    for node in soup.find_all("link"):
        link_type = (node.get("type") or "").lower()
        href = node.get("href")
        if href and ("rss" in link_type or "atom" in link_type):
            return urljoin(base_url, href)
    for candidate in ("/rss", "/rss.xml", "/feed", "/feed.xml"):
        candidate_url = urljoin(base_url, candidate)
        try:
            candidate_response = client.get(candidate_url)
            if candidate_response.status_code < 400 and feedparser.parse(candidate_response.text).entries:
                return candidate_url
        except httpx.HTTPError:
            continue
    return None


def filter_payloads_by_date(
    payloads: list[dict[str, Any]], start_date: str | None = None, end_date: str | None = None
) -> list[dict[str, Any]]:
    start = parse_date_boundary(start_date)
    end = parse_date_boundary(end_date, end_of_day=True)
    if not start and not end:
        return payloads
    filtered = []
    for payload in payloads:
        published = parse_datetime(payload.get("published_at"))
        if not published:
            continue
        if start and published < start:
            continue
        if end and published > end:
            continue
        filtered.append(payload)
    return filtered


def fetch_live_news(
    source_key: str = "vnexpress",
    limit: int = 10,
    fetch_full_text: bool = True,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    configured_sources = load_configured_sources()
    if source_key not in configured_sources:
        allowed = ", ".join(sorted(configured_sources))
        raise ValueError(f"Unknown RSS source '{source_key}'. Available sources: {allowed}")

    source = configured_sources[source_key]
    fetched_at = utcnow()
    with httpx.Client(timeout=12.0, follow_redirects=True, headers={"User-Agent": "BanDoTin/0.1 RSS ingestion"}) as client:
        source["feed_url"] = discover_feed_url(client, source)
        if not source.get("feed_url"):
            raise ValueError(f"No RSS feed could be discovered for {source['name']}")
        feed_response = client.get(source["feed_url"])
        feed_response.raise_for_status()
        payloads = filter_payloads_by_date(parse_feed_entries(feed_response.text, source, limit=limit), start_date, end_date)
        for payload in payloads:
            payload["metadata"]["feed_http_status"] = feed_response.status_code
            if fetch_full_text:
                try:
                    article_response = client.get(payload["url"])
                    article_response.raise_for_status()
                    full_text = extract_article_text(article_response.text)
                except httpx.HTTPError as exc:
                    payload["metadata"]["article_fetch_error"] = str(exc)
                    full_text = ""
                if len(full_text) > len(payload["clean_text"]):
                    payload["clean_text"] = full_text
                    payload["extraction_confidence"] = 0.84
                    payload["metadata"]["provenance"] = "publisher_rss_and_article_html"

    ingested = []
    for payload in payloads:
        # ArticleIngestRequest requires at least 20 characters; short RSS blurbs are skipped instead of padded.
        if len(payload["clean_text"]) < 20:
            continue
        ingested.append(pipeline.ingest_article(payload))

    return {
        "source": source["name"],
        "feed_url": source["feed_url"],
        "fetched_at": fetched_at,
        "requested_limit": limit,
        "ingested_count": len(ingested),
        "events": [item["event"] for item in ingested],
    }


def fetch_many_sources(
    source_key: str = "all",
    limit_per_source: int = 10,
    fetch_full_text: bool = False,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    configured_sources = load_configured_sources()
    keys = list(configured_sources) if source_key == "all" else [source_key]
    results = []
    ingested_count = 0
    errors: list[dict[str, str]] = []
    for key in keys:
        try:
            result = fetch_live_news(
                source_key=key,
                limit=limit_per_source,
                fetch_full_text=fetch_full_text,
                start_date=start_date,
                end_date=end_date,
            )
            results.append(result)
            ingested_count += result["ingested_count"]
        except Exception as exc:
            errors.append({"source": key, "error": str(exc)})
    return {
        "source": source_key,
        "fetched_at": utcnow(),
        "source_count": len(keys),
        "ingested_count": ingested_count,
        "results": results,
        "errors": errors,
    }
