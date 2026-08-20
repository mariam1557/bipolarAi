from config import EVAL_XLSX_PATH
from rag import search

# نفس أسئلة الـ Precision@k 
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


def evaluate_precision_at_k(test_questions, k_values=(3, 5, 10)):
    results_summary = {}
    for k in k_values:
        correct = 0
        details = []
        for tq in test_questions:
            search_results = search(tq["question"], n_results=k)
            retrieved_sections = [meta["section_number"] for meta in search_results["metadatas"][0]]
            found = tq["expected_section"] in retrieved_sections
            correct += int(found)
            details.append({"question": tq["question"], "expected": tq["expected_section"],
                           "retrieved": retrieved_sections, "found": found})
        precision = correct / len(test_questions)
        results_summary[k] = {"precision": precision, "correct": correct, "total": len(test_questions), "details": details}
    return results_summary


def main():
    print("=== Precision@k Evaluation 📊 ===")
    eval_results = evaluate_precision_at_k(TEST_QUESTIONS)
    for k, res in eval_results.items():
        print(f"Precision@{k}: {res['precision']:.2%} ({res['correct']}/{res['total']})")

    print("\n=== Questions failed in Precision@3 ❌ ===")
    for d in eval_results[3]["details"]:
        if not d["found"]:
            print(f"❌ {d['question']}")
            print(f"   Expected: {d['expected']} | Retrieved: {d['retrieved']}")


if __name__ == "__main__":
    main()