The Strategy: Enrich Only What The User Actually Looks At
The workflow:

User ingests news → Your current pipeline runs in milliseconds. Events appear instantly on the terrain. (No LLM yet).

User clicks an event to open the detail panel → The UI shows the deterministic (template‑based) summary immediately.

While they read, the UI fires a background request to /api/events/{id}/llm-deepdive.

The backend checks: Does this event already have AI‑generated insights in the DB?

Yes → returns cached result instantly.

No → calls Ollama (or your chosen LLM) just for this single event, saves the result to the DB, returns it.

The UI slides the AI‑enhanced summary, debate trace, and action card right next to the deterministic one (or replaces it with a “✨ AI‑enhanced” toggle).

Why this is a "smart plan" for your portfolio:

Demonstrates latency awareness – you don’t block ingestion, and you don’t waste compute on unread news.

Shows caching & idempotency – once enriched, it stays enriched forever.

Proves graceful fallback – if Ollama isn’t running or times out (e.g., 8‑second timeout), the UI just shows the deterministic version with a small “AI unavailable” note.

Makes the app feel magical – the user clicks a card, and a few seconds later, a thoughtful AI‑generated civic analysis appears.

What To Implement (Minimal Changes)
1. Extend your Event schema (SQLite)
Add two columns to your events table:

llm_enriched (BOOLEAN, default 0)

llm_insights (TEXT, stores JSON like { "summary": "...", "debate": {...}, "action": {...} })

2. Create a new API endpoint
In app/main.py (or a new route file):

python
from app.services.llm_enrichment import enrich_event_with_llm

@app.get("/api/events/{event_id}/llm-deepdive")
async def get_llm_deepdive(event_id: int):
    event = get_event_by_id(event_id)  # your repo function
    
    if event.llm_enriched:
        return {"enriched": True, "data": json.loads(event.llm_insights)}
    
    # If not enriched, run the LLM pipeline synchronously (but with a timeout guard)
    try:
        insights = await enrich_event_with_llm(event_id, timeout=8.0)
        # Save to DB
        event.llm_insights = json.dumps(insights)
        event.llm_enriched = True
        save_event(event)  # your repo update
        return {"enriched": True, "data": insights}
    except Exception as e:
        # Log error, return deterministic fallback
        return {"enriched": False, "error": str(e), "fallback": generate_deterministic_insights(event)}
3. Write the LLM enrichment function (app/services/llm_enrichment.py)
Keep it focused on the three things that benefit most from AI:

Consensus summary (synthesising multiple article excerpts into a fluent narrative)

Debate trace (extracting agreed facts vs. disputed points with a “skeptic” voice)

Action protocol (extracting actual actionable sentences from the article text)

python
import httpx
import json
from app.services.repository import get_event_articles

async def enrich_event_with_llm(event_id: int, timeout: float = 8.0):
    articles = get_event_articles(event_id)
    titles = [a.title for a in articles]
    excerpts = [a.extracted_text[:500] for a in articles if a.extracted_text]  # trim for context
    
    prompt = f"""
You are a civic intelligence analyst for Vietnamese news. 
Analyze these articles about: {" | ".join(titles)}

Excerpts:
{"---".join(excerpts)}

Return ONLY valid JSON with these keys:
- "ai_summary": a 3‑sentence synthesis of the situation.
- "agreed_facts": list of 3‑5 factual claims most sources agree on.
- "disputed_points": list of 2‑4 points that are uncertain or conflicting.
- "action_advice": list of 2‑3 concrete, safe actions a citizen could take.
- "sentiment": one of ["stable", "concerning", "urgent"].
"""
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            "http://127.0.0.1:11434/api/generate",
            json={"model": "mistral:7b", "prompt": prompt, "stream": False, "format": "json"}  # `format: json` enforces JSON output in Ollama
        )
        result = response.json()
        return json.loads(result["response"])
4. Update your frontend (app/static/app.js)
In the event detail panel, after rendering the deterministic tabs, call:

javascript
fetch(`/api/events/${eventId}/llm-deepdive`)
  .then(r => r.json())
  .then(data => {
    if (data.enriched) {
      // Replace the "Consensus", "Action", "Archaeology" tabs with the AI versions
      // Or add a new tab called "AI Analysis ✨"
    }
  });
Show a small loading spinner while waiting.

If enriched is false, show a note: “AI enrichment unavailable – showing deterministic analysis.”

What This Looks Like In Your Portfolio
When you write this up, you can say:

“I designed a hybrid intelligence pipeline. The core ingestion remains deterministic and sub‑second, ensuring a responsive UX. AI enrichment is applied lazily – only when a user examines an event – using a local Ollama instance. This minimises compute cost, avoids queue infrastructure, and caches results permanently. The system gracefully degrades if the LLM is unavailable, maintaining full functionality.”

This is a production‑conscious, resource‑smart design. It shows you understand:

Asynchronous UX (non‑blocking UI updates),

Caching strategies,

Graceful degradation,

Prompt engineering and structured output,

Cost/performance trade‑offs.

What About Monitoring?
You don’t monitor anything.

If the LLM call times out, it raises an exception, the endpoint returns the fallback, and the frontend shows the deterministic version.

The DB stores the result permanently, so subsequent views are instant.

No queue, no worker, no Redis – just a simple request‑response that runs only when the user asks for it.

Quick Start To Test This
Install Ollama and pull a small model:

bash
ollama pull qwen3.5:9b   # You already have it, just use it.
Implement the three files above.

Run your server as usual.

Open the UI, ingest some news, click an event, and watch the AI analysis appear a few seconds later.

