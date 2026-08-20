
"""
بيدور على أسماء الأدوية العلمية (generic names) جوه نص إجابة الشات بوت،
ويضيف جنب أول ذكر لكل دواء اسمه التجاري الشائع في السوق المصري.

⚠️ راجعي القايمة دي مع صيدلي/طبيب بشكل دوري — الأسماء التجارية والتوفر
في السوق بيتغيروا، والقايمة دي بس بداية مش مرجع نهائي.
"""
import re

EGYPT_DRUG_NAMES: dict[str, list[str]] = {
    "lithium": ["Prianil C.R."],
    "lithium carbonate": ["Prianil C.R."],
    "sodium valproate": ["Depakine", "Depakine Chrono"],
    "valproate": ["Depakine", "Depakine Chrono"],
    "valproic acid": ["Depakine"],
    "olanzapine": ["Zyprexa", "Olapex", "Ranxapin"],
    "quetiapine": ["Seroquel", "Spiraquet"],
    "risperidone": ["Risperdal"],
    "haloperidol": ["Haldol"],
    "lamotrigine": ["Lamictal"],
    "carbamazepine": ["Tegretol"],
    "aripiprazole": ["Abilify"],
}

# بنرتب الأسماء من الأطول للأقصر عشان الـ regex ياخد "sodium valproate"
# كامل بدل ما ياخد "valproate" بس ويقطع الجملة غلط
_SORTED_NAMES = sorted(EGYPT_DRUG_NAMES, key=len, reverse=True)
_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(name) for name in _SORTED_NAMES) + r")\b",
    re.IGNORECASE,
)


def add_egyptian_brand_names(text: str) -> str:
    """
    بترجع نفس النص بعد ما تضيف الاسم التجاري المصري جنب أول ذكر لكل دواء معروف.
    لو النص مفيهوش أي دواء من القايمة، بترجعه زي ما هو من غير أي تعديل.
    """
    if not text:
        return text

    already_annotated: set[str] = set()

    def _replace(match: re.Match) -> str:
        matched_text = match.group(0)
        key = matched_text.lower()
        if key in already_annotated:
            return matched_text  # بس أول ذكر للدواء، مش كل مرة يتكرر فيها
        already_annotated.add(key)

        brands = EGYPT_DRUG_NAMES.get(key)
        if not brands:
            return matched_text

        brand_str = " / ".join(brands)
        return f"{matched_text} (known in Egypt as: {brand_str})"

    return _PATTERN.sub(_replace, text)