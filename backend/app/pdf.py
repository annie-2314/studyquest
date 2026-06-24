"""Render a study plan to a PDF study guide (fpdf2, pure-python)."""
from __future__ import annotations

from fpdf import FPDF
from fpdf.enums import XPos, YPos


def _clean(text: str) -> str:
    # fpdf2 core fonts are latin-1; drop unsupported chars (e.g. emoji) safely.
    return str(text).encode("latin-1", "replace").decode("latin-1")


def build_study_guide_pdf(plan: dict) -> bytes:
    pdf = FPDF()
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    w = pdf.epw  # effective page width (avoids w=0 edge cases)

    def line(text: str, size: int, style: str = "", gap: int = 7):
        pdf.set_font("Helvetica", style, size)
        pdf.multi_cell(w, gap, _clean(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    line(f"StudyQuest Guide: {plan.get('topic', '')}", 20, "B", gap=10)
    if plan.get("personalized_for"):
        line("Personalized for weak spots: " + ", ".join(plan["personalized_for"]), 11, "I")
    pdf.ln(2)

    for i, m in enumerate(plan.get("modules", []), 1):
        line(f"{i}. {m.get('title', '')}", 14, "B", gap=8)
        for obj in m.get("objectives", []):
            line(f"   - {obj}", 11)
        qs = m.get("practice_questions", [])
        if qs:
            line("   Practice questions:", 11, "B")
            for q in qs:
                line(f"     * {q}", 11)
        pdf.ln(2)

    if plan.get("review_notes"):
        pdf.ln(2)
        line("Reviewer notes", 12, "B", gap=8)
        line(plan["review_notes"], 11)

    return bytes(pdf.output())
