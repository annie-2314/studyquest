"""Grounded answering: retrieve the student's own material and answer ONLY from
it, with inline citations. If nothing relevant is retrieved, say so rather than
falling back to the model's own (ungrounded) knowledge.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents import llm as llm_mod
from app.materials import store
from app.observability import langfuse_callbacks

# Low backstop: catches the degenerate "no overlap at all" case. Works across
# both the dense (fastembed) and sparse (mock) embedding scales. Semantic
# grounding ("say so if the sources don't cover it") is enforced in the prompt.
_SCORE_THRESHOLD = 0.05

_NOT_FOUND = ("I couldn't find anything about that in your uploaded materials. "
              "Try rephrasing, or add a source that covers it.")


def answer(db: Session, user_id: str, query: str, material_id: str | None = None,
           k: int = 4) -> dict:
    hits = store.search(db, user_id, query, k=k, material_id=material_id)
    relevant = [(c, s) for c, s in hits if s >= _SCORE_THRESHOLD]
    if not relevant:
        return {"answer": _NOT_FOUND, "citations": [], "grounded": False}

    citations = [{"ref": c.source, "page": c.page, "snippet": c.content[:160]}
                 for c, _ in relevant]
    context = "\n\n".join(f"[{i + 1}] (from {c.source})\n{c.content}"
                          for i, (c, _) in enumerate(relevant))

    model = llm_mod.get_llm(llm_mod.FAST)
    if model is None:
        top = relevant[0][0]
        return {
            "answer": f"From **{top.source}**:\n\n{top.content[:500]}",
            "citations": citations, "grounded": True,
        }

    system = (
        "You are a tutor answering strictly from the student's provided sources. "
        "Use ONLY the sources below — do not add outside facts. Cite the source "
        "inline like (from <source>) where you use it. If the sources don't "
        "contain the answer, say you can't find it in their materials. Be concise "
        "and use Markdown."
    )
    user = f"Sources:\n{context}\n\nQuestion: {query}"
    cbs = langfuse_callbacks()
    cfg = {"callbacks": cbs} if cbs else {}
    text = model.invoke([("system", system), ("user", user)], config=cfg).content
    return {"answer": text, "citations": citations, "grounded": True}
