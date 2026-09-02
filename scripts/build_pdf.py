"""Render a Markdown document to a print-ready PDF.

Markdown -> styled HTML -> PDF via headless Chrome. Kept in the repo so the
submission PDFs can be regenerated from source rather than maintained by hand
alongside it -- the documents and the code cannot drift apart if there is only
one copy of the text.

Usage:  python scripts/build_pdf.py docs/BUSINESS_PROPOSAL.md dist/Name.pdf
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import time
import tempfile
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
PROFILE = Path(tempfile.gettempdir()) / "mycroft-chrome-profile"

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]

CSS = """
@page { size: A4; margin: 18mm 16mm 20mm 16mm; }
:root {
  --ink: #10162e; --navy: #1e2761; --slate: #55607d;
  --line: #dfe3ee; --tint: #f4f6fb; --amber: #a5641a;
}
* { box-sizing: border-box; }
body {
  font-family: "Charter", "Cambria", Georgia, serif;
  color: var(--ink); font-size: 10.2pt; line-height: 1.52; margin: 0;
  -webkit-print-color-adjust: exact; print-color-adjust: exact;
}
h1 {
  font-family: "Helvetica Neue", Arial, sans-serif;
  font-size: 23pt; line-height: 1.15; color: var(--navy);
  margin: 0 0 4pt; letter-spacing: -0.4pt;
}
h2 {
  font-family: "Helvetica Neue", Arial, sans-serif;
  font-size: 14pt; color: var(--navy); margin: 22pt 0 7pt;
  padding-top: 10pt; border-top: 0.7pt solid var(--line);
  break-after: avoid; letter-spacing: -0.2pt;
}
h1 + p + hr + h2, h2:first-of-type { break-before: auto; }
h3 {
  font-family: "Helvetica Neue", Arial, sans-serif;
  font-size: 11pt; color: var(--ink); margin: 14pt 0 5pt; break-after: avoid;
}
p { margin: 0 0 7pt; }
strong { color: var(--navy); }
ul, ol { margin: 0 0 8pt; padding-left: 15pt; }
li { margin-bottom: 3pt; }
hr { border: none; height: 0; margin: 0; }
code {
  font-family: "SF Mono", Menlo, Consolas, monospace; font-size: 8.6pt;
  background: var(--tint); padding: 1pt 3pt; border-radius: 2pt; color: var(--navy);
}
pre {
  background: var(--tint); border: 0.7pt solid var(--line); border-radius: 3pt;
  padding: 8pt 10pt; overflow: hidden; break-inside: avoid; margin: 0 0 9pt;
}
pre code { background: none; padding: 0; font-size: 8.2pt; line-height: 1.42; color: var(--ink); }
blockquote {
  margin: 0 0 9pt; padding: 8pt 11pt; background: var(--tint);
  border-radius: 3pt; break-inside: avoid; color: var(--ink);
}
blockquote p:last-child { margin-bottom: 0; }
table {
  border-collapse: collapse; width: 100%; margin: 0 0 10pt;
  font-size: 8.9pt; break-inside: avoid;
}
th {
  font-family: "Helvetica Neue", Arial, sans-serif; font-size: 8.2pt;
  text-transform: uppercase; letter-spacing: 0.4pt; text-align: left;
  color: var(--slate); border-bottom: 1pt solid var(--navy);
  padding: 5pt 7pt 4pt; vertical-align: bottom;
}
td { padding: 5pt 7pt; border-bottom: 0.5pt solid var(--line); vertical-align: top; }
tbody tr:nth-child(even) { background: #fafbfe; }
.doc-header { margin-bottom: 16pt; }
.doc-header .sub {
  font-family: "Helvetica Neue", Arial, sans-serif; font-size: 9pt;
  color: var(--slate); margin-top: 2pt;
}
"""


def find_chrome() -> str:
    for c in CHROME_CANDIDATES:
        if Path(c).exists():
            return c
    for name in ("google-chrome", "chromium", "chromium-browser"):
        p = shutil.which(name)
        if p:
            return p
    raise SystemExit("No Chrome/Chromium found; install one or export CHROME=/path/to/binary")


def build(src: Path, out: Path) -> None:
    html_body = markdown.markdown(
        src.read_text(),
        extensions=["tables", "fenced_code", "sane_lists", "attr_list"],
    )
    page = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{src.stem}</title><style>{CSS}</style></head>"
        f"<body>{html_body}</body></html>"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        html_path = Path(tmp) / "doc.html"
        html_path.write_text(page)
        # Chrome writes the PDF and then does not always exit on macOS, so
        # run it detached, wait for the file to appear and settle, and stop it.
        if out.exists():
            out.unlink()
        proc = subprocess.Popen(
            [find_chrome(), "--headless=new", "--disable-gpu", "--no-sandbox",
             "--no-first-run", "--no-default-browser-check", "--disable-extensions",
             "--virtual-time-budget=6000", "--no-pdf-header-footer",
             f"--print-to-pdf={out}", f"--user-data-dir={PROFILE}",
             html_path.as_uri()],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        try:
            deadline = time.time() + 90
            last = -1
            while time.time() < deadline:
                if proc.poll() is not None:
                    break
                size = out.stat().st_size if out.exists() else -1
                if size > 0 and size == last:
                    break          # written and no longer growing
                last = size
                time.sleep(0.5)
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
        if not out.exists() or not out.stat().st_size:
            raise SystemExit(f"Chrome produced no PDF for {src}")

    def rel(path: Path) -> str:
        try:
            return str(path.resolve().relative_to(ROOT))
        except ValueError:
            return str(path)

    print(f"{rel(src)}  ->  {rel(out)}  ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    if len(sys.argv) == 3:
        build(Path(sys.argv[1]), Path(sys.argv[2]))
    else:
        for s, o in (
            ("docs/BUSINESS_PROPOSAL.md", "dist/Mycroft_AI_Business_Proposal.pdf"),
            ("README.md", "dist/Mycroft_AI_README.pdf"),
            ("docs/METHODOLOGY.md", "dist/Mycroft_AI_Methodology.pdf"),
            ("docs/ASSUMPTIONS.md", "dist/Mycroft_AI_Assumptions.pdf"),
            ("docs/VIDEO_BRIEF.md", "dist/Mycroft_AI_Video_Brief.pdf"),
        ):
            build(ROOT / s, ROOT / o)
