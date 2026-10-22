"""Turn a Markdown report into one self-contained HTML file, with every picture embedded.

    .venv/Scripts/python.exe reports/make_html.py reports/first_round_report.md

The HTML file opens in any browser and can be passed on as a single file. The Markdown file stays the source.
"""

from __future__ import annotations

import base64
import re
import sys
from pathlib import Path

import markdown

CSS = """
body { font-family: Georgia, 'Times New Roman', serif; line-height: 1.55; color: #1f2328; background: #ffffff;
       max-width: 860px; margin: 2.5rem auto; padding: 0 1.2rem; }
h1, h2, h3 { font-family: 'Segoe UI', Helvetica, Arial, sans-serif; line-height: 1.25; }
h1 { font-size: 1.9rem; margin-bottom: 0.3rem; }
h2 { font-size: 1.4rem; margin-top: 2.4rem; border-bottom: 1px solid #d0d7de; padding-bottom: 0.3rem; }
h3 { font-size: 1.12rem; margin-top: 1.6rem; }
img { max-width: 100%; height: auto; border: 1px solid #d0d7de; margin: 0.6rem 0 0.2rem; }
table { border-collapse: collapse; margin: 1rem 0; font-size: 0.93rem; display: block; overflow-x: auto; }
th, td { border: 1px solid #d0d7de; padding: 0.35rem 0.6rem; text-align: left; vertical-align: top; }
th { background: #f3f5f7; font-family: 'Segoe UI', Helvetica, Arial, sans-serif; }
code { background: #f3f5f7; padding: 0.05rem 0.3rem; border-radius: 3px; font-size: 0.9em; }
blockquote { border-left: 4px solid #d0d7de; margin: 1rem 0; padding: 0.1rem 1rem; color: #57606a; }
em.caption, p.caption { color: #57606a; font-size: 0.92rem; }
"""


def embed_images(html: str, base: Path) -> str:
    def repl(match: re.Match) -> str:
        src = match.group(1)
        path = (base / src).resolve()
        if src.startswith(("http:", "https:", "data:")) or not path.exists():
            return match.group(0)
        kind = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "svg": "image/svg+xml"}[path.suffix[1:].lower()]
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        return f'src="data:{kind};base64,{data}"'

    return re.sub(r'src="([^"]+)"', repl, html)


def main() -> None:
    source = Path(sys.argv[1]).resolve()
    text = source.read_text(encoding="utf-8")
    title = next((line[2:].strip() for line in text.splitlines() if line.startswith("# ")), source.stem)
    body = markdown.markdown(text, extensions=["tables", "sane_lists", "toc"])
    html = (f'<!doctype html>\n<html lang="en-GB">\n<head>\n<meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">\n<title>{title}</title>\n'
            f"<style>{CSS}</style>\n</head>\n<body>\n{embed_images(body, source.parent)}\n</body>\n</html>\n")
    target = source.with_suffix(".html")
    target.write_bytes(html.encode("utf-8"))
    print(target.name, f"{len(html) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
