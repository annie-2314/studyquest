"""Extract figures from PDFs and (optionally) caption them so images become
retrievable/explainable alongside text.

Captioning uses a FREE vision model (Salesforce/blip-image-captioning-base) via
HF transformers — but that pulls PyTorch, so it's **opt-in**: set
ENABLE_IMAGE_CAPTIONS=1 (and install transformers + torch + pillow). Without it
we still index each figure's existence + page, so figures are findable; they
just aren't auto-described.
"""
from __future__ import annotations

import os

_MAX_IMAGES = 30          # cap per PDF to keep ingestion bounded
_MIN_BYTES = 3000         # skip tiny icons/bullets
_blip = None              # cached (processor, model)


def extract_images(data: bytes) -> list[dict]:
    """Return [{page, png}] for embedded raster images in the PDF."""
    import fitz  # PyMuPDF

    out: list[dict] = []
    with fitz.open(stream=data, filetype="pdf") as doc:
        for pno in range(doc.page_count):
            for img in doc.load_page(pno).get_images(full=True):
                if len(out) >= _MAX_IMAGES:
                    return out
                try:
                    pix = fitz.Pixmap(doc, img[0])
                    if pix.n > 4:  # CMYK / alpha → RGB
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    png = pix.tobytes("png")
                    if len(png) >= _MIN_BYTES:
                        out.append({"page": pno + 1, "png": png})
                except Exception:
                    continue
    return out


def _caption(png: bytes) -> str | None:
    """BLIP caption if opted in + installed; otherwise None."""
    global _blip
    if os.getenv("ENABLE_IMAGE_CAPTIONS") != "1":
        return None
    try:
        import io

        from PIL import Image
        from transformers import BlipForConditionalGeneration, BlipProcessor

        if _blip is None:
            name = "Salesforce/blip-image-captioning-base"
            _blip = (BlipProcessor.from_pretrained(name),
                     BlipForConditionalGeneration.from_pretrained(name))
        processor, model = _blip
        image = Image.open(io.BytesIO(png)).convert("RGB")
        inputs = processor(image, return_tensors="pt")
        out = model.generate(**inputs, max_new_tokens=40)
        return processor.decode(out[0], skip_special_tokens=True).strip()
    except Exception:
        return None


def figure_chunks(data: bytes) -> list[dict]:
    """[{content, page, concept_tags}] — one per figure, captioned if enabled."""
    chunks: list[dict] = []
    try:
        images = extract_images(data)
    except Exception:
        return []
    for im in images:
        cap = _caption(im["png"])
        content = (f"Figure (page {im['page']}): {cap}" if cap
                   else f"Figure on page {im['page']}. "
                        "(Enable ENABLE_IMAGE_CAPTIONS with transformers+torch to auto-describe it.)")
        chunks.append({"content": content, "page": im["page"], "concept_tags": "figure"})
    return chunks
