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


def build_roadmap_pdf(roadmap: dict) -> bytes:
    """Render a learning roadmap (goal + time-boxed phases + resources) to PDF."""
    pdf = FPDF()
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    w = pdf.epw

    def line(text: str, size: int, style: str = "", gap: int = 7, link: str = ""):
        pdf.set_font("Helvetica", style, size)
        pdf.multi_cell(w, gap, _clean(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT,
                       link=link or None)

    line(f"Learning Roadmap: {roadmap.get('goal', '')}", 20, "B", gap=10)
    meta = []
    if roadmap.get("timeline"):
        meta.append(f"Timeline: {roadmap['timeline']}")
    if roadmap.get("hours_per_week"):
        meta.append(f"~{roadmap['hours_per_week']} hrs/week")
    if roadmap.get("language"):
        meta.append(f"Language: {roadmap['language']}")
    if meta:
        line(" · ".join(meta), 11, "I")
    if roadmap.get("personalized_for"):
        line("Focus areas: " + ", ".join(roadmap["personalized_for"]), 11, "I")
    pdf.ln(2)

    for i, p in enumerate(roadmap.get("phases", []), 1):
        head = f"{i}. {p.get('title', '')}"
        if p.get("duration"):
            head += f"  ({p['duration']})"
        line(head, 14, "B", gap=8)
        for t in p.get("topics", []):
            line(f"   - {t}", 11)
        res = p.get("resources", [])
        if res:
            line("   Resources:", 11, "B")
            for r in res:
                label = r.get("label", "") if isinstance(r, dict) else str(r)
                url = r.get("url", "") if isinstance(r, dict) else ""
                pdf.set_text_color(60, 90, 200)
                line(f"     {label} — {url}", 10, link=url)
                pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

    if roadmap.get("review_notes"):
        pdf.ln(2)
        line("Reviewer notes", 12, "B", gap=8)
        line(roadmap["review_notes"], 11)

    return bytes(pdf.output())
