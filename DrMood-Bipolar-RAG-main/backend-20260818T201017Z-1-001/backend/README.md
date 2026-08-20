# Dr. Mood — Backend (FastAPI + RAG)

Backend for the Dr. Mood bipolar-support chat UI. Answers are generated only from
approved clinical source excerpts you ingest yourself (RAG), never from the model's
general knowledge — matching the "Based on approved clinical resources" evidence
drawer in the frontend.

## Stack
- **API:** FastAPI
- **DB (users/conversations/messages):** SQLite by default, swap to Postgres by changing `DATABASE_URL`
- **Vector store:** ChromaDB (local, persistent — no external service to run)
- **Embeddings:** sentence-transformers, runs locally, no API key needed
- **Generation:** Google Gemini API

## 1. Setup

```bash
cd dr-mood-backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# then edit .env and set GEMINI_API_KEY
```

## 2. Load sample clinical sources (optional, for demo purposes)

```bash
python -m app.seed_data.seed
```

This loads a few sample excerpts (mania, hypomania, Bipolar I, treatment) so the
app is usable immediately. **Replace these with your own vetted clinical guideline
content** before using this with real users — see "Ingesting real sources" below.

## 3. Run

```bash
uvicorn app.main:app --reload --port 8001
```

API docs: http://localhost:8001/docs

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/chat` | Ask a question. Body: `{conversation_id?, role: "patient"|"doctor", message}` → returns the assistant message + evidence list |
| GET | `/api/conversations` | List conversations for the sidebar History submenu |
| POST | `/api/conversations` | Start a new empty conversation |
| GET | `/api/conversations/{id}/messages` | Full message history (with evidence) for one chat |
| DELETE | `/api/conversations/{id}` | Delete a conversation |
| POST | `/api/documents/upload` | Ingest a PDF/text file as an approved source (admin) |
| POST | `/api/documents/text` | Ingest pasted text as an approved source (admin) |
| GET | `/api/documents` | List ingested source documents |
| GET | `/api/health` | Health check |

## Ingesting real clinical sources

```bash
curl -X POST http://localhost:8001/api/documents/upload \
  -F "title=DSM-5-TR Bipolar Criteria" \
  -F "category=Mania" \
  -F "page=123" \
  -F "file=@/path/to/guideline.pdf"
```

Only ingest material you're licensed/approved to use — the whole point of the RAG
design is that Dr. Mood can't say anything that isn't grounded in these sources.

## How answers stay grounded + safe

- Every answer is generated with the retrieved source text injected into the prompt,
  and the system prompt instructs the model to answer only from that context
  (`app/services/llm.py`).
- Patient-mode and doctor-mode use different system prompts (tone/terminology),
  matching the frontend's role switcher.
- Neither mode is allowed to give a diagnosis, a medication, or a dose.
- A lightweight keyword check (`app/services/safety.py`) flags possible crisis
  language and prepends a supportive message + `crisis_flag: true` in the response,
  independent of what the LLM itself says.
- This keyword check is a safety net, not a clinical triage tool — for a real
  deployment, pair it with proper crisis-detection and a human escalation path.

## Wiring up the existing frontend (`index.html`)

In `js/app.js`, replace the mocked send logic with something like:

```js
async function sendMessage(text, role, conversationId) {
  const res = await fetch("http://localhost:8001/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ conversation_id: conversationId, role, message: text }),
  });
  const data = await res.json();
  // data.message.content        -> assistant bubble text
  // data.message.evidence       -> array for the evidence drawer (source_title,
  //                                 source_meta, snippet, full_text, score, used)
  // data.crisis_flag            -> show crisis UI if true
  // data.conversation_id        -> store this for the next turn / sidebar history
  return data;
}
```

For the sidebar History submenu, call `GET /api/conversations` and render
`title` for each item; clicking one calls `GET /api/conversations/{id}/messages`
to repopulate the chat panel.

## Notes / production hardening to add before going live

- No auth is implemented yet — add user accounts + session/JWT auth before
  storing real patient conversations.
- Rate limit `/api/chat` and `/api/documents/*`.
- Put `/api/documents/*` behind an admin-only role.
- Consider a proper crisis-detection service instead of the keyword list.
- Add HTTPS/CORS origin lock-down for production domains in `.env`.
