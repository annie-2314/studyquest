"""CLI evaluation harness.

Run from backend/:  python -m scripts.run_eval
Generates tutor explanations for a built-in prompt set and scores them with an
LLM-as-judge (heuristic fallback if no OPENROUTER_API_KEY). Prints a report."""
from app.eval.harness import run_explanation_eval


def main() -> None:
    report = run_explanation_eval()
    print("=" * 60)
    print("StudyQuest AI — Explanation Quality Eval")
    print("=" * 60)
    for r in report["results"]:
        print(f"\n[{r['score']}/5] {r['prompt']}")
        print(f"     judge: {r['rationale']}")
    print("\n" + "-" * 60)
    print(f"Average score: {report['average_score']}/5 over {report['n']} prompts")


if __name__ == "__main__":
    main()
