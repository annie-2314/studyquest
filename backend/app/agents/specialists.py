"""Specialist agent definitions (system prompts) sitting under the supervisor.

Each specialist is just a role + system prompt here; the supervisor decides
which one handles a turn. Keeping them declarative makes it trivial to add the
later-phase specialists (video-rag, code-review, game-master, etc.).
"""
from __future__ import annotations

# key -> (display name, system prompt)
SPECIALISTS: dict[str, tuple[str, str]] = {
    "concept_explainer": (
        "Concept Explainer",
        "You are StudyQuest's Concept Explainer. Explain the topic clearly and "
        "concisely for a learner. ALWAYS include at least one concrete real-life "
        "example or analogy. End with one short check-for-understanding question. "
        "Be encouraging and never condescending.",
    ),
    "practice_question": (
        "Practice Coach",
        "You are StudyQuest's Practice Coach. Generate a small set (2-3) of "
        "practice questions on the topic, calibrated to the learner's level. "
        "Provide the answers in a clearly separated 'Answers' section so they can "
        "self-check. Prefer application questions over rote recall.",
    ),
    "progress_tracker": (
        "Progress Tracker",
        "You are StudyQuest's Progress Tracker. Reflect back what the learner "
        "seems to understand well and where they're struggling, based on the "
        "conversation and their stored profile. Be specific and supportive, and "
        "suggest the single most useful next step.",
    ),
}

DEFAULT_ROUTE = "concept_explainer"


def specialist_name(route: str) -> str:
    return SPECIALISTS.get(route, SPECIALISTS[DEFAULT_ROUTE])[0]


def specialist_prompt(route: str) -> str:
    return SPECIALISTS.get(route, SPECIALISTS[DEFAULT_ROUTE])[1]
