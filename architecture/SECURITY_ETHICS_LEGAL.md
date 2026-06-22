# Security, Ethics, and Legal Safeguards

## Purpose

Bản Đồ Tin processes civic information that may influence public behavior. The platform must therefore be designed with strong safeguards around source reliability, copyright, privacy, misinformation, and responsible AI presentation.

The system should help users understand uncertainty rather than amplify unverified claims.

---

## Content Safety

### Safety Screening

All ingested content should pass through a lightweight safety screening layer before public display.

Flag categories include:

- hate speech,
- graphic violence,
- illegal content,
- targeted harassment,
- personal data exposure,
- potentially dangerous emergency misinformation.

For the hackathon, a simple classifier and rule-based quarantine system is acceptable. A future production system can use a fine-tuned Vietnamese classifier such as PhoBERT.

---

## Source Verification

Sources should begin with different base credibility assumptions.

| Source Type | Initial Treatment |
|---|---|
| Government portals | High base credibility, still check dates and document relevance. |
| Established news outlets | Medium/high credibility, check source diversity. |
| Smaller blogs | Medium/low credibility until corroborated. |
| Social media screenshots | Unverified by default. |
| User-submitted URLs | Unknown until classified and corroborated. |
| Audio clips | Unverified until source and context are established. |

### Important Rule

A social media screenshot alone must never generate a verified event or high-confidence action card.

---

## AI Transparency

All user-facing AI outputs should include:

- confidence score,
- source list,
- last updated time,
- whether cloud or local fallback generated the result,
- disputed claims if any,
- clear labeling as AI-generated.

The system should avoid pretending that synthesized summaries are original reporting.

---

## Legal Compliance

### Robots.txt and Crawl Rate

Crawlers must respect:

- robots.txt directives,
- site-specific rate limits,
- user-agent identification,
- reasonable crawl intervals.

### Attribution

Every article-derived event should preserve:

- source name,
- original URL,
- publication timestamp,
- excerpt or headline attribution.

### Copyright

The system should avoid reproducing full copyrighted articles in user-facing pages. Use:

- metadata,
- short excerpts,
- generated summaries,
- links to original sources.

Government PDFs may be public domain or public records, but attribution should still be preserved.

---

## Privacy Requirements

### User Uploads

For uploaded screenshots, PDFs, and audio:

- collect only what is needed,
- avoid permanent storage unless authorized,
- anonymize personal identifiers where possible,
- redact phone numbers and private chat participants,
- display upload handling policy clearly.

### Social Screenshots

Screenshots from Zalo/Facebook may contain private conversations. They require special care:

- process locally where possible,
- quarantine sensitive screenshots,
- do not expose raw screenshot images publicly,
- use only extracted civic-relevant claims after anonymization.

---

## Bias Mitigation

The project addresses bias through structural design:

- multiple agents with different roles,
- explicit skeptic review,
- source diversity scoring,
- historical context through Temporal Archaeology,
- dispute heatmap instead of forced single narrative.

The system should also avoid over-weighting sources solely because they are frequent or highly indexed.

---

## Crisis and Emergency Information

For disasters, accidents, public health, and safety events:

- display timestamps prominently,
- avoid unsupported casualty numbers,
- prefer official emergency channels for action recommendations,
- mark developing information clearly,
- update or expire action cards as information changes.

Emergency numbers and official channels must be checked before production use.

---

## Human Review

A production system should include human review for:

- quarantined content,
- low-confidence high-severity events,
- viral social media claims,
- sensitive allegations,
- action cards involving legal or emergency behavior.

For the hackathon, simulate this through clear UI badges and prepared demo data.

---

## Ethical Presentation Rules

1. Do not hide uncertainty.
2. Do not overstate AI confidence.
3. Do not turn social rumors into official-looking facts.
4. Do not remove source context from summaries.
5. Do not encourage unsafe actions.
6. Do not replace official emergency guidance.
7. Do not expose private user-uploaded content.

---

## Demo Safety Guidance

Use demo scenarios that are realistic but controlled. Avoid live misinformation, active emergencies, or sensitive personal data in the pitch.

Recommended demo materials:

- public news articles,
- public government PDFs,
- synthetic or anonymized Zalo screenshots,
- short public-domain or self-recorded audio clips,
- seeded historical events and laws.
