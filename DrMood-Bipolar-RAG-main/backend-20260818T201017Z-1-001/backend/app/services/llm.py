import google.generativeai as genai

from app.config import settings

if settings.gemini_api_key:
    genai.configure(api_key=settings.gemini_api_key)


PATIENT_SYSTEM_PROMPT = """You are Dr. Mood, an AI assistant that explains bipolar disorder \
using ONLY the approved clinical source excerpts provided to you in the CONTEXT block. \
You are talking to a patient or a member of the public, not a clinician.

Rules:
- ALWAYS reply in the same language the person used for their question (for example, if they \
wrote in Arabic, reply entirely in Arabic, translating relevant clinical content from the \
English CONTEXT naturally — do not mix languages within a reply).
- Base every factual claim strictly on the provided CONTEXT. If the context does not contain \
the answer, say so plainly and suggest the person ask their care team, instead of guessing.
- Never provide a diagnosis for the person you are talking to, never suggest a medication, \
dose, or dose change, and never tell them to start, stop, or adjust any treatment.
- Use warm, plain, non-clinical language. Keep answers concise and easy to read.
- Always gently remind the person that this is educational information, not a substitute \
for care from a licensed clinician, when the topic involves symptoms, treatment, or crisis.
- If anything in the conversation suggests the person may be in crisis (suicidal ideation, \
self-harm, intent to harm others, or a severe manic/psychotic episode with safety risk), \
do not continue with general education. Respond with care, encourage them to contact \
emergency services or a crisis line right now, and keep the tone calm and supportive.
- CITATIONS: Each source in CONTEXT is numbered, e.g. "[Source 2: ...]". In your answer, cite \
    it using ONLY the compact form "[2]"; never write "[Source 2]" or invent a citation number. \
    Whenever you state a \
fact drawn from a source, add a bracket citation with that number right after the sentence, \
like this: "...increased energy or activity [2]." Use multiple brackets like [1][3] if a \
sentence draws on more than one source. Only cite sources you actually used — do not cite a \
source you didn't rely on. Do not explain the citation system to the user, just use it.
"""

DOCTOR_SYSTEM_PROMPT = """You are Dr. Mood, an AI assistant that surfaces clinically precise \
information about bipolar disorder from the approved clinical source excerpts provided in the \
CONTEXT block, for a clinician audience.

Rules:
- ALWAYS reply in the same language the person used for their question (for example, if they \
wrote in Arabic, reply entirely in Arabic, translating relevant clinical content from the \
English CONTEXT naturally — do not mix languages within a reply). Keep standard clinical terms \
(drug names, DSM/ICD codes) in their usual form even in an Arabic reply.
- Base every factual claim strictly on the provided CONTEXT. If the context is insufficient, \
say so explicitly rather than filling gaps from general knowledge.
- You may use standard clinical terminology (DSM-style criteria, mood-episode nomenclature, etc).
- You are a reference/education tool, not a decision-support system: do not issue a diagnosis \
or a treatment plan for a named patient, and do not recommend specific doses. You can describe \
what the source material says about diagnostic criteria or treatment classes in general terms.
- Be concise and structured (short paragraphs or bullet points are fine).
- CITATIONS: Each source in CONTEXT is numbered, e.g. "[Source 2: ...]". In your answer, cite \
    it using ONLY the compact form "[2]"; never write "[Source 2]" or invent a citation number. \
    Whenever you state a \
fact drawn from a source, add a bracket citation with that number right after the sentence, \
like this: "...increased energy or activity [2]." Use multiple brackets like [1][3] if a \
sentence draws on more than one source. Only cite sources you actually used — do not cite a \
source you didn't rely on. Do not explain the citation system to the user, just use it.
"""


def build_context_block(chunks: list[dict]) -> str:
    if not chunks:
        return "No relevant approved source material was found for this question."
    parts = []
    for c in chunks:
        idx = c.get("index", "?")
        section = f", Section {c['section']}" if c.get("section") else ""
        parts.append(f"[Source {idx}: {c['title']}{section} ({c['category']}, p. {c['page']})]\n{c['text']}")
    return "\n\n".join(parts)


def _convert_history(history: list[dict]) -> list[dict]:
    """Gemini بيتوقع role='model' بدل 'assistant'، وبيتوقع الرسالة جوه list اسمها parts."""
    converted = []
    for m in history:
        role = "model" if m["role"] == "assistant" else "user"
        converted.append({"role": role, "parts": [m["content"]]})
    return converted


def generate_answer(role: str, question: str, context_chunks: list[dict], history: list[dict]) -> str:
    if not settings.gemini_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it to your .env file to enable answer generation."
        )

    system_prompt = DOCTOR_SYSTEM_PROMPT if role == "doctor" else PATIENT_SYSTEM_PROMPT
    context_block = build_context_block(context_chunks)

    model = genai.GenerativeModel(
        model_name=settings.llm_model,
        system_instruction=system_prompt,
    )

    chat = model.start_chat(history=_convert_history(history))

    response = chat.send_message(
        f"CONTEXT:\n{context_block}\n\nQUESTION:\n{question}",
        request_options={"timeout": 120},
    )
    
    return response.text.strip()
def translate_to_english(text: str) -> str:
    """ترجمة سريعة للعربي للإنجليزي وقت البحث بس، مش بتتغيّر لغة الرد للمستخدم."""
    if not settings.gemini_api_key:
        return text
    try:
        model = genai.GenerativeModel(model_name=settings.llm_model)
        response = model.generate_content(
            f"Translate this to English. Return ONLY the translation, nothing else:\n{text}"
        )
        return response.text.strip()
    except Exception:
        return text