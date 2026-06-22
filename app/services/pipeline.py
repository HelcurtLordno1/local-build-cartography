from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.core.database import init_db, utcnow
from app.services import repository as repo


CATEGORY_SEVERITY = {
    "thoi-tiet": "critical",
    "giao-thong": "warning",
    "phap-luat": "warning",
    "chinh-sach": "information",
    "du-lich": "information",
    "van-hoa": "information",
    "thoi-su": "warning",
    "the-thao": "information",
    "kinh-doanh": "information",
    "suc-khoe": "information",
    "giao-duc": "information",
    "cong-nghe": "information",
}


def confidence_state(score: int) -> str:
    if score >= 80:
        return "verified"
    if score >= 70:
        return "high_confidence"
    if score >= 50:
        return "developing"
    if score >= 30:
        return "disputed"
    return "unverified"


def score_consensus(source_count: int, extraction_confidence: float, has_official: bool, disputed: bool) -> int:
    agreement = 0.7 if disputed else 0.92
    diversity = 1.0 if source_count >= 3 else 0.5 if source_count == 2 else 0.2
    temporal = 0.85
    corroboration = 1.0 if has_official else extraction_confidence
    score = (agreement * 0.4 + diversity * 0.3 + temporal * 0.2 + corroboration * 0.1) * 100
    final_score = max(10, min(98, round(score)))
    if disputed and source_count <= 1 and not has_official:
        return min(final_score, 49)
    return final_score


def summarize_text(text: str, limit: int = 220) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rsplit(" ", 1)[0] + "."


def extract_article_html(html: str) -> tuple[str | None, str]:
    soup = BeautifulSoup(html, "html.parser")
    title = None
    title_node = soup.find("meta", property="og:title") or soup.find("title")
    if title_node:
        title = title_node.get("content") or title_node.get_text(" ", strip=True)
    for selector in ("article", ".fck_detail", ".detail-content", ".content-detail", ".article-body", "main"):
        node = soup.select_one(selector)
        if node:
            text = node.get_text(" ", strip=True)
            if len(text) >= 200:
                return title, re.sub(r"\s+", " ", text).strip()
    paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    text = re.sub(r"\s+", " ", " ".join(p for p in paragraphs if p)).strip()
    return title, text


def fetch_url_content(url: str) -> dict[str, Any]:
    with httpx.Client(timeout=12.0, follow_redirects=True, headers={"User-Agent": "BanDoTin/0.1 Quick Ingest"}) as client:
        response = client.get(url)
        response.raise_for_status()
    title, clean_text = extract_article_html(response.text)
    return {
        "title": title,
        "clean_text": clean_text,
        "metadata": {
            "url_fetch_status": response.status_code,
            "url_fetched_at": utcnow(),
            "provenance": "direct_url_article_html",
        },
    }


def detailed_news_summary(event: dict[str, Any], articles: list[dict[str, Any]]) -> str:
    article_lines = []
    all_text = " ".join(article.get("clean_text", "") for article in articles)
    for index, article in enumerate(articles, start=1):
        date = article.get("published_at") or article.get("ingested_at") or "unknown date"
        article_lines.append(
            "\n".join(
                [
                    f"Story {index}: {article['title']}",
                    f"Source & Date: {article.get('source_name') or article.get('source_id') or 'Unknown source'} · {date}",
                    f"Summary: {summarize_text(article.get('clean_text', ''), 320)}",
                    "Details:",
                    f"- What: {summarize_text(article.get('clean_text', ''), 520)}",
                    f"- Where: {event.get('geographic_scope', 'Vietnam')}",
                    f"- Category: {event.get('category', 'thoi-su')}",
                    "Context: Based only on the supplied article text and preserved source metadata.",
                    "Outlook: Follow newer source updates before taking action or resharing.",
                    f"Sentiment: {infer_sentiment(all_text)}",
                ]
            )
        )
    takeaways = [summarize_text(article.get("clean_text", ""), 180) for article in articles[:8]]
    return "\n\n".join(
        [
            "Executive Summary",
            summarize_text(all_text or event["canonical_title"], 760),
            "Key Takeaways",
            "\n".join(f"- {item}" for item in takeaways if item),
            *article_lines,
            "Cross-Story Analysis",
            f"The current cluster contains {len(articles)} source item(s). Single-source items remain developing until corroborated by additional independent or official sources.",
        ]
    )


def infer_sentiment(text: str) -> str:
    negative_terms = {"cảnh báo", "nguy cơ", "tai nạn", "lừa đảo", "ngập", "thiệt hại", "ùn tắc", "bắt", "khởi tố"}
    positive_terms = {"khai trương", "tăng", "cải thiện", "thành công", "hỗ trợ", "phục hồi"}
    lowered = text.lower()
    negative = any(term in lowered for term in negative_terms)
    positive = any(term in lowered for term in positive_terms)
    if negative and positive:
        return "Mixed - the report contains both risk and improvement signals."
    if negative:
        return "Negative - the tone is cautionary or risk-focused."
    if positive:
        return "Positive - the tone emphasizes improvement or benefit."
    return "Neutral - the tone is primarily informational."


def build_debate(event: dict[str, Any], articles: list[dict[str, Any]], disputed: bool) -> dict[str, Any]:
    source_names = [source["name"] for source in event.get("sources", [])]
    agreed = [
        f"Sự kiện thuộc nhóm {event['category']} tại {event['geographic_scope']}.",
        f"Có {len(articles)} nguồn/artifact liên quan trong cụm hiện tại.",
        "Thông tin được giữ kèm nguồn, điểm tin cậy và trạng thái xác minh.",
    ]
    disputes = []
    if disputed:
        disputes.append(
            {
                "claim": "Một tín hiệu xã hội chưa có đủ xác nhận độc lập.",
                "sources_pro": source_names[-1:],
                "sources_con": source_names[:2],
                "confidence": "low",
                "note": "Theo quy tắc an toàn, ảnh chụp hoặc cảnh báo xã hội đơn lẻ không được xem là sự thật đã xác minh.",
            }
        )
    return {
        "id": repo.stable_id("debate", event["id"]),
        "event_id": event["id"],
        "agreed_facts": agreed,
        "disputed_points": disputes,
        "agent_outputs": {
            "media_agent": "Trích xuất tiêu đề, thời gian, địa điểm, nguồn và các tuyên bố chính.",
            "policy_agent": "Gắn sự kiện với kênh chính quyền, quy định hoặc thủ tục hành chính liên quan.",
            "skeptic_agent": "Đánh dấu khoảng trống bằng chứng, nguồn chưa độc lập và rủi ro khuếch đại tin đồn.",
        },
        "synthesis_output": (
            f"{event['canonical_title']} đạt CCS {event['consensus_score']}/100. "
            "Phần chắc chắn được trình bày riêng với các điểm còn tranh chấp để người dùng không nhầm lẫn giữa tín hiệu và sự thật."
        ),
        "created_at": utcnow(),
    }


def action_priority(event: dict[str, Any]) -> str:
    category = event.get("category")
    severity = event.get("severity_level")
    score = int(event.get("consensus_score") or 0)
    if severity == "critical" or category in {"thoi-tiet", "suc-khoe"}:
        return "High"
    if severity == "warning" or category in {"giao-thong", "phap-luat"}:
        return "Medium"
    if score < 50:
        return "Informational"
    return "Low"


def official_source_for_category(category: str) -> str:
    return {
        "thoi-tiet": "Trung tâm Dự báo Khí tượng Thủy văn Quốc gia và thông báo UBND địa phương.",
        "giao-thong": "Sở Giao thông Vận tải, Cục Cảnh sát giao thông và kênh vận tải công cộng địa phương.",
        "phap-luat": "Cổng thông tin Bộ Tư pháp, công an địa phương hoặc trung tâm trợ giúp pháp lý nhà nước.",
        "chinh-sach": "Cổng dịch vụ công, UBND phường/xã và cơ quan ban hành chính sách.",
        "kinh-doanh": "Ngân hàng Nhà nước, Bộ Tài chính, Tổng cục Thống kê và cơ quan bảo vệ người tiêu dùng.",
        "suc-khoe": "Bộ Y tế, Sở Y tế địa phương và cơ sở y tế gần nhất.",
        "giao-duc": "Bộ Giáo dục và Đào tạo, Sở Giáo dục địa phương và trường học liên quan.",
        "cong-nghe": "Cục An toàn thông tin, nhà mạng hoặc nền tảng dịch vụ chính thức.",
        "du-lich": "Cục Du lịch Quốc gia Việt Nam, Sở Du lịch địa phương và đơn vị vận chuyển/lưu trú chính thức.",
        "van-hoa": "Bộ Văn hóa, Thể thao và Du lịch, bảo tàng hoặc ban tổ chức chính thức.",
        "the-thao": "Ban tổ chức, liên đoàn thể thao hoặc cơ quan quản lý địa điểm thi đấu.",
    }.get(category, "Cổng thông tin chính quyền địa phương, báo chí chính thống và cơ quan chuyên ngành liên quan.")


CATEGORY_ACTION_DEFAULTS = {
    "thoi-tiet": [
        "Kiểm tra dự báo mới nhất và cảnh báo địa phương trước khi ra ngoài hoặc lên lịch di chuyển.",
        "Tránh khu vực ngập, sạt lở, nắng nóng cực đoan hoặc nơi có nguy cơ cây, biển hiệu, vật dụng rơi.",
        "Chuẩn bị áo mưa, nước uống, thuốc cá nhân, đèn pin hoặc pin dự phòng theo loại thời tiết được nêu.",
        "Nhắc trẻ em, người cao tuổi và người có bệnh nền hạn chế di chuyển khi cảnh báo còn hiệu lực.",
    ],
    "giao-thong": [
        "Kiểm tra tuyến đường bị ảnh hưởng và chọn tuyến thay thế trước khi khởi hành.",
        "Cộng thêm thời gian dự phòng nếu có phân luồng, ùn tắc, công trình, ngập nước hoặc tai nạn.",
        "Giảm tốc độ, giữ khoảng cách và tuân thủ hướng dẫn tại hiện trường.",
        "Không dừng lại quay phim, chụp ảnh hoặc đi vào khu vực bị hạn chế.",
    ],
    "phap-luat": [
        "Xác định bạn có thuộc nhóm cá nhân, hộ gia đình hoặc doanh nghiệp bị ảnh hưởng bởi vụ việc hay không.",
        "Lưu giấy tờ, tin nhắn, hóa đơn, ảnh chụp hoặc bằng chứng liên quan theo cách hợp pháp.",
        "Không ký giấy tờ, chuyển tiền hoặc cung cấp dữ liệu cá nhân khi chưa xác minh cơ quan yêu cầu.",
        "Liên hệ công an, UBND hoặc trợ giúp pháp lý nếu quyền lợi, tài sản hoặc an toàn của bạn bị ảnh hưởng.",
    ],
    "chinh-sach": [
        "Kiểm tra đối tượng áp dụng, thời điểm hiệu lực và địa bàn áp dụng của chính sách.",
        "Ghi lại hạn nộp hồ sơ, hạn góp ý, ngày bắt đầu hoặc ngày kết thúc được nêu trong bản tin.",
        "Chuẩn bị căn cước, giấy tờ cư trú, giấy phép, hóa đơn hoặc tài liệu chứng minh nếu cần thực hiện thủ tục.",
        "Hỏi UBND phường/xã hoặc cổng dịch vụ công nếu bản tin chưa đủ thông tin để hành động.",
    ],
    "kinh-doanh": [
        "Kiểm tra tác động trực tiếp đến chi phí sinh hoạt, khoản vay, tiết kiệm, hóa đơn hoặc hoạt động kinh doanh nhỏ.",
        "Đối chiếu thông tin với ngân hàng, cơ quan thuế, cơ quan thống kê hoặc đơn vị cung cấp dịch vụ chính thức.",
        "Không mua bán, chuyển tiền hoặc đầu tư chỉ dựa trên một bản tin chưa được xác minh.",
        "Lưu hợp đồng, biên lai và trao đổi với ngân hàng hoặc chuyên gia phù hợp nếu rủi ro tài chính lớn.",
    ],
    "suc-khoe": [
        "Xác định nhóm nguy cơ trong gia đình như trẻ nhỏ, người cao tuổi, phụ nữ mang thai hoặc người có bệnh nền.",
        "Kiểm tra khuyến cáo phòng bệnh, lịch tiêm, hướng dẫn khám hoặc số điện thoại y tế địa phương.",
        "Không tự dùng thuốc, chia sẻ đơn thuốc hoặc làm theo mẹo điều trị chưa có hướng dẫn y tế.",
        "Đến cơ sở y tế gần nhất hoặc gọi 115 nếu có triệu chứng nặng hoặc nguy hiểm trực tiếp.",
    ],
    "giao-duc": [
        "Kiểm tra học sinh, phụ huynh, lớp hoặc trường của bạn có thuộc phạm vi thông báo hay không.",
        "Ghi lại mốc tuyển sinh, lịch thi, hạn nộp hồ sơ, lịch nghỉ hoặc thay đổi chương trình.",
        "Chuẩn bị học bạ, giấy khai sinh, căn cước, ảnh, lệ phí hoặc tài khoản đăng ký trực tuyến nếu cần.",
        "Liên hệ nhà trường hoặc Sở Giáo dục nếu thông tin trong bản tin khác với thông báo chính thức.",
    ],
    "cong-nghe": [
        "Không bấm liên kết lạ hoặc nhập OTP, mật khẩu, số thẻ, thông tin ngân hàng từ tin nhắn chưa xác minh.",
        "Đổi mật khẩu, bật xác thực hai lớp và kiểm tra thiết bị nếu bản tin liên quan đến lừa đảo hoặc rò rỉ dữ liệu.",
        "Chụp lại bằng chứng trước khi xóa tin nhắn, email hoặc cuộc gọi đáng ngờ.",
        "Báo cáo sự cố cho nền tảng, nhà mạng, ngân hàng hoặc cơ quan an toàn thông tin nếu bạn bị ảnh hưởng.",
    ],
    "du-lich": [
        "Kiểm tra tình trạng điểm đến, phương tiện, lưu trú và chính sách hoàn hủy trước khi thanh toán hoặc khởi hành.",
        "Lưu mã đặt chỗ, hóa đơn, điều kiện vé và số liên hệ chính thức của đơn vị vận chuyển hoặc lưu trú.",
        "Không chuyển tiền qua liên kết, tài khoản hoặc đại lý chưa xác minh.",
        "Theo dõi thông báo của địa phương nếu bản tin liên quan đến thời tiết, an ninh, lễ hội hoặc quá tải điểm đến.",
    ],
    "van-hoa": [
        "Kiểm tra thời gian, địa điểm, vé vào cửa và quy định của ban tổ chức trước khi tham gia.",
        "Chuẩn bị giấy tờ, vé, trang phục hoặc yêu cầu an toàn nếu sự kiện có kiểm soát ra vào.",
        "Không chia sẻ lịch trình, giá vé hoặc thông báo thay đổi khi chưa có nguồn chính thức.",
        "Liên hệ ban tổ chức hoặc địa điểm nếu cần hỗ trợ tiếp cận, hoàn vé hoặc xác nhận thay đổi.",
    ],
    "the-thao": [
        "Kiểm tra lịch thi đấu, địa điểm, vé và quy định ra vào trước khi di chuyển.",
        "Theo dõi thông báo đổi lịch, đổi sân, an ninh hoặc giao thông quanh địa điểm thi đấu.",
        "Không mua vé qua nguồn không rõ ràng hoặc chuyển tiền trước khi xác minh người bán.",
        "Giữ giấy tờ, vé điện tử và thông tin liên hệ của ban tổ chức khi tham gia sự kiện.",
    ],
    "thoi-su": [
        "Xác định bản tin có ảnh hưởng trực tiếp đến khu vực, lịch trình, thủ tục hoặc an toàn của bạn hay không.",
        "Theo dõi cập nhật từ cơ quan liên quan trước khi thay đổi kế hoạch hoặc chia sẻ rộng rãi.",
        "Lưu lại nguồn, thời gian đăng và các chi tiết chính để đối chiếu khi có thông tin mới.",
        "Liên hệ chính quyền địa phương, trường học, nơi làm việc hoặc đơn vị dịch vụ nếu cần hướng dẫn cụ thể.",
    ],
}

ACTION_CUE_PATTERN = re.compile(
    r"\b(khuyến cáo|khuyến nghị|đề nghị|yêu cầu|cần|nên|không nên|không được|tránh|hạn chế|"
    r"chuẩn bị|kiểm tra|theo dõi|liên hệ|gọi|báo|lưu|chụp|đăng ký|nộp|cập nhật|đổi mật khẩu|"
    r"bật xác thực|đến cơ sở|tuân thủ|thực hiện|phòng tránh|cảnh giác|xác minh)\b",
    re.IGNORECASE,
)
VERIFY_CUE_PATTERN = re.compile(
    r"\b(xác minh|kiểm tra|đối chiếu|theo dõi|liên hệ|gọi|truy cập|nguồn chính thức|website|"
    r"cổng thông tin|tổng đài|hotline)\b",
    re.IGNORECASE,
)

IMMEDIATE_CUE_PATTERN = re.compile(
    r"\b(khuyến cáo|khuyến nghị|đề nghị|yêu cầu|không nên|không được|tránh|hạn chế|"
    r"chuẩn bị|lưu|chụp|đăng ký|nộp|đổi mật khẩu|bật xác thực|đến cơ sở|tuân thủ|thực hiện|"
    r"phòng tránh|cảnh giác)\b",
    re.IGNORECASE,
)


def default_actions_for_category(category: str) -> list[str]:
    return CATEGORY_ACTION_DEFAULTS.get(category, CATEGORY_ACTION_DEFAULTS["thoi-su"])


def split_action_sentences(text: str) -> list[str]:
    clean = re.sub(r"\s+", " ", text or "").strip()
    if not clean:
        return []
    return [item.strip(" -•\t") for item in re.split(r"(?<=[.!?。！？])\s+|[;\n]+", clean) if item.strip(" -•\t")]


def normalize_action_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip(" -•\t")
    text = re.sub(
        r"^.*?\b(?:khuyến cáo|khuyến nghị|đề nghị|yêu cầu)\s+(?:người dân|công dân|phụ huynh|học sinh|du khách|người dùng)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"^(?:người dân|công dân|phụ huynh|học sinh|du khách|người dùng)\s+(?:được\s+)?"
        r"(?:khuyến cáo|khuyến nghị|đề nghị|yêu cầu|cần|nên)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"^(người dân|công dân|phụ huynh|học sinh|du khách|người dùng)\s+", "", text, flags=re.IGNORECASE)
    if len(text) > 190:
        text = text[:187].rsplit(" ", 1)[0] + "..."
    return text[:1].upper() + text[1:] if text else text


def action_tokens(text: str) -> set[str]:
    return {token for token in re.sub(r"[^\w\sÀ-ỹ]", " ", text.lower(), flags=re.UNICODE).split() if len(token) > 3}


def add_unique_action(target: list[str], candidate: str, limit: int) -> None:
    candidate = normalize_action_text(candidate)
    if not candidate or len(candidate) < 18:
        return
    candidate_tokens = action_tokens(candidate)
    for existing in target:
        existing_tokens = action_tokens(existing)
        if candidate.lower() == existing.lower():
            return
        if candidate_tokens and existing_tokens:
            overlap = len(candidate_tokens & existing_tokens) / max(1, len(candidate_tokens | existing_tokens))
            if overlap >= 0.58:
                return
    target.append(candidate)
    del target[limit:]


def extract_citizen_actions(event: dict[str, Any], articles: list[dict[str, Any]] | None = None) -> tuple[list[str], list[str]]:
    texts = [article.get("clean_text", "") for article in articles or []]
    if not any(str(text).strip() for text in texts):
        texts = [event.get("generated_summary", ""), event.get("canonical_title", "")]
    immediate: list[str] = []
    verification: list[str] = []
    for sentence in split_action_sentences(" ".join(str(text) for text in texts if text)):
        if not ACTION_CUE_PATTERN.search(sentence):
            continue
        if VERIFY_CUE_PATTERN.search(sentence) and not IMMEDIATE_CUE_PATTERN.search(sentence):
            add_unique_action(verification, sentence, 3)
        else:
            add_unique_action(immediate, sentence, 4)
    if not immediate and verification:
        immediate, verification = verification[:2], verification[2:]
    return immediate, verification


def default_verification_steps(category: str) -> list[str]:
    return [
        "Đối chiếu thời gian cập nhật của bản tin với ít nhất một nguồn đáng tin cậy khác.",
        f"Ưu tiên xác nhận từ {official_source_for_category(category)}",
        "Không chia sẻ số liệu, cáo buộc, cảnh báo khẩn cấp hoặc ưu đãi tài chính khi chưa được xác minh.",
    ]


def build_action_protocol(event: dict[str, Any], articles: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    category = event["category"]
    title = event["canonical_title"]
    extracted_actions, extracted_verification = extract_citizen_actions(event, articles)
    immediate = extracted_actions or default_actions_for_category(category)
    verification = extracted_verification or default_verification_steps(category)
    action_source = "extracted_from_news" if extracted_actions else "section_default"
    return {
        "id": repo.stable_id("gcap", event["id"]),
        "event_id": event["id"],
        "protocol_type": category,
        "immediate_actions": immediate,
        "verification_steps": verification,
        "legal_tools": [
            f"Nguồn chính thức nên kiểm tra: {official_source_for_category(category)}",
            "Số khẩn cấp tại Việt Nam: 113, 114, 115 khi có nguy hiểm trực tiếp.",
            f"Loại hành động: {action_source}.",
            "Phiên bản phân tích hành động: v2.",
        ],
        "community_sharing": [
            f"Cập nhật công dân: {title}. Chỉ chia sẻ kèm nguồn, thời gian đăng và phần hướng dẫn đã được xác minh."
        ],
        "historical_context": [
            "So sánh với sự kiện tương tự trong lớp Temporal Archaeology để nhận diện tiền lệ, mùa vụ hoặc địa bàn lặp lại.",
            "Kiểm tra lớp pháp lý để biết quy định, quyền lợi, nghĩa vụ hoặc cơ quan chịu trách nhiệm.",
        ],
        "status": "generated",
        "created_at": utcnow(),
        "expires_at": None,
    }


def build_archaeology(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": repo.stable_id("arch", event["id"]),
        "event_id": event["id"],
        "layers": {
            "current": {
                "summary": event["generated_summary"],
                "confidence_state": event["confidence_state"],
            },
            "precedent": [
                "Đối chiếu với các cụm sự kiện cùng loại trong dữ liệu demo Da Nang Today.",
                "Ưu tiên tiền lệ có cùng địa bàn, mùa vụ hoặc nhóm đối tượng bị ảnh hưởng.",
            ],
            "legal_framework": [
                "Gắn với quy định phòng chống thiên tai, an toàn giao thông, bảo vệ người tiêu dùng hoặc thủ tục hành chính tùy loại sự kiện.",
                "Thông tin pháp lý trong bản demo là lớp định hướng, cần xác minh văn bản chính thức trước sử dụng thực tế.",
            ],
            "simulation": {
                "next_24h": "Nếu nguồn chính thức tăng xác nhận, CCS tăng và hành động được giữ ở trạng thái generated.",
                "risk": "Nếu xuất hiện mâu thuẫn nguồn, marker chuyển sang disputed và GCAP cần review.",
            },
        },
        "created_at": utcnow(),
    }


def ingest_article(payload: dict[str, Any]) -> dict[str, Any]:
    payload = dict(payload)
    metadata = dict(payload.get("metadata") or {})
    if payload.get("url") and (not payload.get("clean_text") or len(str(payload.get("clean_text")).strip()) < 20):
        fetched = fetch_url_content(str(payload["url"]))
        payload["clean_text"] = fetched["clean_text"]
        if fetched["title"] and (not payload.get("title") or payload["title"].lower() in {"url", "quick ingest"}):
            payload["title"] = fetched["title"]
        metadata.update(fetched["metadata"])
        payload["metadata"] = metadata
        payload["modality_type"] = payload.get("modality_type") or "direct_url"
        payload["extraction_confidence"] = 0.82 if len(payload["clean_text"]) >= 200 else 0.62
    if not payload.get("clean_text") or len(str(payload["clean_text"]).strip()) < 20:
        raise ValueError("Could not extract enough article text from the supplied URL or text.")

    source = repo.upsert_source(
        {
            "name": payload.get("source_name", "User submission"),
            "source_type": payload.get("source_type", "direct_url"),
            "base_url": payload.get("base_url") or (str(payload["url"]) if payload.get("url") else None),
            "credibility_base_score": payload.get(
                "credibility_base_score",
                0.55 if payload.get("modality_type") == "screenshot" else 0.72,
            ),
            "metadata": payload.get("source_metadata", {}),
        }
    )
    article = repo.upsert_article({**payload, "source_id": source["id"]})
    has_official = source["source_type"] in {"government", "pdf"} or "official" in source["name"].lower()
    disputed = payload.get("modality_type") == "screenshot"
    existing_event = repo.find_similar_event(payload["title"], payload["category"])
    if existing_event:
        event = existing_event
        sources = list(event.get("sources", []))
        if not any(item.get("article_id") == article["id"] for item in sources):
            sources.append({"name": source["name"], "type": source["source_type"], "article_id": article["id"]})
        articles = repo.get_articles_for_event(event["id"])
        if not any(item["id"] == article["id"] for item in articles):
            articles.append({**article, "source_name": source["name"]})
        has_official = has_official or any(item.get("type") in {"government", "pdf"} for item in sources)
        score = score_consensus(len(articles), min(item["extraction_confidence"] for item in articles), has_official, disputed)
        event = {
            **event,
            "generated_summary": summarize_text(payload["clean_text"]),
            "confidence_state": confidence_state(score),
            "consensus_score": score,
            "cluster_size": len(articles),
            "last_updated_at": utcnow(),
            "sources": sources,
        }
        event["generated_summary"] = detailed_news_summary(event, articles)
        relationship = "corroborating_report"
    else:
        score = score_consensus(1, article["extraction_confidence"], has_official, disputed)
        event = {
            "id": repo.stable_id("evt", f"{payload['category']}:{payload['title']}"),
            "canonical_title": payload["title"],
            "generated_summary": summarize_text(payload["clean_text"]),
            "category": payload["category"],
            "severity_level": CATEGORY_SEVERITY.get(payload["category"], "information"),
            "confidence_state": confidence_state(score),
            "consensus_score": score,
            "geographic_scope": payload.get("geographic_scope", "Vietnam"),
            "latitude": payload.get("latitude"),
            "longitude": payload.get("longitude"),
            "cluster_size": 1,
            "first_seen_at": payload.get("published_at") or utcnow(),
            "last_updated_at": utcnow(),
            "status": "active",
            "sources": [{"name": source["name"], "type": source["source_type"], "article_id": article["id"]}],
        }
        event["generated_summary"] = detailed_news_summary(event, [{**article, "source_name": source["name"]}])
        relationship = "primary_report"
    repo.upsert_event(event)
    repo.link_article(event["id"], article["id"], relationship)
    debate = repo.upsert_debate(build_debate(event, repo.get_articles_for_event(event["id"]), disputed))
    protocol = build_action_protocol(event, repo.get_articles_for_event(event["id"]))
    if protocol:
        repo.upsert_action_protocol(protocol)
    repo.upsert_archaeology(build_archaeology(event))
    return {
        "job_status": "queued_for_analysis",
        "article": article,
        "event": event,
        "debate": debate,
        "action_protocol": protocol,
    }


def load_seed_data(path: Path | None = None) -> None:
    init_db()
    seed_path = path or get_settings().seed_data_path
    data = json.loads(seed_path.read_text(encoding="utf-8"))
    for event_seed in data["events"]:
        sources = []
        articles = []
        for article_seed in event_seed["articles"]:
            source = repo.upsert_source(article_seed["source"])
            article = repo.upsert_article({**article_seed, "source_id": source["id"]})
            articles.append(article)
            sources.append({"name": source["name"], "type": source["source_type"], "article_id": article["id"]})
        disputed = bool(event_seed.get("disputed_points"))
        has_official = any(source["type"] in {"government", "pdf"} for source in sources)
        score = event_seed.get("consensus_score") or score_consensus(
            len(sources), min(a["extraction_confidence"] for a in articles), has_official, disputed
        )
        event = {
            **event_seed["event"],
            "consensus_score": score,
            "confidence_state": confidence_state(score),
            "cluster_size": len(articles),
            "first_seen_at": event_seed["event"].get("first_seen_at") or utcnow(),
            "last_updated_at": event_seed["event"].get("last_updated_at") or utcnow(),
            "sources": sources,
        }
        event["generated_summary"] = detailed_news_summary(
            event,
            [
                {
                    **article,
                    "source_name": next((source["name"] for source in sources if source["article_id"] == article["id"]), article.get("source_id")),
                }
                for article in articles
            ],
        )
        repo.upsert_event(event)
        for index, article in enumerate(articles):
            rel = event_seed["articles"][index].get("relationship_type", "corroborating_report")
            repo.link_article(event["id"], article["id"], rel, 0.83 - index * 0.04)
        debate = build_debate(event, articles, disputed)
        debate["agreed_facts"] = event_seed.get("agreed_facts", debate["agreed_facts"])
        debate["disputed_points"] = event_seed.get("disputed_points", debate["disputed_points"])
        repo.upsert_debate(debate)
        protocol = event_seed.get("action_protocol") or build_action_protocol(event, articles)
        if protocol:
            repo.upsert_action_protocol({**protocol, "id": repo.stable_id("gcap", event["id"]), "event_id": event["id"], "created_at": utcnow()})
        archaeology = event_seed.get("archaeology") or build_archaeology(event)
        repo.upsert_archaeology({**archaeology, "id": repo.stable_id("arch", event["id"]), "event_id": event["id"], "created_at": utcnow()})
