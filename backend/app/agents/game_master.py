"""Game-Master agent: generates mini-game content (flashcards, fill-in-the-blank)
and boss-battle quiz questions. Mock-safe so the arcade works without a key."""
from __future__ import annotations

import json
import re

from app.agents import llm as llm_mod


def _parse_json_array(text: str):
    m = re.search(r"\[.*\]", text, flags=re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def flashcards(topic: str, n: int = 6) -> list[dict]:
    model = llm_mod.get_llm(llm_mod.FAST)
    if model is None:
        return [{"front": f"{topic}: key term {i + 1}", "back": f"Definition of term {i + 1}"}
                for i in range(min(n, 4))]
    msgs = [("system", f"Create {n} study flashcards as a JSON array of "
                       '{"front","back"} objects. Output ONLY the JSON array.'),
            ("user", f"Topic: {topic}")]
    data = _parse_json_array(model.invoke(msgs).content) or []
    cards = [{"front": str(c.get("front", "")), "back": str(c.get("back", ""))}
             for c in data if isinstance(c, dict)]
    return cards[:n]


def boss_quiz(topic: str, n: int = 5) -> list[dict]:
    """Timed boss-battle questions. Answers are included for client-side timed
    grading (acceptable for a casual mini-game)."""
    model = llm_mod.get_llm(llm_mod.FAST)
    if model is None:
        return [{
            "q": f"({topic}) Sample question {i + 1}?",
            "options": ["Correct answer", "Wrong A", "Wrong B", "Wrong C"],
            "answer_index": 0,
        } for i in range(min(n, 3))]
    msgs = [("system", f"Create {n} multiple-choice quiz questions as a JSON array of "
                       '{"q","options"(4 strings),"answer_index"(0-3)} objects. '
                       "Output ONLY the JSON array."),
            ("user", f"Topic: {topic}")]
    data = _parse_json_array(model.invoke(msgs).content) or []
    out = []
    for item in data:
        if isinstance(item, dict) and isinstance(item.get("options"), list) and len(item["options"]) >= 2:
            out.append({
                "q": str(item.get("q", "")),
                "options": [str(o) for o in item["options"]][:4],
                "answer_index": int(item.get("answer_index", 0)) % len(item["options"][:4]),
            })
    return out[:n]
