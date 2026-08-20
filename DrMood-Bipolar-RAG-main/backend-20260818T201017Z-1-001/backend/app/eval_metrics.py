"""
تقييم فعلي بيشتغل على نفس الـ vector store اللي الباك إند بتاع الإنتاج بيستخدمه
(app/services/vector_store.py)، مش على سكريبت الكولاب القديم (src/evaluate.py)
اللي كان بيشتغل على chroma_db منفصلة تمامًا وموديل embedding مختلف.

بيحسب:
  1. Precision@k (k = 3, 5, 10) — هل الـ section الصح ظهر في النتائج المسترجَعة
  2. Refusal correctness — هل النظام رفض صح للأسئلة اللي مفروض يرفضها (Not covered)
  3. متوسط أعلى score لكل سؤال (Confidence signal)

وبيحفظ كل حاجة في backend/eval_logs/eval_<timestamp>.json — ده الـ "evaluation log"
المطلوب في Day 4 Readiness Scorecard.

الشغل:
    cd backend
    python -m app.eval_metrics
"""
import json
import re
import time
from pathlib import Path

from app.services import vector_store
from app.config import settings

LOG_DIR = Path(__file__).resolve().parents[1] / "eval_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# نفس أسئلة الـ Day 2 (من src/evaluate.py) — كل سؤال مربوط برقم section الصح المتوقع
# من data/all_chunks.json (اللي عملها src/ingest.py على NICE CG185)
TEST_QUESTIONS = [
    {"question": "What are the diagnostic criteria for bipolar disorder?", "expected_section": "2.3.1"},
    {"question": "How is bipolar disorder distinguished from other diagnoses?", "expected_section": "2.3.3"},
    {"question": "What comorbidities are associated with bipolar disorder?", "expected_section": "2.3.5"},
    {"question": "What are the early warning signs of bipolar disorder relapse?", "expected_section": "2.5.1"},
    {"question": "What written information should be given to carers?", "expected_section": "1.1.14"},
    {"question": "What themes did carers identify as improving their experience?", "expected_section": "4.2.2"},
    {"question": "What should happen immediately after a patient assessment?", "expected_section": "5.4"},
    {"question": "What are the clinical practice recommendations for case identification?", "expected_section": "5.6.1"},
    {"question": "What medication is recommended for acute mania?", "expected_section": "6.1"},
    {"question": "What did the network meta-analysis find about pharmacological interventions?", "expected_section": "6.3.4"},
    {"question": "What nutritional interventions help with acute bipolar episodes?", "expected_section": "6.3.7"},
    {"question": "What is the trade-off between clinical benefits and harms in long-term management?", "expected_section": "7.5.2"},
    {"question": "What are the research recommendations for long-term bipolar management?", "expected_section": "7.6.2"},
    {"question": "What is the clinical evidence for psychological interventions?", "expected_section": "8.1.3"},
    {"question": "What clinical practice recommendations exist for monitoring physical health?", "expected_section": "9.4.1"},
    {"question": "What health economics evidence exists for treating children with bipolar disorder?", "expected_section": "10.4.5"},
    {"question": "What is the risk of bias in studies on children and young people with bipolar disorder?", "expected_section": "10.3.4"},
    {"question": "How should mania or hypomania be managed in adults?", "expected_section": "11.5"},
    {"question": "How should medication be used for bipolar disorder?", "expected_section": "11.10"},
]

# أسئلة المفروض النظام يرفضها (برا نطاق الدليل الإرشادي تمامًا) — لاختبار الـ refusal logic
REFUSAL_TEST_QUESTIONS = [
    "What is the best pizza topping?",
    "How do I fix my car's brakes?",
    "What is the capital of France?",
    "Should I invest in cryptocurrency?",
]

# نفس الـ 19 سؤال بالظبط بس بالعربي، عشان نتحقق إن الـ retrieval بيلاقي نفس
# الـ sections الصح حتى لو السؤال جه بلغة تانية غير لغة الدليل (إنجليزي).
# ده أهم اختبار قبل ما نقول إن البوت "بيفهم كويس بالعربي".
ARABIC_TEST_QUESTIONS = [
    {"question": "ما هي معايير تشخيص اضطراب ثنائي القطب؟", "expected_section": "2.3.1"},
    {"question": "كيف يتم تمييز اضطراب ثنائي القطب عن التشخيصات الأخرى؟", "expected_section": "2.3.3"},
    {"question": "ما هي الأمراض المصاحبة المرتبطة باضطراب ثنائي القطب؟", "expected_section": "2.3.5"},
    {"question": "ما هي العلامات المبكرة لانتكاسة اضطراب ثنائي القطب؟", "expected_section": "2.5.1"},
    {"question": "ما المعلومات المكتوبة التي يجب تقديمها لمقدمي الرعاية؟", "expected_section": "1.1.14"},
    {"question": "ما المحاور التي حددها مقدمو الرعاية لتحسين تجربتهم؟", "expected_section": "4.2.2"},
    {"question": "ماذا يجب أن يحدث مباشرة بعد تقييم المريض؟", "expected_section": "5.4"},
    {"question": "ما هي توصيات الممارسة السريرية لتحديد الحالات؟", "expected_section": "5.6.1"},
    {"question": "ما هو الدواء الموصى به لنوبة الهوس الحادة؟", "expected_section": "6.1"},
    {"question": "ماذا وجد التحليل التلوي الشبكي بخصوص التدخلات الدوائية؟", "expected_section": "6.3.4"},
    {"question": "ما هي التدخلات الغذائية التي تساعد في نوبات ثنائي القطب الحادة؟", "expected_section": "6.3.7"},
    {"question": "ما هي المفاضلة بين الفوائد والأضرار السريرية في الإدارة طويلة المدى؟", "expected_section": "7.5.2"},
    {"question": "ما هي توصيات البحث للإدارة طويلة المدى لثنائي القطب؟", "expected_section": "7.6.2"},
    {"question": "ما هو الدليل السريري على التدخلات النفسية؟", "expected_section": "8.1.3"},
    {"question": "ما هي توصيات الممارسة السريرية لمراقبة الصحة الجسدية؟", "expected_section": "9.4.1"},
    {"question": "ما الأدلة الاقتصادية الصحية بخصوص علاج الأطفال المصابين بثنائي القطب؟", "expected_section": "10.4.5"},
    {"question": "ما هو خطر التحيز في الدراسات الخاصة بالأطفال واليافعين المصابين بثنائي القطب؟", "expected_section": "10.3.4"},
    {"question": "كيف تتم إدارة الهوس أو الهوس الخفيف لدى البالغين؟", "expected_section": "11.5"},
    {"question": "كيف يجب استخدام الدواء لعلاج اضطراب ثنائي القطب؟", "expected_section": "11.10"},
]

# doc_id بييجي من seed_nice.py بالصيغة: ch<chapter>_<section_number>_<index>  مثال: ch02_2.1_002
SECTION_FROM_DOC_ID = re.compile(r"^ch\d+_([\d.]+)_")


def extract_section(doc_id: str) -> str | None:
    m = SECTION_FROM_DOC_ID.match(doc_id or "")
    return m.group(1) if m else None


def evaluate_precision_at_k(k_values=(3, 5, 10), questions=None) -> dict:
    questions = questions if questions is not None else TEST_QUESTIONS
    results_summary = {}
    for k in k_values:
        correct = 0
        details = []
        for tq in questions:
            raw = vector_store.query(tq["question"], top_k=k)
            retrieved_sections = [extract_section(r.get("doc_id", "")) for r in raw]
            # fallback: doc_id مش راجع من query() النهارده — لو كده هنحتاج نضيفه (شوفي الملاحظة تحت)
            found = tq["expected_section"] in retrieved_sections
            correct += int(found)
            details.append({
                "question": tq["question"],
                "expected": tq["expected_section"],
                "retrieved": retrieved_sections,
                "top_score": raw[0]["score"] if raw else None,
                "found": found,
            })
        precision = correct / len(questions)
        results_summary[k] = {
            "precision": round(precision, 4),
            "correct": correct,
            "total": len(questions),
            "details": details,
        }
    return results_summary


def evaluate_refusals() -> dict:
    """للأسئلة البعيدة تمامًا عن الدليل، أعلى score المفروض يبقى تحت retrieval_min_score."""
    results = []
    correct = 0
    for q in REFUSAL_TEST_QUESTIONS:
        raw = vector_store.query(q, top_k=3)
        top_score = raw[0]["score"] if raw else 0.0
        should_refuse = top_score < settings.retrieval_min_score
        correct += int(should_refuse)
        results.append({"question": q, "top_score": top_score, "correctly_refused": should_refuse})
    return {
        "precision": round(correct / len(REFUSAL_TEST_QUESTIONS), 4),
        "correct": correct,
        "total": len(REFUSAL_TEST_QUESTIONS),
        "details": results,
        "threshold_used": settings.retrieval_min_score,
    }


def main():
    print("=== Precision@k (against LIVE backend vector store) ===")
    precision_results = evaluate_precision_at_k()
    for k, res in precision_results.items():
        print(f"Precision@{k}: {res['precision']:.2%} ({res['correct']}/{res['total']})")
        for d in res["details"]:
            if not d["found"]:
                print(f"  ❌ {d['question']}  expected={d['expected']} got={d['retrieved']}")

    print("\n=== Cross-lingual (Arabic) Precision@k — same questions, translated ===")
    arabic_results = evaluate_precision_at_k(questions=ARABIC_TEST_QUESTIONS)
    for k, res in arabic_results.items():
        print(f"Precision@{k} (AR): {res['precision']:.2%} ({res['correct']}/{res['total']})")
        for d in res["details"]:
            if not d["found"]:
                print(f"  ❌ {d['question']}  expected={d['expected']} got={d['retrieved']}")
    ar_scores = [d["top_score"] for d in arabic_results[3]["details"] if d["top_score"] is not None]
    if ar_scores:
        below_threshold = [s for s in ar_scores if s < settings.retrieval_min_score]
        print(f"\nArabic top_score range: {min(ar_scores):.3f} - {max(ar_scores):.3f} "
              f"(threshold={settings.retrieval_min_score})")
        if below_threshold:
            print(f"⚠️  {len(below_threshold)}/{len(ar_scores)} Arabic questions score BELOW the "
                  f"threshold — these would be wrongly refused even though they're in scope.")
        else:
            print("✅ All Arabic questions clear the threshold — cross-lingual retrieval looks safe.")

    print("\n=== Refusal correctness (out-of-scope questions) ===")
    refusal_results = evaluate_refusals()
    print(f"Correctly refused: {refusal_results['precision']:.2%} "
          f"({refusal_results['correct']}/{refusal_results['total']}) "
          f"at threshold={refusal_results['threshold_used']}")
    for d in refusal_results["details"]:
        status = "✅" if d["correctly_refused"] else "❌ (should have refused)"
        print(f"  {status} score={d['top_score']:.3f}  \"{d['question']}\"")

    log = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "embedding_model": settings.embedding_model,
        "retrieval_min_score": settings.retrieval_min_score,
        "collection_count": vector_store.collection_count(),
        "precision_at_k": precision_results,
        "precision_at_k_arabic": arabic_results,
        "refusal_evaluation": refusal_results,
    }
    log_path = LOG_DIR / f"eval_{time.strftime('%Y%m%d_%H%M%S')}.json"
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n📝 Evaluation log saved to: {log_path}")


if __name__ == "__main__":
    main()