"""Roadmap CREW — a role pipeline (Planner -> Resource-Curator -> Reviewer) that
turns a learning GOAL into a time-boxed roadmap.

The learner says what they want to be proficient in, how many hours/week they
can give, a target timeline, and a preferred language. The crew returns ordered
phases — each with what to cover, a time box, and resource links (including
YouTube lecture/playlist searches that always resolve, with no API key or
cookies needed).

Same rationale as the study-plan crew: a fixed pipeline of specialist roles is
CrewAI's sweet spot; we run it on the shared OpenRouter LLM layer so it works
with one key (and a deterministic mock when no key is set).
"""
from __future__ import annotations

import json
import re
import urllib.parse as _url

from app.agents import llm as llm_mod


def youtube_search_url(query: str) -> str:
    """A YouTube results URL for a query — always works, no API/cookies needed."""
    return "https://www.youtube.com/results?search_query=" + _url.quote_plus(query)


def _json_obj(text: str):
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def _real_crewai_available() -> bool:
    try:
        import crewai  # noqa: F401
        return True
    except Exception:
        return False


# ---- Role 1: Planner — break the goal into ordered, time-boxed phases ----
def _planner(goal: str, hours_per_week: int, timeline: str, language: str,
             weak_spots: list[str]) -> list[dict]:
    model = llm_mod.get_llm(llm_mod.SMART)
    if model is None:
        return [
            {"title": "Foundations", "duration": "Weeks 1-2",
             "topics": [f"Core concepts of {goal}", "Set up your tools", "Key vocabulary"]},
            {"title": "Core Skills", "duration": "Weeks 3-5",
             "topics": [f"The main techniques of {goal}", "Hands-on practice"]},
            {"title": "Applied Practice", "duration": "Weeks 6-7",
             "topics": ["Build a small project", "Apply what you learned"]},
            {"title": "Proficiency & Review", "duration": "Week 8",
             "topics": ["Review weak spots", "Tackle a capstone challenge"]},
        ]
    lang = f" Preferred language: {language}." if language.strip() else ""
    focus = f" Give extra attention to: {', '.join(weak_spots)}." if weak_spots else ""
    sys = (
        "You are a learning-path Planner. Build a realistic, ordered roadmap that takes a "
        "learner from beginner to proficient. Output ONLY JSON: "
        '{"phases":[{"title","duration","topics":[3-6 strings],'
        '"youtube_queries":[2-3 short search phrases for lectures or playlists]}]}. '
        "Use 4-7 phases. 'duration' should be a time box (e.g. 'Weeks 1-2') that fits the "
        "learner's available time and target timeline. youtube_queries must be specific "
        "(include the language/tool where relevant)."
    )
    user = (f"Goal — become proficient in: {goal}\n"
            f"Available time: ~{hours_per_week} hours/week\n"
            f"Target timeline: {timeline}.{lang}{focus}")
    obj = _json_obj(model.invoke([("system", sys), ("user", user)]).content) or {}
    phases = obj.get("phases") if isinstance(obj, dict) else None
    if isinstance(phases, list) and phases:
        return phases
    return [{"title": f"Learn {goal}", "duration": timeline,
             "topics": ["Start with the fundamentals"], "youtube_queries": [f"{goal} tutorial"]}]


# ---- Role 2: Resource-Curator — attach working resource links to each phase ----
def _curate(goal: str, language: str, phases: list[dict]) -> list[dict]:
    out = []
    for p in phases:
        title = p.get("title", goal)
        queries = p.get("youtube_queries")
        if not isinstance(queries, list) or not queries:
            base = f"{title} {goal}".strip()
            queries = [f"{base} tutorial", f"{base} full course"]
        # Bias queries toward the chosen language when one was given.
        suffix = f" {language}" if language.strip() else ""
        resources = [{"label": f"▶ {str(q)}", "url": youtube_search_url(f"{q}{suffix}")}
                     for q in queries[:3]]
        out.append({
            "title": title,
            "duration": p.get("duration", ""),
            "topics": [str(t) for t in (p.get("topics") or [])][:6],
            "resources": resources,
        })
    return out


# ---- Role 3: Reviewer — sanity-check the ordering/coverage ----
def _reviewer(goal: str, phases: list[dict], timeline: str) -> str:
    model = llm_mod.get_llm(llm_mod.FAST)
    if model is None:
        return (f"Reviewed roadmap for '{goal}': {len(phases)} phases ordered from foundations to "
                f"proficiency, scoped to {timeline}. Coverage looks coherent — adjust the pace to "
                "your weekly time.")
    titles = "; ".join(p.get("title", "") for p in phases)
    sys = ("You are the Reviewer. In 2-3 sentences, assess whether this roadmap is well-ordered "
           "and realistic for the timeline, and note one improvement.")
    user = f"Goal: {goal}\nTimeline: {timeline}\nPhases: {titles}"
    return model.invoke([("system", sys), ("user", user)]).content


def run_roadmap_crew(goal: str, *, hours_per_week: int = 5, timeline: str = "8 weeks",
                     language: str = "", weak_spots: list[str] | None = None) -> dict:
    """Execute the three-role crew and return an assembled roadmap."""
    weak_spots = weak_spots or []
    phases = _planner(goal, hours_per_week, timeline, language, weak_spots)
    phases = _curate(goal, language, phases)
    review = _reviewer(goal, phases, timeline)
    return {
        "goal": goal,
        "hours_per_week": hours_per_week,
        "timeline": timeline,
        "language": language,
        "personalized_for": weak_spots,
        "phases": phases,
        "review_notes": review,
        "engine": "crewai" if _real_crewai_available() else "studyquest-crew",
    }
