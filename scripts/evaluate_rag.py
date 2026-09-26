"""
RAG Evaluation Script
=====================
Evaluates retrieval quality and answer correctness against a golden test set.

Usage:
    python scripts/evaluate_rag.py

Requires:
    - Running PostgreSQL with indexed documents
    - Valid LLM API key in .env
"""
import asyncio
import json
import sys
import time
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

# Golden test set — questions with expected source documents
# Replace with real evaluation data based on actual documents in your KB
GOLDEN_DATASET = [
    {
        "id": "Q001",
        "question": "What is the minimum attendance required for semester exams?",
        "expected_keywords": ["75%", "attendance", "eligible"],
        "expected_source_contains": "attendance",
        "category": "policy",
    },
    {
        "id": "Q002",
        "question": "What departments are available at WCE?",
        "expected_keywords": ["computer", "mechanical", "civil"],
        "expected_source_contains": "department",
        "category": "general",
    },
    {
        "id": "Q003",
        "question": "How do I apply for a scholarship?",
        "expected_keywords": ["scholarship", "apply", "portal"],
        "expected_source_contains": "scholarship",
        "category": "scholarship",
    },
    {
        "id": "Q004",
        "question": "What is the grading system at WCE?",
        "expected_keywords": ["CGPA", "grade", "credits"],
        "expected_source_contains": "grading",
        "category": "academic",
    },
    {
        "id": "Q005",
        "question": "Tell me about the hostel facilities",
        "expected_keywords": ["hostel", "rooms", "mess"],
        "expected_source_contains": "hostel",
        "category": "facilities",
    },
]


def evaluate_answer(answer: str, expected_keywords: list[str]) -> dict:
    """Evaluate answer quality based on keyword presence."""
    answer_lower = answer.lower()
    found = [kw for kw in expected_keywords if kw.lower() in answer_lower]
    precision = len(found) / len(expected_keywords) if expected_keywords else 0

    return {
        "keyword_coverage": precision,
        "found_keywords": found,
        "missing_keywords": [kw for kw in expected_keywords if kw not in found],
    }


def evaluate_citations(citations: list[dict], expected_source_contains: str) -> dict:
    """Check if citations include the expected source document."""
    if not citations:
        return {"has_citation": False, "source_found": False}

    source_found = any(
        expected_source_contains.lower() in (c.get("document_title", "")).lower()
        for c in citations
    )

    return {
        "has_citation": True,
        "citation_count": len(citations),
        "source_found": source_found,
        "avg_similarity": sum(c.get("similarity_score", 0) for c in citations) / len(citations),
    }


async def run_evaluation():
    """Run the evaluation pipeline against the golden dataset."""
    print("=" * 60)
    print("WalchandGPT RAG Evaluation")
    print("=" * 60)
    print(f"Evaluating {len(GOLDEN_DATASET)} questions\n")

    results = []
    total_latency = 0

    for item in GOLDEN_DATASET:
        print(f"[{item['id']}] {item['question'][:60]}...")

        # NOTE: In a real evaluation, you would call the actual API endpoint
        # This is a structural evaluation script — connect to running backend
        # to get real answers.
        #
        # Example with httpx:
        # import httpx
        # async with httpx.AsyncClient() as client:
        #     resp = await client.post(
        #         "http://localhost:8000/api/chat/stream",
        #         headers={"Authorization": f"Bearer {TOKEN}"},
        #         json={"message": item["question"]}
        #     )
        #
        # For now, log a placeholder result
        result = {
            "id": item["id"],
            "question": item["question"],
            "category": item["category"],
            "status": "TODO: Connect to running backend for real evaluation",
            "answer_evaluation": None,
            "citation_evaluation": None,
            "latency_ms": None,
        }

        results.append(result)
        print(f"  → {result['status']}")

    print("\n" + "=" * 60)
    print("Evaluation Complete")
    print("=" * 60)
    print(f"Total questions: {len(results)}")
    print("\nTo run a real evaluation:")
    print("  1. Start the backend: docker compose up")
    print("  2. Index documents via admin dashboard")
    print("  3. Update this script with a real API token")
    print("  4. Uncomment the httpx calls above")

    # Save results
    output_path = Path(__file__).parent / "evaluation_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(run_evaluation())
