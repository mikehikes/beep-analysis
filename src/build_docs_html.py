"""Export executive_summary.ipynb to docs/index.html for GitHub Pages.

Code cells stay hidden (nbconvert's TagRemovePreprocessor strips the "hide-input"
tagged cells entirely, it does not just CSS-hide them), so no source code ships
in the published page.
"""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TITLE = "ATL Spoke Ridership — Executive Summary"

subprocess.run(
    ["uv", "run", "jupyter", "nbconvert", "--to", "html",
     "executive_summary.ipynb", "--output-dir", "docs", "--output", "index.html"],
    cwd=ROOT, check=True,
)

out = ROOT / "docs" / "index.html"
html = out.read_text()
html = re.sub(r"<title>.*?</title>", f"<title>{TITLE}</title>", html, count=1)
out.write_text(html)
print(f"docs/index.html written, title set to: {TITLE!r}")
