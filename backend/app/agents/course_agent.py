"""Course agent: summarize a video, run a quiz with a real-life-example
fallback on wrong answers, and answer questions about a specific video using
its transcript (with timestamp citations)."""
from __future__ import annotations

import re

from app.agents import llm as llm_mod
from app.youtube import format_duration

# Per-step time estimate = video length + a fixed buffer for the quiz & notes.
QUIZ_BUFFER_SECONDS = 5 * 60


def estimate_step_seconds(duration_seconds: int) -> int:
    return max(duration_seconds, 0) + QUIZ_BUFFER_SECONDS


def transcript_text(segments: list[dict]) -> str:
    return " ".join(s.get("text", "") for s in segments)


def _ts(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


def summarize(title: str, segments: list[dict]) -> str:
    text = transcript_text(segments)[:6000]
    model = llm_mod.get_llm(llm_mod.FAST)
    if model is None:
        preview = text[:280] if text else "(no transcript available)"
        return f"🔧 (mock summary) '{title}' — {preview}…"
    msgs = [("system", "Summarize this video transcript for a learner in 4-6 bullet points, "
                       "then one sentence on why it matters."),
            ("user", f"Title: {title}\n\nTranscript:\n{text}")]
    return model.invoke(msgs).content


def generate_quiz(title: str, segments: list[dict]) -> dict:
    """Return one multiple-choice question. Correct answer stays server-side
    (the client posts the chosen option back to /quiz/grade)."""
    text = transcript_text(segments)[:4000]
    model = llm_mod.get_llm(llm_mod.FAST)
    if model is None:
        return {
            "question": f"What was the main idea of '{title}'?",
            "options": ["The key concept it taught", "An unrelated topic",
                        "Nothing in particular", "A different subject"],
        }
    msgs = [("system", "Write ONE multiple-choice question testing the core concept of this video. "
                       "Output exactly:\nQ: <question>\nA) ..\nB) ..\nC) ..\nD) ..\n"
                       "Do NOT reveal the answer."),
            ("user", f"Title: {title}\n\nTranscript:\n{text}")]
    raw = model.invoke(msgs).content
    q_match = re.search(r"Q:\s*(.+)", raw)
    options = re.findall(r"^[A-D]\)\s*(.+)$", raw, flags=re.MULTILINE)
    return {
        "question": q_match.group(1).strip() if q_match else f"What was the main idea of '{title}'?",
        "options": options[:4] if len(options) >= 2 else
                   ["The key concept", "An unrelated topic", "Nothing", "A different subject"],
    }


def grade_answer(title: str, question: str, selected: str, segments: list[dict]) -> dict:
    """Judge the learner's answer. On a wrong answer, explain the concept with a
    real-life example (the Phase-4 'until they get it' behavior)."""
    text = transcript_text(segments)[:4000]
    model = llm_mod.get_llm(llm_mod.SMART)
    if model is None:
        ok = bool(selected) and "unrelated" not in selected.lower() and "nothing" not in selected.lower()
        fb = ("Correct! 🎉" if ok else
              "Not quite. 🔧 (mock) Add an OPENROUTER_API_KEY and I'll explain the concept with a "
              "real-life example until it clicks.")
        return {"correct": ok, "feedback": fb}
    msgs = [("system", "You are grading a learner's quiz answer about a video. Decide if it's "
                       "correct. Reply with 'CORRECT' or 'INCORRECT' on the first line. If "
                       "INCORRECT, then explain the concept clearly WITH a concrete real-life "
                       "example so they finally get it."),
            ("user", f"Video: {title}\nTranscript (context): {text}\n\n"
                     f"Question: {question}\nLearner's answer: {selected}")]
    out = model.invoke(msgs).content
    correct = out.strip().upper().startswith("CORRECT")
    return {"correct": correct, "feedback": out}


def answer_about_video(title: str, question: str, segments: list[dict]) -> dict:
    """Video-RAG: retrieve the most relevant transcript windows (BM25) and
    answer with [mm:ss] timestamp citations."""
    from rank_bm25 import BM25Okapi

    # Build ~30s windows so citations point at a place in the video.
    windows: list[dict] = []
    buf, start = [], None
    for seg in segments:
        if start is None:
            start = seg.get("start", 0)
        buf.append(seg.get("text", ""))
        if seg.get("start", 0) - start >= 30:
            windows.append({"start": start, "text": " ".join(buf)})
            buf, start = [], None
    if buf:
        windows.append({"start": start or 0, "text": " ".join(buf)})
    if not windows:
        return {"answer": "This video has no transcript to search.", "citations": []}

    tok = lambda s: re.findall(r"[a-z0-9]+", s.lower())
    bm25 = BM25Okapi([tok(w["text"]) for w in windows])
    scores = bm25.get_scores(tok(question))
    top = [w for w, _ in sorted(zip(windows, scores), key=lambda x: x[1], reverse=True)[:3]]
    citations = [{"ref": _ts(w["start"]), "content": w["text"][:160]} for w in top]
    context = "\n\n".join(f"[{_ts(w['start'])}] {w['text']}" for w in top)

    model = llm_mod.get_llm(llm_mod.SMART)
    if model is None:
        return {"answer": f"🔧 (mock) Around [{citations[0]['ref']}]: {top[0]['text'][:200]}…",
                "citations": citations}
    msgs = [("system", "Answer the question using ONLY the transcript windows. Cite the [mm:ss] "
                       "timestamps you used. Add a real-life example if it helps."),
            ("user", f"Video: {title}\n\nWindows:\n{context}\n\nQuestion: {question}")]
    return {"answer": model.invoke(msgs).content, "citations": citations}
