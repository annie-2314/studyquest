"""Evaluation harness.

Two measurements the brief asks for:
  1. Explanation quality — an LLM-as-judge scores clarity / correctness / example
     presence on a 1-5 scale.
  2. Quiz improvement — whether a learner's quiz pass-rate trends upward over time.

Mock-safe: with no API key the judge returns a deterministic heuristic score so
the harness still runs end-to-end.
"""
from __future__ import annotations

import json
import re

from sqlalchemy.orm import Session

from app.agents import llm as llm_mod
from app.agents.supervisor import run_turn
from app.models.course import Course, CourseStep

# A tiny built-in dataset for the explanation eval.
SAMPLE_PROMPTS = [
    "Explain recursion to a beginner.",
    "What is photosynthesis?",
    "Explain how a for-loop works.",
]


def judge_explanation(question: str, answer: str) -> dict:
    """Score an explanation 1-5 with a rationale."""
    model = llm_mod.get_llm(llm_mod.SMART)
    if model is None:
        # Heuristic: reward length + presence of an example keyword.
        has_example = any(k in answer.lower() for k in ("example", "for instance", "imagine", "like when"))
        score = 3 + (1 if len(answer) > 200 else 0) + (1 if has_example else 0)
        return {"score": min(score, 5), "rationale": "Heuristic score (no judge LLM configured)."}
    msgs = [("system", "You are an evaluation judge. Score the explanation from 1-5 on clarity, "
                       "correctness, and whether it includes a real-life example. Output JSON "
                       '{"score": <1-5>, "rationale": "<one sentence>"} only.'),
            ("user", f"Question: {question}\n\nExplanation:\n{answer}")]
    m = re.search(r"\{.*\}", model.invoke(msgs).content, flags=re.DOTALL)
    if not m:
        return {"score": 3, "rationale": "Could not parse judge output."}
    try:
        obj = json.loads(m.group(0))
        return {"score": int(obj.get("score", 3)), "rationale": str(obj.get("rationale", ""))}
    except (json.JSONDecodeError, ValueError):
        return {"score": 3, "rationale": "Could not parse judge output."}


def run_explanation_eval(prompts: list[str] | None = None) -> dict:
    """Generate explanations via the tutor and judge each. Returns per-item +
    average score — the core 'does the tutor explain well' metric."""
    prompts = prompts or SAMPLE_PROMPTS
    results = []
    for p in prompts:
        answer = run_turn("eval-user", [], p, "Evaluation run.")["answer"]
        verdict = judge_explanation(p, answer)
        results.append({"prompt": p, "score": verdict["score"], "rationale": verdict["rationale"]})
    avg = round(sum(r["score"] for r in results) / len(results), 2) if results else 0
    return {"average_score": avg, "n": len(results), "results": results}


def _parse_json(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def judge_factuality(answer: str, sources: list[str]) -> dict:
    """Score how well an answer is grounded in the provided source chunks
    (0..1). Detects hallucination = claims not supported by the sources."""
    src = "\n\n".join(f"[{i + 1}] {s}" for i, s in enumerate(sources))
    model = llm_mod.get_llm(llm_mod.SMART)
    if model is None or not sources:
        # Heuristic: fraction of answer words that appear in the sources.
        words = re.findall(r"[a-z0-9]{4,}", answer.lower())
        joined = " ".join(sources).lower()
        overlap = sum(1 for w in set(words) if w in joined)
        score = round(overlap / max(len(set(words)), 1), 2) if words else 0.0
        return {"score": score, "grounded": score >= 0.5,
                "rationale": "Heuristic lexical-overlap score (no judge LLM / no sources)."}
    msgs = [("system", "You are a factuality judge. Given SOURCES and an ANSWER, decide whether "
                       "every claim in the answer is supported by the sources. Output JSON only: "
                       '{"score": <0..1 grounded fraction>, "grounded": <true|false>, '
                       '"rationale": "<one sentence; name any unsupported claim>"}.'),
            ("user", f"SOURCES:\n{src}\n\nANSWER:\n{answer}")]
    obj = _parse_json(model.invoke(msgs).content) or {}
    try:
        score = float(obj.get("score", 0.0))
    except (TypeError, ValueError):
        score = 0.0
    return {"score": round(min(max(score, 0.0), 1.0), 2),
            "grounded": bool(obj.get("grounded", score >= 0.5)),
            "rationale": str(obj.get("rationale", ""))}


def judge_quiz_validity(question: str, options: list[str], answer_index: int) -> dict:
    """Score whether a multiple-choice item is well-formed: exactly one clearly
    correct option, plausible distractors (0..1)."""
    model = llm_mod.get_llm(llm_mod.SMART)
    if model is None:
        ok = bool(question.strip()) and len(options) >= 2 and 0 <= answer_index < len(options)
        return {"score": 1.0 if ok else 0.0, "valid": ok,
                "rationale": "Structural check (no judge LLM configured)."}
    opts = "\n".join(f"{i}. {o}" for i, o in enumerate(options))
    msgs = [("system", "You are a quiz-validity judge. Decide if the item has exactly one correct "
                       "option (the marked index), unambiguous wording, and plausible distractors. "
                       'Output JSON only: {"score": <0..1>, "valid": <bool>, "rationale": "<one sentence>"}.'),
            ("user", f"Question: {question}\nOptions:\n{opts}\nMarked correct index: {answer_index}")]
    obj = _parse_json(model.invoke(msgs).content) or {}
    try:
        score = float(obj.get("score", 0.0))
    except (TypeError, ValueError):
        score = 0.0
    return {"score": round(min(max(score, 0.0), 1.0), 2),
            "valid": bool(obj.get("valid", score >= 0.5)),
            "rationale": str(obj.get("rationale", ""))}


def quiz_improvement(db: Session, user_id: str) -> dict:
    """Compare the learner's quiz pass-rate in the first vs second half of their
    course steps (ordinal order) as a simple improvement signal."""
    steps = (db.query(CourseStep).join(Course)
             .filter(Course.user_id == user_id).order_by(CourseStep.ordinal).all())
    if len(steps) < 2:
        return {"enough_data": False, "first_half": None, "second_half": None, "improved": None}
    mid = len(steps) // 2
    first = steps[:mid]
    second = steps[mid:]
    fr = sum(1 for s in first if s.quiz_passed) / len(first)
    sr = sum(1 for s in second if s.quiz_passed) / len(second)
    return {"enough_data": True, "first_half": round(fr, 2), "second_half": round(sr, 2),
            "improved": sr >= fr}
