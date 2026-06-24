"""Phase 4 API: turn a YouTube playlist into a trackable course roadmap, with
per-video completion, summaries, transcript Q&A, and quizzes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents import course_agent
from app.agents.code_review import review_code
from app.api.deps import get_current_user
from app.sandbox import run_code
from app.database import get_db
from app.models.course import Course, CourseStep
from app.models.user import User
from app.youtube import YouTubeError, fetch_playlist, fetch_transcript, format_duration

router = APIRouter(prefix="/courses", tags=["courses"])


# ---------- serialization helpers ----------

def _step_json(s: CourseStep) -> dict:
    est = course_agent.estimate_step_seconds(s.duration_seconds)
    return {
        "id": s.id, "ordinal": s.ordinal, "video_id": s.video_id, "title": s.title,
        "duration": format_duration(s.duration_seconds),
        "estimated": format_duration(est),
        "completed": s.completed, "quiz_passed": s.quiz_passed,
        "youtube_url": f"https://www.youtube.com/watch?v={s.video_id}",
    }


def _course_json(c: Course) -> dict:
    total = len(c.steps)
    done = sum(1 for s in c.steps if s.completed)
    est_total = sum(course_agent.estimate_step_seconds(s.duration_seconds) for s in c.steps)
    proficient = total > 0 and all(s.completed and s.quiz_passed for s in c.steps)
    return {
        "id": c.id, "title": c.title, "playlist_url": c.playlist_url,
        "total_steps": total, "completed_steps": done,
        "percent": round(100 * done / total) if total else 0,
        "estimated_total": format_duration(est_total),
        "proficient": proficient,
        "steps": [_step_json(s) for s in c.steps],
    }


def _get_owned_course(db: Session, course_id: str, user: User) -> Course:
    c = db.get(Course, course_id)
    if c is None or c.user_id != user.id:
        raise HTTPException(status_code=404, detail="Course not found")
    return c


def _get_owned_step(db: Session, course_id: str, step_id: str, user: User) -> CourseStep:
    _get_owned_course(db, course_id, user)
    s = db.get(CourseStep, step_id)
    if s is None or s.course_id != course_id:
        raise HTTPException(status_code=404, detail="Step not found")
    return s


# ---------- ingestion + roadmap ----------

class CourseIn(BaseModel):
    playlist_url: str


@router.post("", status_code=201)
def create_course(payload: CourseIn, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    url = payload.playlist_url.strip()
    if "list=" not in url and "playlist" not in url:
        raise HTTPException(status_code=400, detail="Please paste a YouTube PLAYLIST link (contains 'list=').")
    try:
        title, videos = fetch_playlist(url)
    except YouTubeError as e:
        # 502: upstream/network problem, not the client's fault.
        raise HTTPException(status_code=502, detail=str(e))

    course = Course(user_id=user.id, title=title, playlist_url=url,
                    total_seconds=sum(v.duration_seconds for v in videos))
    db.add(course)
    db.flush()
    for i, v in enumerate(videos):
        db.add(CourseStep(course_id=course.id, ordinal=i, video_id=v.video_id,
                          title=v.title, duration_seconds=v.duration_seconds))
    db.commit()
    db.refresh(course)
    return _course_json(course)


@router.get("")
def list_courses(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    courses = (db.query(Course).filter(Course.user_id == user.id)
               .order_by(Course.created_at.desc()).all())
    return [_course_json(c) for c in courses]


@router.get("/{course_id}")
def get_course(course_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _course_json(_get_owned_course(db, course_id, user))


# ---------- per-step actions ----------

@router.post("/{course_id}/steps/{step_id}/complete")
def complete_step(course_id: str, step_id: str, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    s = _get_owned_step(db, course_id, step_id, user)
    s.completed = True
    db.commit()
    return _course_json(_get_owned_course(db, course_id, user))


@router.post("/{course_id}/steps/{step_id}/summarize")
def summarize_step(course_id: str, step_id: str, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    s = _get_owned_step(db, course_id, step_id, user)
    try:
        segments = fetch_transcript(s.video_id)
    except YouTubeError as e:
        return {"summary": f"⚠️ {e}"}
    return {"summary": course_agent.summarize(s.title, segments)}


class AskIn(BaseModel):
    question: str


@router.post("/{course_id}/steps/{step_id}/ask")
def ask_step(course_id: str, step_id: str, payload: AskIn,
             user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = _get_owned_step(db, course_id, step_id, user)
    try:
        segments = fetch_transcript(s.video_id)
    except YouTubeError as e:
        return {"answer": f"⚠️ {e}", "citations": []}
    return course_agent.answer_about_video(s.title, payload.question, segments)


@router.post("/{course_id}/steps/{step_id}/quiz")
def quiz_step(course_id: str, step_id: str, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    s = _get_owned_step(db, course_id, step_id, user)
    try:
        segments = fetch_transcript(s.video_id)
    except YouTubeError:
        segments = []
    return course_agent.generate_quiz(s.title, segments)


class GradeIn(BaseModel):
    question: str
    selected: str


@router.post("/{course_id}/steps/{step_id}/quiz/grade")
def grade_step(course_id: str, step_id: str, payload: GradeIn,
               user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = _get_owned_step(db, course_id, step_id, user)
    try:
        segments = fetch_transcript(s.video_id)
    except YouTubeError:
        segments = []
    result = course_agent.grade_answer(s.title, payload.question, payload.selected, segments)
    if result["correct"]:
        s.quiz_passed = True
        db.commit()
    return result


class CodeReviewIn(BaseModel):
    language: str = "python"
    code: str
    task: str = ""


@router.post("/{course_id}/steps/{step_id}/code-review")
def code_review_step(course_id: str, step_id: str, payload: CodeReviewIn,
                     user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """For coding courses: run the student's code and review it. The step is only
    marked truly complete when the Code-Review agent returns a PASS verdict."""
    s = _get_owned_step(db, course_id, step_id, user)
    run = run_code(payload.language, payload.code)
    review = review_code(payload.language, payload.code, run, payload.task)
    if review["approved"]:
        s.completed = True
        s.quiz_passed = True
        db.commit()
    return {"run": run, **review, "course": _course_json(_get_owned_course(db, course_id, user))}
