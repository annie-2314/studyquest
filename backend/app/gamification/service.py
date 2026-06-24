"""Gamification engine: XP, levels, daily streaks, badges, leaderboard.

Levels use a simple 100-XP band so progress is legible. Streaks compare the
last-active date to today (UTC). Badges are awarded either by XP threshold or
by an explicit key (e.g. course_complete, code_master) from other features.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.game import GameProfile, UserBadge
from app.models.user import User

XP_PER_LEVEL = 100

# key -> (emoji, name, xp_threshold or None for event-awarded)
BADGES: dict[str, tuple[str, str, int | None]] = {
    "first_xp": ("✨", "First Steps", 10),
    "centurion": ("💯", "Centurion (100 XP)", 100),
    "scholar": ("🎓", "Scholar (500 XP)", 500),
    "streak_3": ("🔥", "3-Day Streak", None),
    "streak_7": ("⚡", "7-Day Streak", None),
    "course_complete": ("🏆", "Course Complete", None),
    "code_master": ("💻", "Code Master", None),
}

# XP awards for common actions (kept here so values live in one place).
XP_STEP_COMPLETE = 20
XP_QUIZ_PASS = 15
XP_CODE_PASS = 30
XP_MINIGAME_WIN = 10


def level_for_xp(xp: int) -> int:
    return 1 + xp // XP_PER_LEVEL


def xp_into_level(xp: int) -> int:
    return xp % XP_PER_LEVEL


def get_profile(db: Session, user_id: str) -> GameProfile:
    p = db.get(GameProfile, user_id)
    if p is None:
        p = GameProfile(user_id=user_id, xp=0, streak_count=0, longest_streak=0, last_active="")
        db.add(p)
        db.commit()
        db.refresh(p)
    return p


def _has_badge(db: Session, user_id: str, key: str) -> bool:
    return db.query(UserBadge).filter(
        UserBadge.user_id == user_id, UserBadge.badge_key == key).first() is not None


def award_badge(db: Session, user_id: str, key: str) -> bool:
    """Grant a badge if not already earned. Returns True if newly awarded."""
    if key not in BADGES or _has_badge(db, user_id, key):
        return False
    db.add(UserBadge(user_id=user_id, badge_key=key))
    db.commit()
    return True


def _touch_streak(db: Session, p: GameProfile) -> None:
    today = date.today().isoformat()
    if p.last_active == today:
        return
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    p.streak_count = p.streak_count + 1 if p.last_active == yesterday else 1
    p.longest_streak = max(p.longest_streak, p.streak_count)
    p.last_active = today
    db.commit()


def _check_badges(db: Session, p: GameProfile) -> list[str]:
    newly: list[str] = []
    for key, (_emoji, _name, threshold) in BADGES.items():
        if threshold is not None and p.xp >= threshold and award_badge(db, p.user_id, key):
            newly.append(key)
    if p.streak_count >= 3 and award_badge(db, p.user_id, "streak_3"):
        newly.append("streak_3")
    if p.streak_count >= 7 and award_badge(db, p.user_id, "streak_7"):
        newly.append("streak_7")
    return newly


def award_xp(db: Session, user_id: str, amount: int, reason: str = "") -> dict:
    """Add XP, refresh the daily streak, and award any newly-earned badges."""
    p = get_profile(db, user_id)
    _touch_streak(db, p)
    p.xp += max(0, amount)
    db.commit()
    newly = _check_badges(db, p)
    return profile_json(db, p, newly_earned=newly, last_reason=reason)


def badge_list(db: Session, user_id: str) -> list[dict]:
    earned = {b.badge_key for b in db.query(UserBadge).filter(UserBadge.user_id == user_id).all()}
    return [{"key": k, "emoji": e, "name": n, "earned": k in earned}
            for k, (e, n, _t) in BADGES.items()]


def profile_json(db: Session, p: GameProfile, newly_earned: list[str] | None = None,
                 last_reason: str = "") -> dict:
    return {
        "xp": p.xp,
        "level": level_for_xp(p.xp),
        "xp_into_level": xp_into_level(p.xp),
        "xp_per_level": XP_PER_LEVEL,
        "streak": p.streak_count,
        "longest_streak": p.longest_streak,
        "badges": badge_list(db, p.user_id),
        "newly_earned": newly_earned or [],
        "last_reason": last_reason,
    }


def leaderboard(db: Session, limit: int = 10) -> list[dict]:
    rows = (db.query(GameProfile, User).join(User, User.id == GameProfile.user_id)
            .order_by(GameProfile.xp.desc()).limit(limit).all())
    return [{"display_name": u.display_name, "xp": gp.xp, "level": level_for_xp(gp.xp),
             "streak": gp.streak_count} for gp, u in rows]
