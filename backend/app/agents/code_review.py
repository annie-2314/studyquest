"""Code-Review agent: reviews student code for correctness, style, and gives
suggestions, and decides whether it passes (used to gate coding-course steps)."""
from __future__ import annotations

from app.agents import llm as llm_mod

_SYSTEM = (
    "You are StudyQuest's Code Reviewer. Review the student's code for: "
    "(1) correctness vs. the task, (2) style/readability, (3) concrete "
    "improvement suggestions. Be encouraging and specific. End your reply with "
    "a final line that is EXACTLY 'VERDICT: PASS' or 'VERDICT: NEEDS_WORK'."
)


def review_code(language: str, code: str, run_result: dict, task: str = "") -> dict:
    model = llm_mod.get_llm(llm_mod.SMART)
    run_summary = (f"exit={run_result.get('exit_code')} "
                   f"timed_out={run_result.get('timed_out')}\n"
                   f"stdout:\n{run_result.get('stdout','')}\n"
                   f"stderr:\n{run_result.get('stderr','')}")
    if model is None:
        approved = bool(run_result.get("ok"))
        verdict = "PASS" if approved else "NEEDS_WORK"
        return {
            "review": (f"🔧 (mock code review) The code "
                       f"{'ran successfully' if approved else 'did not run cleanly'}.\n{run_summary}\n"
                       "Add an OPENROUTER_API_KEY for a full correctness/style review.\n"
                       f"VERDICT: {verdict}"),
            "approved": approved,
        }
    msgs = [("system", _SYSTEM),
            ("user", f"Task: {task or '(none given)'}\nLanguage: {language}\n\n"
                     f"Code:\n```\n{code}\n```\n\nExecution result:\n{run_summary}")]
    review = model.invoke(msgs).content
    approved = "VERDICT: PASS" in review.upper()
    return {"review": review, "approved": approved}
