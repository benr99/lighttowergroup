#!/usr/bin/env python3
"""Build docs/intelligence-system-map.html from data.js + engine.html.

Run after editing data.js:   python docs/system-map/build.py
Line counts are read from the real files, so the map never states a stale size.
"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
data = (HERE / "data.js").read_text(encoding="utf-8")
engine = (HERE / "engine.html").read_text(encoding="utf-8")


# Line counts mean something for code and prose, not for data or state files.
COUNTED = {".py", ".js", ".yml", ".yaml", ".html", ".css", ".md", ".txt"}


def add_lines(match: re.Match) -> str:
    path = ROOT / match.group(1)
    if path.is_file() and path.suffix.lower() in COUNTED:
        try:
            n = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
            return f"file:'{match.group(1)}', lines:{n}"
        except OSError:
            pass
    return match.group(0)


data = re.sub(r"file:'([^']+)'", add_lines, data)
out = engine.replace("/*__DATA__*/", data)
target = ROOT / "docs" / "intelligence-system-map.html"
target.write_text(out, encoding="utf-8")
print(f"wrote {target} ({len(out) / 1024:.0f} KB)")
