"""LangGraph SUPERVISOR.

WHY LangGraph here (vs CrewAI, which we use in Phase 8): the tutor is a
stateful, routed conversation — a single request must be classified and handed
to exactly one specialist, with per-student memory threaded through. LangGraph's
explicit StateGraph models that control flow precisely and gives us a hard
STEP BUDGET so the agent can never loop forever.

The compiled graph (route -> respond) is the canonical orchestration used by
the REST endpoint and tests. The WebSocket path reuses the same building blocks
(`classify_route`, `build_chat_messages`) to stream tokens live.
"""
from __future__ import annotations

from typing import AsyncIterator, TypedDict

from app.agents import llm as llm_mod
from app.agents.specialists import DEFAULT_ROUTE, specialist_prompt

# Hard cap on supervisor hops — defense against infinite agent loops.
STEP_BUDGET = 6

_PRACTICE_HINTS = ("quiz", "practice", "test me", "question", "exercise", "problem set")
_PROGRESS_HINTS = ("how am i doing", "my progress", "weak spot", "what should i", "am i ready")


def classify_route(message: str) -> str:
    """Deterministic intent routing (mock-safe). Real LLM classification can be
    layered on later; keeping it rule-based makes routing testable and free."""
    m = message.lower()
    if any(h in m for h in _PROGRESS_HINTS):
        return "progress_tracker"
    if any(h in m for h in _PRACTICE_HINTS):
        return "practice_question"
    return DEFAULT_ROUTE


def build_chat_messages(route: str, memory_ctx: str, history: list[dict], user_message: str):
    """Assemble the (role, content) list sent to the chat model."""
    system = specialist_prompt(route) + "\n\n[Learner profile]\n" + memory_ctx
    messages: list[tuple[str, str]] = [("system", system)]
    for h in history[-10:]:  # keep context bounded
        role = "assistant" if h.get("role") == "assistant" else "user"
        messages.append((role, h.get("content", "")))
    messages.append(("user", user_message))
    return messages


class TutorState(TypedDict, total=False):
    user_id: str
    user_message: str
    history: list
    memory_ctx: str
    route: str
    answer: str
    steps: int


def _supervisor_node(state: TutorState) -> TutorState:
    steps = state.get("steps", 0) + 1
    if steps > STEP_BUDGET:
        return {"route": DEFAULT_ROUTE, "steps": steps}
    return {"route": classify_route(state["user_message"]), "steps": steps}


def _respond_node(state: TutorState) -> TutorState:
    msgs = build_chat_messages(
        state["route"], state.get("memory_ctx", ""), state.get("history", []), state["user_message"]
    )
    model = llm_mod.get_llm(llm_mod.SMART)
    if model is None:
        system = msgs[0][1]
        return {"answer": llm_mod.mock_reply(system, state["user_message"])}
    result = model.invoke(msgs)
    return {"answer": result.content}


def build_supervisor_graph():
    """Compile the route -> respond StateGraph."""
    from langgraph.graph import END, START, StateGraph

    g = StateGraph(TutorState)
    g.add_node("supervisor", _supervisor_node)
    g.add_node("respond", _respond_node)
    g.add_edge(START, "supervisor")
    g.add_edge("supervisor", "respond")
    g.add_edge("respond", END)
    return g.compile()


_GRAPH = None


def _graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_supervisor_graph()
    return _GRAPH


def run_turn(user_id: str, history: list[dict], user_message: str, memory_ctx: str) -> dict:
    """Run one full supervised turn through the compiled graph (non-streaming)."""
    state = _graph().invoke({
        "user_id": user_id, "user_message": user_message,
        "history": history, "memory_ctx": memory_ctx, "steps": 0,
    })
    return {"route": state["route"], "answer": state["answer"]}


async def stream_turn(
    user_id: str, history: list[dict], user_message: str, memory_ctx: str
) -> AsyncIterator[tuple[str, str]]:
    """Stream a supervised turn. Yields ('route', route) first, then ('token', chunk)*.

    Reuses the supervisor's routing + prompt building so the streamed answer is
    identical in shape to the graph path."""
    route = classify_route(user_message)
    yield ("route", route)
    msgs = build_chat_messages(route, memory_ctx, history, user_message)
    model = llm_mod.get_llm(llm_mod.SMART)
    if model is None:
        text = llm_mod.mock_reply(msgs[0][1], user_message)
        async for tok in llm_mod.stream_text(text):
            yield ("token", tok)
        return
    async for chunk in model.astream(msgs):
        if chunk.content:
            yield ("token", chunk.content)
