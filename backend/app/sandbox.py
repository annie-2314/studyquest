"""Best-effort sandboxed code runner.

WHY this exists / its limits: the spec wants student code executed safely. A
true sandbox is Judge0 or a Docker-isolated runner; that's the documented
production path. Here (native, no Docker) we run code in a SEPARATE PROCESS with
a hard timeout, output cap, isolated interpreter flags, and a throwaway temp
dir. This contains runaway loops and accidental output floods — it does NOT
fully contain malicious code, so it is intended for a learner running their own
code locally. Never expose this endpoint to untrusted multi-tenant traffic
without a real sandbox.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TIMEOUT_SECONDS = 6
MAX_OUTPUT_CHARS = 10_000

SUPPORTED = {"python", "javascript"}


def _truncate(text: str) -> str:
    return text if len(text) <= MAX_OUTPUT_CHARS else text[:MAX_OUTPUT_CHARS] + "\n…(truncated)"


def run_code(language: str, code: str, stdin: str = "") -> dict:
    language = language.lower()
    if language not in SUPPORTED:
        return {"ok": False, "stdout": "", "stderr": f"Unsupported language: {language}",
                "exit_code": -1, "timed_out": False}

    workdir = tempfile.mkdtemp(prefix="sq_run_")
    try:
        if language == "python":
            src = Path(workdir) / "main.py"
            src.write_text(code, encoding="utf-8")
            # -I = isolated mode (ignore env/user site), -B = no .pyc.
            cmd = [sys.executable, "-I", "-B", str(src)]
        else:  # javascript
            node = shutil.which("node")
            if not node:
                return {"ok": False, "stdout": "", "stderr": "Node.js is not installed on the server.",
                        "exit_code": -1, "timed_out": False}
            src = Path(workdir) / "main.js"
            src.write_text(code, encoding="utf-8")
            cmd = [node, str(src)]

        try:
            proc = subprocess.run(
                cmd, input=stdin, capture_output=True, text=True,
                timeout=TIMEOUT_SECONDS, cwd=workdir,
            )
        except subprocess.TimeoutExpired:
            return {"ok": False, "stdout": "", "stderr": f"Timed out after {TIMEOUT_SECONDS}s.",
                    "exit_code": -1, "timed_out": True}

        return {
            "ok": proc.returncode == 0,
            "stdout": _truncate(proc.stdout),
            "stderr": _truncate(proc.stderr),
            "exit_code": proc.returncode,
            "timed_out": False,
        }
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
