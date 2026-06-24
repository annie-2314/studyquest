"""Phase 9 API: student progress analytics + a teacher/parent overview."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.memory import load_memory
from app.api.deps import get_current_user
from app.database import get_db
from app.gamification import service as game
from app.models.course import Course, CourseStep
from app.models.learning import Conversation, Message
from app.models.user import User, UserRole

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _student_summary(db: Session, user: User) -> dict:
    profile = game.get_profile(db, user.id)
    courses = db.query(Course).filter(Course.user_id == user.id).all()
    course_rows = []
    completed_steps = 0
    for c in courses:
        total = len(c.steps)
        done = sum(1 for s in c.steps if s.completed)
        completed_steps += done
        course_rows.append({"title": c.title, "percent": round(100 * done / total) if total else 0})

    mem = load_memory(db, user.id)
    quizzes_passed = (db.query(CourseStep).join(Course)
                      .filter(Course.user_id == user.id, CourseStep.quiz_passed.is_(True)).count())
    msg_count = (db.query(Message).join(Conversation)
                 .filter(Conversation.user_id == user.id).count())

    return {
        "user": {"id": user.id, "display_name": user.display_name, "email": user.email, "role": user.role},
        "xp": profile.xp,
        "level": game.level_for_xp(profile.xp),
        "streak": profile.streak_count,
        "longest_streak": profile.longest_streak,
        "badges_earned": sum(1 for b in game.badge_list(db, user.id) if b["earned"]),
        "courses": course_rows,
        "completed_steps": completed_steps,
        "quizzes_passed": quizzes_passed,
        "messages": msg_count,
        "weak_spots": list(mem.weak_spots or []),
        "strengths": list(mem.strengths or []),
    }


@router.get("/me")
def my_analytics(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _student_summary(db, user)


@router.get("/students")
def students_overview(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Teacher/parent view of all students. Students may not access this."""
    if user.role not in (UserRole.TEACHER, UserRole.PARENT):
        raise HTTPException(status_code=403, detail="Teacher or parent access only")
    students = db.query(User).filter(User.role == UserRole.STUDENT).all()
    return [_student_summary(db, s) for s in students]
