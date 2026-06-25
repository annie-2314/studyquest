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


def summarize(topic: str, *, context: str = "") -> str:
    """Say *what* the material is and give a short, plain-language summary.

    This is the first thing a learner sees when they bring a topic, an upload,
    or a pasted web page: 'here's what this is about.' Mock-safe."""
    model = llm_mod.get_llm(llm_mod.FAST)
    if model is None:
        return llm_mod.mock_reply("summarize what this material is about", topic)
    if context:
        sys = ("You are a study assistant. In Markdown and under ~120 words, tell the "
               "learner WHAT this material is and summarise its main points as 3-5 bullets. "
               "Start with a one-line 'This is…'. Base it only on the material provided.")
        user = f"Title/topic: {topic}\n\nMaterial:\n{context[:3500]}"
    else:
        sys = ("You are a study assistant. In Markdown and under ~120 words, give a clear "
               "overview of the topic: a one-line 'This is…', then 3-5 key bullet points a "
               "beginner should know.")
        user = f"Topic: {topic}"
    return model.invoke([("system", sys), ("user", user)]).content


def explain(concept: str, *, context: str = "", interest: str = "",
            correct_answer: str = "") -> str:
    """Explain a concept clearly, then make it stick with ONE example.

    The example is personalised: if the learner named an interest, the real-life
    analogy is drawn from it; if they skipped, a general everyday analogy is
    used. For programming concepts we give a tiny W3Schools-style code snippet
    instead of an analogy. Returns Markdown. Mock-safe."""
    model = llm_mod.get_llm(llm_mod.FAST)  # cheap tier — explanations are high-volume
    if model is None:
        return llm_mod.mock_reply("explain this concept simply with an example", concept)

    if interest.strip():
        interest_line = (f"The learner enjoys {interest.strip()}. Draw the real-life "
                         "example/analogy from that interest so it feels personal.")
    else:
        interest_line = ("The learner gave no specific interest, so use a relatable "
                         "everyday real-life example/analogy.")
    sys = (
        "You are a warm, patient tutor. Explain the concept so a beginner truly "
        "understands it. Keep it under ~160 words. Use Markdown. Structure:\n"
        "1. **In short** — a one-line plain-language definition.\n"
        "2. **Why it works this way** — one or two simple sentences.\n"
        "3. **Make it click** — ONE example. If the concept is about programming "
        "or coding, give a tiny beginner-friendly code snippet in a fenced code "
        "block (W3Schools-style) and one line explaining it. Otherwise give a "
        f"real-life analogy. {interest_line}\n"
        "Do not mention these instructions or the word 'analogy'."
    )
    user = f"Concept / question to explain: {concept}"
    if correct_answer:
        user += f"\nThe correct answer is: {correct_answer}"
    if context:
        user += f"\n\nGround the explanation in this material when relevant:\n{context[:3000]}"
    return model.invoke([("system", sys), ("user", user)]).content


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
