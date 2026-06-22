# Multi-Modal Ingestion Architecture

## Purpose

The ingestion layer is what distinguishes Bản Đồ Tin from ordinary news aggregation systems. It is designed to process civic information from multiple Vietnamese information channels, not only from standard HTML articles.

The platform should support five major input streams:

1. RSS feeds and web articles,
2. government PDFs,
3. social media screenshots,
4. audio and radio broadcasts,
5. direct user-submitted URLs.

Each modality requires its own extraction approach, but all extracted content must normalize into a shared Article/Event pipeline.

---

## Ingestion Gateway

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                         INGESTION GATEWAY                                   │
│                                                                             │
│  Input 1: RSS Feeds and Web Articles                                        │
│  ├─ Parser: feedparser                                                       │
│  ├─ Extractor: vnnews selectors / newspaper3k                               │
│  └─ Fallback: Selenium + BeautifulSoup                                      │
│                                                                             │
│  Input 2: Government PDFs                                                   │
│  ├─ Parser: PyMuPDF                                                          │
│  ├─ Structure: legal document section parser                                │
│  └─ Metadata: document number, date, issuing body                           │
│                                                                             │
│  Input 3: Social Media Screenshots                                          │
│  ├─ Preprocess: OpenCV deskewing and contrast enhancement                   │
│  ├─ OCR: EasyOCR Vietnamese language pack                                   │
│  └─ Cleanup: OCR artifact correction                                        │
│                                                                             │
│  Input 4: Audio / Radio Broadcasts                                          │
│  ├─ Segmentation: PyDub silence-based chunking                              │
│  ├─ STT: local Whisper                                                       │
│  └─ Filtering: news versus advertisement                                    │
│                                                                             │
│  Input 5: Direct URL Paste                                                   │
│  ├─ Validation: reachability and content type                               │
│  ├─ Classification: news, blog, government, social, unknown                 │
│  └─ Routing: modality-specific parser                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Normalized Output Contract

Every modality should produce a normalized record with the following conceptual fields:

| Field | Description |
|---|---|
| `source_type` | `rss`, `web`, `pdf`, `screenshot`, `audio`, or `url`. |
| `title` | Best available title or generated title. |
| `source_name` | Outlet, government body, uploaded source label, or unknown source. |
| `published_at` | Source publication time if available. |
| `ingested_at` | System ingestion time. |
| `raw_artifact_ref` | Reference to raw HTML, PDF, OCR text, audio transcript, or uploaded file. |
| `clean_text` | Normalized text used by downstream AI and embedding pipeline. |
| `metadata` | Source-specific JSON metadata. |
| `confidence_flags` | Extraction confidence and warnings. |

---

## Web Articles

### Primary Method

Use a Vietnamese source selector registry derived from `vnnews`. Each known outlet should have domain-specific selectors for:

- headline,
- author,
- publication time,
- article body,
- category tags,
- canonical URL.

### Generic Fallback

When a domain is not in the selector registry, use newspaper-style heuristics to extract title, text, and metadata.

### JavaScript Fallback

For JavaScript-rendered pages, use a headless browser strategy:

1. load URL,
2. wait for DOM stabilization,
3. capture rendered HTML,
4. pass rendered content to the same extraction pipeline.

### Quality Controls

- Reject pages with extremely short extracted text unless manually approved.
- Keep source URL and attribution.
- Respect `robots.txt` and crawl-rate limits.
- Avoid storing full copyrighted article bodies beyond what is required for temporary processing unless licensing permits it.

---

## Government PDFs

Vietnamese government documents often contain structured legal signals such as:

- issuing authority,
- document number,
- date of issue,
- document type,
- article/clause structure,
- signatures or seals.

### Extraction Steps

1. Extract text with PyMuPDF.
2. Detect metadata using regex and structural patterns.
3. Segment into sections, articles, and clauses.
4. Use an LLM parser only where deterministic parsing is insufficient.
5. Store the raw PDF in artifact storage if legally permissible.
6. Store normalized legal references in the historical/legal corpus.

### Important Vietnamese Patterns

- Header: `CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM`
- Document number: `Số: .../...`
- Common types: `Nghị định`, `Thông tư`, `Công văn`, `Quyết định`, `Luật`

---

## Social Media Screenshots

Zalo and Facebook screenshots are important because Vietnamese civic information often circulates socially before formal publication.

### Processing Steps

1. Validate upload type and size.
2. Preprocess image:
   - deskew,
   - denoise,
   - improve contrast,
   - detect text regions.
3. Run Vietnamese OCR.
4. Correct common Vietnamese OCR artifacts:
   - missing diacritics,
   - `đ` misread as `d`,
   - broken lines,
   - merged words.
5. Mark source as **unverified** by default.
6. Require corroboration from additional sources before high-confidence presentation.

### Privacy Requirements

- Avoid permanent storage of personal screenshots unless explicitly authorized.
- Remove phone numbers, personal identifiers, and private chat metadata where possible.
- Display a clear unverified badge for screenshot-origin claims.

---

## Audio and Radio Broadcasts

Audio sources include radio news, public announcements, and broadcast clips.

### Processing Steps

1. Convert audio into a supported format.
2. Segment audio into manageable chunks, ideally around 30 seconds.
3. Use local Whisper for speech-to-text.
4. Remove advertisements and non-news segments.
5. Concatenate news segments into clean transcript.
6. Normalize transcript into the Article/Event pipeline.

### Speaker Handling

A lightweight speaker heuristic may label segments as:

- anchor,
- interviewee,
- advertisement,
- unknown.

For the hackathon, perfect speaker diarization is not required. The priority is reliable transcript extraction and civic relevance.

---

## Direct URL Submission

Users can paste URLs directly into the platform.

### URL Flow

1. Check reachability.
2. Validate content type.
3. Detect source class:
   - known news outlet,
   - unknown news/blog,
   - government document,
   - social/media page,
   - unsupported.
4. Route to the correct extraction method.
5. Process through priority queue.
6. Return job status to UI.

---

## Error Handling

Each ingestion job should produce one of these states:

- `received`,
- `extracting`,
- `extracted`,
- `normalized`,
- `queued_for_analysis`,
- `failed_retryable`,
- `failed_permanent`,
- `quarantined`.

Failures should include machine-readable reason codes such as:

- `blocked_by_robots`,
- `unsupported_format`,
- `ocr_low_confidence`,
- `pdf_no_text_layer`,
- `audio_transcription_failed`,
- `source_unreachable`,
- `content_safety_quarantine`.

---

## Demo Priorities

For the 48-hour build, prioritize:

1. five Vietnamese web sources,
2. one government PDF example,
3. one Zalo screenshot example,
4. one short audio clip,
5. one direct URL paste flow.

The demo does not need full production coverage. It needs to prove that the architecture supports information beyond web-only aggregation.
