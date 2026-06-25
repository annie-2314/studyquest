"""Offline tests for web-page text extraction (no network)."""
from app.web_ingest import extract_text


def test_extracts_title_and_strips_tags_and_scripts():
    html = """
    <html><head><title>  My Notes </title>
    <style>.x{color:red}</style></head>
    <body>
      <script>var a = 1;</script>
      <h1>Heading</h1>
      <p>First &amp; important paragraph.</p>
      <p>Second paragraph.</p>
    </body></html>
    """
    title, text = extract_text(html, "text/html; charset=utf-8")
    assert title == "My Notes"
    assert "First & important paragraph." in text
    assert "Second paragraph." in text
    # script/style contents must not leak into the readable text
    assert "var a" not in text and "color:red" not in text
    assert "<" not in text  # no stray tags


def test_plaintext_passthrough():
    title, text = extract_text("just some plain text", "text/plain")
    assert title == ""
    assert text == "just some plain text"
