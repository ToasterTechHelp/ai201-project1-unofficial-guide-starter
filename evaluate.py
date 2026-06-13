"""Milestone 6 — Evaluation harness.

Runs the 5 planning.md test questions end-to-end and prints, for each:
the answer, the sources used, and the retrieved chunks with distances — the
raw material for the README Evaluation Report. Accuracy verdicts are left to
the human (that's the point of the exercise).

Run:  python evaluate.py
"""

from query import ask

# The 5 evaluation questions from planning.md (Q5 is the designed-to-fail,
# layout-dependent line lookup).
EVAL_QUESTIONS = [
    "What is Schedule C (Form 1040) used for?",
    "What does an employer report on Form 941?",
    "What expenses does Form 8829 calculate?",
    "What is the Texas form 01-114?",
    "What value goes on Line 31 of Schedule C?",
]


def main() -> None:
    for n, q in enumerate(EVAL_QUESTIONS, 1):
        result = ask(q)
        print(f"\n{'#' * 90}\nQ{n}: {q}\n{'#' * 90}")
        print(f"\nANSWER:\n{result['answer']}")
        print(f"\nSOURCES USED: {result['sources'] or '(none)'}")
        print("\nRETRIEVED CHUNKS (source#index | distance):")
        for r in result["chunks"]:
            preview = r["text"].replace("\n", " ")[:140]
            print(f"  {r['source']}#{r['chunk_index']:<3} | {r['distance']:.3f} | {preview}")


if __name__ == "__main__":
    main()
