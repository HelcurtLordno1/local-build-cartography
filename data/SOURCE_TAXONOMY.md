# Source Taxonomy

## Purpose

This document defines the categories and source treatment used by Bản Đồ Tin. It guides ingestion, filtering, event classification, credibility scoring, and UI color encoding.

---

## Source Types

| Source Type | Description | Initial Trust Treatment |
|---|---|---|
| Established news | Recognized Vietnamese news outlets. | Medium/high, still requires cross-source validation. |
| Government source | Official ministry, province, city, or agency portal. | High for official statements, check date and scope. |
| Social screenshot | Zalo, Facebook, or chat screenshot. | Unverified by default. |
| Audio broadcast | Radio, public announcement, or uploaded audio. | Depends on source identity and transcript confidence. |
| Blog / independent site | Small site or personal publication. | Medium/low until corroborated. |
| User-submitted URL | Any pasted link. | Unknown until classified. |
| Historical/legal corpus | Curated precedent or law. | High if source is official or curated. |

---

## Vietnamese News Categories

Initial taxonomy adapted from Vietnamese news structures:

| Category Key | Vietnamese Label | Description |
|---|---|---|
| `thoi_su` | Thời sự | General civic and national news. |
| `kinh_doanh` | Kinh doanh | Business and economic activity. |
| `phap_luat` | Pháp luật | Law, courts, enforcement, legal cases. |
| `the_gioi` | Thế giới | International news relevant to Vietnam. |
| `van_hoa` | Văn hóa | Culture and society. |
| `giai_tri` | Giải trí | Entertainment and showbiz. |
| `du_lich` | Du lịch | Tourism and travel. |
| `thoi_tiet` | Thời tiết | Weather, storms, floods, disaster monitoring. |
| `giao_thong` | Giao thông | Transport, accidents, roads, mobility. |
| `chinh_sach` | Chính sách | Policy changes, administrative decisions. |
| `suc_khoe` | Sức khỏe | Public health, hospitals, disease alerts. |
| `giao_duc` | Giáo dục | Schools, exams, education policy. |

---

## Severity Taxonomy

| Severity | Meaning | Example |
|---|---|---|
| `critical` | Immediate safety, legal, economic, or public order significance. | Flood warning, major accident, emergency policy deadline. |
| `warning` | Important but not immediately urgent. | Developing policy dispute, suspected scam, infrastructure disruption. |
| `information` | Useful civic context without urgent action. | Cultural event, tourism update, routine announcement. |

---

## Confidence Taxonomy

| Confidence State | Meaning |
|---|---|
| `verified` | Strong agreement across multiple reliable sources. |
| `high_confidence` | Good evidence with minor uncertainty. |
| `developing` | Early but plausible; needs more sources. |
| `disputed` | Conflicting claims or unclear evidence. |
| `unverified` | Weak, single-source, social-only, or low-confidence claim. |

---

## Credibility Inputs

Credibility is not a single source ranking. It combines:

- source identity,
- source independence,
- publication timestamp,
- corroboration,
- official confirmation,
- modality reliability,
- extraction confidence,
- agent critique severity.

---

## Source Diversity Rules

Sources should be considered independent only if they are not simply reposting the same original report.

Potentially independent:

- VNExpress and Tuổi Trẻ separately reporting an event,
- official government portal plus local news,
- eyewitness image plus official update.

Potentially not independent:

- identical syndicated text reposted across many sites,
- article copied from a press release without additional reporting,
- multiple screenshots from the same original message.

---

## UI Filtering

The taxonomy should power UI filters:

- category toggles,
- severity filters,
- confidence filters,
- source-type filters,
- time-window filters,
- official-source-only mode.

---

## Demo Recommendation

For the hackathon, include at least one event from each of these groups:

- `thoi_tiet` or disaster,
- `phap_luat` or consumer scam,
- `chinh_sach`,
- `giao_thong`,
- lower-severity culture or tourism item for contrast.
