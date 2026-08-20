"""
Very small keyword-based safety net. This is NOT a substitute for a proper
clinical triage system — it only exists to make sure a crisis-flag reaches
the frontend so it can surface crisis resources immediately, even while the
main LLM response is also being generated with crisis-aware instructions.
"""

_CRISIS_PATTERNS = [
    # English
    "suicide", "kill myself", "end my life", "want to die", "self harm",
    "self-harm", "hurt myself", "hurting myself", "no reason to live",
    "better off dead", "can't go on", "cant go on",
    # Arabic (فصحى ومصري عامية)
    "انتحار", "عايز اموت", "عايزة اموت", "نفسي اموت", "عاوز اموت", "عاوزة اموت",
    "هقتل نفسي", "هموت نفسي", "اقتل نفسي", "اذي نفسي", "بأذي نفسي",
    "مش عايز اعيش", "مش عايزة اعيش", "مفيش داعي اعيش", "مفيش فايدة اني اعيش",
    "أحسن لو موت", "احسن لو موت", "مش قادر استحمل", "مش قادرة استحمل",
    "مش قادر اكمل", "مش قادرة اكمل", "تعبت من الدنيا",
]


def is_potential_crisis(text: str) -> bool:
    lowered = text.lower()
    return any(p in lowered for p in _CRISIS_PATTERNS)
