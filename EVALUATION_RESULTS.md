# Dr. Mood — Evaluation Results

## Retrieval Quality (embedding: gte-base, src/ pipeline)

| Metric | English |
|---|---|
| Precision@3 | 78.95% (15/19) |
| Precision@5 | 89.47% (17/19) |
| Precision@10 | 94.74% (18/19) |

`gte-base` is an English-only embedding model, so it is not evaluated directly on
Arabic queries. Arabic support in the live chatbot is handled at the application
layer instead: an Arabic question is translated to English before retrieval (so it
still searches the English-only corpus accurately), then the final answer is
generated back in Arabic. Live spot-checks of Arabic questions after this step show
top retrieval scores of 0.85–0.92, consistent with the English-language numbers above.

## Answer Grounding & Faithfulness

- Every source passed to the LLM is numbered; the system prompt requires a bracket
  citation (e.g. `[2]`) after any sentence drawn from that source, and forbids citing
  sources that weren't actually used.
- Refusal behavior: verified — a question with no relevant source (e.g. "best pizza
  topping") returns an explicit refusal instead of a fabricated or generic answer.
- Manual spot-check example: question "ايه هي اعراض الانتكاسة المبكرة؟" — answer cited
  [1], [2], [4] and correctly omitted [3] (an unrelated Treatment excerpt), showing the
  model does not cite indiscriminately.

## Clinical Safety & Responsible AI

- Crisis-language detection covers both English and Arabic/Egyptian-colloquial phrases
  (e.g. "kill myself", "عايز اموت", "مش قادر استحمل").
- On detection, the system returns a bilingual crisis-support message directing the
  user to emergency services/a trusted person, instead of continuing with general
  education.
- The system never provides a diagnosis, medication, or dosage advice for the person
  it's talking to (enforced in the system prompt for both patient and doctor roles).

## System Architecture

- FastAPI backend (Gemini for generation, ChromaDB + sentence-transformers for
  retrieval, SQLite for conversation history) + HTML/CSS/JS frontend, connected over
  a local REST API (`/api/chat`).
- Role-based prompting: patient vs. doctor mode changes system prompt tone/terminology
  without changing the retrieval pipeline.