"""Game-Master agent: generates mini-game content (flashcards, boss-battle quiz)
from a topic OR from the learner's own uploaded material. Mock-safe and
hardened so it never returns an empty set."""
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


def _topic_line(topic: str, context: str) -> str:
    if context:
        return f"Topic: {topic}\n\nBase the content ONLY on this material:\n{context[:4000]}"
    return f"Topic: {topic}"


def _fallback_cards(topic: str, n: int) -> list[dict]:
    return [{"front": f"{topic}: key idea {i + 1}", "back": f"A core point about {topic}."}
            for i in range(min(n, 4))]


def flashcards(topic: str, n: int = 6, context: str = "") -> list[dict]:
    """n flashcards. Uses the SMART model (better JSON adherence). Falls back to
    a non-empty placeholder set if the model output can't be parsed."""
    model = llm_mod.get_llm(llm_mod.SMART)
    if model is None:
        return _fallback_cards(topic, n)
    msgs = [("system", f"Create {n} study flashcards as a JSON array of "
                       '{"front","back"} objects. Output ONLY the JSON array, no prose.'),
            ("user", _topic_line(topic, context))]
    data = _parse_json_array(model.invoke(msgs).content) or []
    cards = [{"front": str(c.get("front", "")), "back": str(c.get("back", ""))}
             for c in data if isinstance(c, dict) and c.get("front")]
    return cards[:n] if cards else _fallback_cards(topic, n)


def _fallback_quiz(topic: str, n: int) -> list[dict]:
    return [{"q": f"({topic}) Sample question {i + 1}?",
             "options": ["Correct answer", "Wrong A", "Wrong B", "Wrong C"],
             "answer_index": 0} for i in range(min(n, 3))]


def boss_quiz(topic: str, n: int = 5, context: str = "") -> list[dict]:
    """Timed boss-battle questions. Answers are included for client-side timed
    grading (fine for a casual mini-game)."""
    model = llm_mod.get_llm(llm_mod.SMART)
    if model is None:
        return _fallback_quiz(topic, n)
    msgs = [("system", f"Create {n} multiple-choice quiz questions as a JSON array of "
                       '{"q","options"(4 strings),"answer_index"(0-3)} objects. '
                       "Output ONLY the JSON array, no prose."),
            ("user", _topic_line(topic, context))]
    data = _parse_json_array(model.invoke(msgs).content) or []
    out = []
    for item in data:
        if isinstance(item, dict) and isinstance(item.get("options"), list) and len(item["options"]) >= 2:
            opts = [str(o) for o in item["options"]][:4]
            out.append({"q": str(item.get("q", "")), "options": opts,
                        "answer_index": int(item.get("answer_index", 0)) % len(opts)})
    return out[:n] if out else _fallback_quiz(topic, n)
