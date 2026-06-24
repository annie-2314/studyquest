"""Vision agent: read a photo of a handwritten problem / textbook page and
explain or solve it. Uses OpenRouter multimodal (base64 data URL) via the
OpenAI-compatible content format."""
from __future__ import annotations

import base64

from app.agents import llm as llm_mod

_SYSTEM = (
    "You are StudyQuest's vision tutor. The user uploaded a photo of a problem "
    "or page. Read it carefully, state what you see, then explain and solve it "
    "step by step with a real-life example where useful. If the image is "
    "unreadable, say so and ask for a clearer photo."
)


def solve_image(image_bytes: bytes, mime: str, question: str = "") -> str:
    model = llm_mod.get_llm(llm_mod.SMART)
    if model is None:
        return ("🔧 (mock vision tutor) I received your image "
                f"({len(image_bytes)} bytes, {mime}). Add an OPENROUTER_API_KEY "
                "and I'll read and solve the problem in the photo step by step.")

    b64 = base64.b64encode(image_bytes).decode()
    data_url = f"data:{mime};base64,{b64}"
    user_text = question.strip() or "Please read and solve the problem in this image."
    # OpenAI-compatible multimodal content: text + image_url parts.
    from langchain_core.messages import HumanMessage, SystemMessage

    messages = [
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=[
            {"type": "text", "text": user_text},
            {"type": "image_url", "image_url": {"url": data_url}},
        ]),
    ]
    result = model.invoke(messages)
    return result.content
