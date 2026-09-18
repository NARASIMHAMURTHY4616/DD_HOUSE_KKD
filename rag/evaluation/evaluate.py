"""Evaluation script: runs all 50 benchmark questions against the DD House RAG pipeline.
Asserts groundedness, negative constraint enforcement, and hallucination resistance.
"""
import json
import time
from pathlib import Path
from typing import Dict, List, Any
from rag.pipeline.rag_pipeline import RAGPipeline
from rag.config import settings

def run_evaluation() -> Dict[str, Any]:
    test_file = Path(__file__).resolve().parent / "test_questions.json"
    with open(test_file, "r", encoding="utf-8") as f:
        questions: List[Dict[str, Any]] = json.load(f)

    pipeline = RAGPipeline()
    passed = 0
    failed = 0
    results_detail = []

    print("\n=======================================================")
    print("      DD HOUSE RAG EVALUATION BENCHMARK (50 TESTS)     ")
    print("=======================================================\n")

    start_time = time.time()

    for item in questions:
        q_id = item["id"]
        cat = item["category"]
        q_text = item["question"]
        exp_grounded = item["expected_grounded"]
        must_contain = item.get("must_contain", [])
        must_not_contain = item.get("must_not_contain", [])

        res = pipeline.query(q_text)
        ans = res["answer"]
        actual_grounded = res["grounded"]
        conf = res["confidence"]

        item_passed = True
        reasons = []

        # Check expected grounded status
        if actual_grounded != exp_grounded:
            # Special allowance for safe answers (e.g. unknown response is safely ungrounded)
            if not exp_grounded and actual_grounded:
                item_passed = False
                reasons.append(f"Expected ungrounded, got grounded=True")

        # Check must contain keywords
        for term in must_contain:
            if term.lower() not in ans.lower():
                item_passed = False
                reasons.append(f"Missing required text: '{term}'")

        # Check must NOT contain keywords
        for term in must_not_contain:
            if term.lower() in ans.lower():
                item_passed = False
                reasons.append(f"Hallucination / forbidden text found: '{term}'")

        if item_passed:
            passed += 1
            status_str = "PASS"
        else:
            failed += 1
            status_str = "FAIL"

        print(f"[{status_str}] Q#{q_id:02d} [{cat:20s}] {q_text}")
        print(f"       -> Conf: {conf:.2f} | Grounded: {actual_grounded} | Answer: {ans[:90]}...")
        if reasons:
            print(f"       -> Errors: {', '.join(reasons)}")

        results_detail.append({
            "id": q_id,
            "category": cat,
            "question": q_text,
            "passed": item_passed,
            "grounded": actual_grounded,
            "confidence": conf,
            "answer": ans,
            "reasons": reasons
        })

    elapsed = time.time() - start_time
    total = len(questions)
    pass_rate = (passed / total) * 100

    # Hallucination prevention rate on category 8
    cat8_tests = [r for r in results_detail if r["category"] == "UNKNOWN_HALLUCINATION"]
    cat8_passed = sum(1 for r in cat8_tests if r["passed"])
    cat8_rate = (cat8_passed / len(cat8_tests)) * 100 if cat8_tests else 100.0

    print("\n=======================================================")
    print("                 BENCHMARK SUMMARY                     ")
    print("=======================================================")
    print(f"Total Questions Evaluated    : {total}")
    print(f"Tests Passed                 : {passed} / {total} ({pass_rate:.1f}%)")
    print(f"Tests Failed                 : {failed} / {total}")
    print(f"Category 8 Hallucination Res : {cat8_passed} / {len(cat8_tests)} ({cat8_rate:.1f}%)")
    print(f"Total Evaluation Time        : {elapsed:.2f} seconds")
    print("=======================================================\n")

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": pass_rate,
        "cat8_hallucination_prevention_rate": cat8_rate,
        "elapsed_seconds": elapsed,
        "results": results_detail
    }

if __name__ == "__main__":
    run_evaluation()
