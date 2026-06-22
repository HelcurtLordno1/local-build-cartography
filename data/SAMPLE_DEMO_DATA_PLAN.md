# Sample Demo Data Plan

## Purpose

The hackathon demo should not depend entirely on live external data. Live crawling can fail because of network issues, robots rules, layout changes, or time pressure. This document defines a controlled demo data strategy that still feels realistic.

---

## Demo Scenario Name

**Da Nang Today**

The scenario presents a civic intelligence view of events affecting Đà Nẵng and nearby central Vietnam.

---

## Required Demo Inputs

### 1. Vietnamese News Articles

Prepare approximately 20 articles or article-like records.

Recommended distribution:

- 5 weather/disaster articles,
- 4 traffic/infrastructure articles,
- 4 policy or administrative articles,
- 3 consumer scam/legal articles,
- 2 tourism/culture articles,
- 2 conflicting or uncertain reports.

### 2. Government PDF

Prepare one public government document related to:

- disaster response,
- city administration,
- consumer protection,
- traffic regulation,
- local policy.

### 3. Zalo-Style Screenshot

Prepare one anonymized or synthetic screenshot that contains a civic claim.

The screenshot should include enough text for OCR but avoid personal data.

### 4. Audio Clip

Optional but valuable:

- short radio-style announcement,
- self-recorded Vietnamese audio,
- public-domain or authorized clip.

### 5. Historical and Legal Seeds

Prepare:

- 10 historical events,
- 5 laws/decrees/circulars,
- 3 emergency guidance references,
- 3 consumer protection references.

---

## Recommended Event Clusters

### Cluster 1 — Weather / Flood Risk

Sources:

- two established news articles,
- one official weather/government update,
- one social screenshot with unverified local claim.

Demo value:

- shows conflict heatmap,
- shows official corroboration,
- triggers action card,
- links to historical floods.

### Cluster 2 — Consumer Scam

Sources:

- one news article,
- one user-submitted warning,
- one legal reference.

Demo value:

- shows GCAP legal/admin tools,
- demonstrates skeptic agent warning,
- avoids emergency overclaiming.

### Cluster 3 — Policy Change

Sources:

- one government PDF,
- two news explanations,
- one historical precedent.

Demo value:

- shows PDF ingestion,
- shows legal framework layer,
- produces checklist-style action card.

### Cluster 4 — Traffic Disruption

Sources:

- news article,
- audio/radio transcript,
- map location.

Demo value:

- shows audio modality,
- creates visible geographic terrain marker,
- action card suggests route verification.

---

## Data Preparation Rules

- Use public sources when possible.
- Keep source attribution.
- Avoid personal data.
- Mark synthetic data clearly for internal demo use.
- Preserve timestamps so the time slider looks meaningful.
- Include at least one contradiction for the consensus engine to resolve.

---

## Backup Strategy

Prepare static JSON exports for all demo records:

- articles,
- events,
- debates,
- action cards,
- archaeology outputs.

If live ingestion fails, the demo can still show the full experience using preloaded data.

---

## Judge-Friendly Demo Flow

1. Start with a blank terrain.
2. Ingest prepared sources.
3. Show events appearing.
4. Open the flood-risk cluster.
5. Show a disputed screenshot claim.
6. Show consensus score resolving the uncertainty.
7. Generate action card.
8. Open archaeology layer showing historical flood precedent and legal framework.
9. End with map view showing the civic landscape.
