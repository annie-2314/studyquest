"""Mastery service: apply BKT on each attempt, persist per-concept state + a
time-series, and expose weak-concept / spaced-review queries that drive
adaptation.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.learning import bkt
from app.models.mastery import LearnerConceptMastery, MasteryEvent


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _interval_hours(p_known: float, correct: bool) -> int:
    """Spaced-repetition gap: wrong → revisit soon; higher mastery → longer gap."""
    if not correct:
        return 1
    if p_known < 0.5:
        return 4
    if p_known < 0.8:
        return 24
    return 72


def record_attempt(db: Session, user_id: str, concept: str, correct: bool):
    """Update mastery for one concept after a graded attempt. Returns the row."""
    concept = (concept or "").strip().lower()
    if not concept:
        return None
    row = (db.query(LearnerConceptMastery)
           .filter(LearnerConceptMastery.user_id == user_id,
                   LearnerConceptMastery.concept == concept).first())
    if row is None:
        row = LearnerConceptMastery(user_id=user_id, concept=concept, p_known=bkt.DEFAULT.p_init)
        db.add(row)
        db.flush()
    row.p_known = bkt.update(row.p_known, correct)
    row.attempts += 1
    row.correct += 1 if correct else 0
    row.last_seen = _now()
    row.due_at = _now() + timedelta(hours=_interval_hours(row.p_known, correct))
    db.add(MasteryEvent(user_id=user_id, concept=concept, p_known=row.p_known,
                        correct=1 if correct else 0))
    db.commit()
    db.refresh(row)
    return row


def record_many(db: Session, user_id: str, concepts: list[str], correct: bool) -> None:
    for c in concepts:
        record_attempt(db, user_id, c, correct)


def _row_json(r: LearnerConceptMastery) -> dict:
    return {"concept": r.concept, "p_known": round(r.p_known, 3),
            "attempts": r.attempts, "correct": r.correct,
            "last_seen": r.last_seen.isoformat() if r.last_seen else None,
            "due_at": r.due_at.isoformat() if r.due_at else None}


def mastery_overview(db: Session, user_id: str) -> dict:
    rows = (db.query(LearnerConceptMastery)
            .filter(LearnerConceptMastery.user_id == user_id)
            .order_by(LearnerConceptMastery.p_known.asc()).all())
    events = (db.query(MasteryEvent)
              .filter(MasteryEvent.user_id == user_id)
              .order_by(MasteryEvent.created_at.asc()).all())
    history = [{"concept": e.concept, "p_known": round(e.p_known, 3),
                "correct": e.correct,
                "at": e.created_at.isoformat() if e.created_at else None}
               for e in events]
    return {"concepts": [_row_json(r) for r in rows], "history": history}


def review_queue(db: Session, user_id: str, limit: int = 10) -> list[dict]:
    """Concepts due for review (due_at passed) or weakest-first."""
    now = _now()
    rows = (db.query(LearnerConceptMastery)
            .filter(LearnerConceptMastery.user_id == user_id).all())
    def _due(r):
        if r.due_at is None:
            return False
        # SQLite returns naive datetimes even for tz-aware columns — assume UTC.
        due = r.due_at if r.due_at.tzinfo else r.due_at.replace(tzinfo=timezone.utc)
        return due <= now
    rows.sort(key=lambda r: (not _due(r), r.p_known))
    out = []
    for r in rows[:limit]:
        d = _row_json(r)
        d["due"] = _due(r)
        out.append(d)
    return out


def weak_concepts(db: Session, user_id: str, n: int = 3) -> list[str]:
    rows = (db.query(LearnerConceptMastery)
            .filter(LearnerConceptMastery.user_id == user_id)
            .order_by(LearnerConceptMastery.p_known.asc()).limit(n).all())
    return [r.concept for r in rows]
