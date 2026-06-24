"""Per-student memory: load a compact profile and update it after each turn.

The update is heuristic + optional-LLM: we always append lightweight signals,
and when an LLM is available we let it refine the running summary. This keeps
memory working even in mock mode.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.learning import StudentMemory


def load_memory(db: Session, user_id: str) -> StudentMemory:
    mem = db.get(StudentMemory, user_id)
    if mem is None:
        mem = StudentMemory(user_id=user_id, summary="", weak_spots=[], strengths=[])
        db.add(mem)
        db.commit()
        db.refresh(mem)
    return mem


def memory_context(mem: StudentMemory) -> str:
    """Render the student's memory as a short system-context string."""
    parts = []
    if mem.summary:
        parts.append(f"Learner summary: {mem.summary}")
    if mem.weak_spots:
        parts.append("Known weak spots: " + ", ".join(mem.weak_spots))
    if mem.strengths:
        parts.append("Known strengths: " + ", ".join(mem.strengths))
    return "\n".join(parts) if parts else "No prior profile yet for this learner."


def note_topic(db: Session, user_id: str, topic: str, *, weak: bool) -> None:
    """Record a topic as a weak spot or strength (deduped, capped)."""
    mem = load_memory(db, user_id)
    topic = topic.strip()
    if not topic:
        return
    bucket = list(mem.weak_spots if weak else mem.strengths)
    if topic.lower() not in [t.lower() for t in bucket]:
        bucket.append(topic)
        bucket = bucket[-20:]  # cap growth
        if weak:
            mem.weak_spots = bucket
        else:
            mem.strengths = bucket
        db.commit()


def update_summary(db: Session, user_id: str, last_user_msg: str) -> None:
    """Keep a rolling one-line-ish summary of what the learner is working on.

    Mock-safe: appends the latest topic without needing the LLM. (A later phase
    can replace this with an LLM-distilled summary.)"""
    mem = load_memory(db, user_id)
    snippet = last_user_msg.strip().replace("\n", " ")[:120]
    if snippet:
        mem.summary = f"Recently working on: {snippet}"
        db.commit()
