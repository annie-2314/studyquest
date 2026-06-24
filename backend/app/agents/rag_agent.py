"""RAG answer agent: retrieve grounding chunks, then answer WITH citations.

Every answer is grounded to its source_ref handles (the Phase-10 'citations'
requirement starts here and is reused by video RAG in Phase 6)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents import llm as llm_mod
from app.rag import store

_SYSTEM = (
    "You are StudyQuest's grounded tutor. Answer ONLY from the provided context "
    "passages. Cite the passages you use with their [ref] tags. If the context "
    "doesn't contain the answer, say so honestly. Keep it clear and include a "
    "real-life example when it helps."
)


def answer(db: Session, user_id: str, query: str, document_id: str | None = None) -> dict:
    chunks = store.search(db, user_id, query, k=4, document_id=document_id)
    if not chunks:
        return {"answer": "There's nothing in your knowledge base yet. Add a document first.",
                "citations": []}

    context = "\n\n".join(f"[{c.source_ref}] {c.content}" for c in chunks)
    citations = [{"ref": c.source_ref, "content": c.content[:200]} for c in chunks]

    model = llm_mod.get_llm(llm_mod.SMART)
    if model is None:
        top = chunks[0]
        return {
            "answer": (f"🔧 (mock RAG) Based on [{top.source_ref}]: {top.content[:300]}…\n\n"
                       "Add an OPENROUTER_API_KEY for a synthesized, cited answer."),
            "citations": citations,
        }
    msgs = [("system", _SYSTEM),
            ("user", f"Context passages:\n{context}\n\nQuestion: {query}")]
    result = model.invoke(msgs)
    return {"answer": result.content, "citations": citations}
