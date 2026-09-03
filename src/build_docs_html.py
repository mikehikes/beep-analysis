"""Export executive_summary.ipynb to docs/index.html for GitHub Pages.

Two fixes over a plain nbconvert export:

1. --no-input strips every code cell's input area from the DOM entirely (not
   just via a CSS/tag toggle), so no source ships in the published page and no
   empty collapsed-cell scaffolding is left behind.

2. nbconvert's default MathJax config enables single-`$` inline math
   (`inlineMath: [['$','$'], ...]`), and the markdown-to-HTML step drops a
   literal backslash before it reaches MathJax, so a backslash-escaped dollar
   sign in the source does NOT survive as an escape in the exported HTML. Any
   paragraph with two dollar amounts then gets typeset as italic maths. This
   report has no LaTeX in it, so the fix is to disable single-`$` delimiters
   in the exported page's MathJax config rather than rely on escaping, which
   this pipeline cannot make reliable.
"""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TITLE = "ATL Spoke Ridership — Summary"
REPO_URL = "https://github.com/mikehikes/beep-analysis"

subprocess.run(
    ["uv", "run", "jupyter", "nbconvert", "--to", "html", "--no-input",
     "executive_summary.ipynb", "--output-dir", "docs", "--output", "index.html"],
    cwd=ROOT, check=True,
)

out = ROOT / "docs" / "index.html"
html = out.read_text()

html = re.sub(r"<title>.*?</title>", f"<title>{TITLE}</title>", html, count=1)

# Single-`$` math off; keep \( \) and $$ $$, which nothing here uses anyway.
old_inline = "inlineMath: [ ['$','$'], [\"\\\\(\",\"\\\\)\"] ],"
new_inline = "inlineMath: [ [\"\\\\(\",\"\\\\)\"] ],"
assert old_inline in html, "MathJax inlineMath config not found; template changed"
html = html.replace(old_inline, new_inline)

repo_link = (
    f'<div style="max-width:900px;margin:0 auto;padding:12px 20px 0;'
    f'font-family:-apple-system,Segoe UI,sans-serif;font-size:13px">'
    f'<a href="{REPO_URL}" style="color:#0969da;text-decoration:none">'
    f"&larr; {REPO_URL.removeprefix('https://')}</a></div>"
)
assert "<body" in html
html = re.sub(r"(<body[^>]*>)", r"\1" + repo_link, html, count=1)

out.write_text(html)
print(f"docs/index.html written, title={TITLE!r}, single-$ math disabled, repo link added")
