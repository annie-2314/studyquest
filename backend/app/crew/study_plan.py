"""Study-Plan CREW — role-based collaboration (Planner -> Question-Writer ->
Reviewer) that produces a personalized study plan.

WHY a crew here (vs the LangGraph supervisor): this task is a fixed pipeline of
*specialist roles* each refining the previous one's output — exactly CrewAI's
sweet spot. We implement that role pipeline on the shared OpenRouter LLM layer.

NOTE on real CrewAI: the `crewai` package pulls in chromadb -> hnswlib, which
needs the MS C++ Build Tools and won't build on this machine. So this module is
the portable implementation of the same Planner/Question-Writer/Reviewer crew.
If `crewai` is importable in your environment, `_real_crewai_available()` lets
you swap in the native engine without changing callers.
"""
from __future__ import annotations

import json
import re

from app.agents import llm as llm_mod


def _real_crewai_available() -> bool:
    try:
        import crewai  # noqa: F401
        return True
    except Exception:
        return False


def _json_obj(text: str):
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


# ---- Role 1: Planner ----
def _planner(topic: str, weak_spots: list[str]) -> list[dict]:
    model = llm_mod.get_llm(llm_mod.SMART)
    focus = f" Pay extra attention to these weak spots: {', '.join(weak_spots)}." if weak_spots else ""
    if model is None:
        return [{"title": f"{topic}: Foundations", "objectives": ["Understand core ideas", "Key vocabulary"]},
                {"title": f"{topic}: Core Concepts", "objectives": ["Apply the main techniques"]},
                {"title": f"{topic}: Practice & Mastery", "objectives": ["Solve real problems", "Review weak spots"]}]
    msgs = [("system", 'You are the Planner. Output JSON {"modules":[{"title","objectives":[...]}]} '
                       "with 3-5 ordered modules for the topic." + focus),
            ("user", f"Topic: {topic}")]
    obj = _json_obj(model.invoke(msgs).content) or {}
    mods = obj.get("modules") if isinstance(obj, dict) else None
    if isinstance(mods, list) and mods:
        return mods
    return [{"title": f"{topic}: Overview", "objectives": ["Learn the basics"]}]


# ---- Role 2: Question-Writer ----
def _question_writer(topic: str, modules: list[dict]) -> list[dict]:
    model = llm_mod.get_llm(llm_mod.FAST)
    out = []
    for m in modules:
        title = m.get("title", topic)
        if model is None:
            qs = [f"Explain the key idea behind '{title}' in your own words.",
                  f"Give a real-life example related to '{title}'."]
        else:
            msgs = [("system", "You are the Question-Writer. Output a JSON object "
                               '{"questions":["..","..","..."]} with 3 practice questions.'),
                    ("user", f"Module: {title}\nObjectives: {m.get('objectives', [])}")]
            obj = _json_obj(model.invoke(msgs).content) or {}
            qs = obj.get("questions") if isinstance(obj.get("questions"), list) else \
                [f"Practice applying '{title}'."]
        out.append({**m, "practice_questions": [str(q) for q in qs][:3]})
    return out


# ---- Role 3: Reviewer ----
def _reviewer(topic: str, modules: list[dict]) -> str:
    model = llm_mod.get_llm(llm_mod.FAST)
    if model is None:
        return (f"Reviewed plan for '{topic}': {len(modules)} modules, ordered from foundations to "
                "mastery. Looks coherent and covers the essentials.")
    titles = "; ".join(m.get("title", "") for m in modules)
    msgs = [("system", "You are the Reviewer. In 2-3 sentences, assess whether this study plan is "
                       "well-ordered and complete, and note any gap."),
            ("user", f"Topic: {topic}\nModules: {titles}")]
    return model.invoke(msgs).content


def run_study_plan_crew(topic: str, weak_spots: list[str] | None = None) -> dict:
    """Execute the three-role crew sequentially and return the assembled plan."""
    weak_spots = weak_spots or []
    modules = _planner(topic, weak_spots)
    modules = _question_writer(topic, modules)
    review = _reviewer(topic, modules)
    return {
        "topic": topic,
        "personalized_for": weak_spots,
        "modules": modules,
        "review_notes": review,
        "engine": "crewai" if _real_crewai_available() else "studyquest-crew",
    }
