#!/usr/bin/env python3
"""Prepare a GitHub Pages update by advancing its shared cache version."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ("index.html", "travel.html", "accommodations.html", "explore.html")
META = re.compile(r'(<meta name="site-version" content=")(\d+)(">)')
SCRIPT = re.compile(r'(<script src="version-check\.js\?v=)(\d+)(" defer></script>)')


def read_version():
    version = json.loads((ROOT / "version.json").read_text(encoding="utf-8"))["version"]
    if not isinstance(version, str) or not version.isdecimal():
        raise ValueError("version.json must contain a decimal string version")
    return version


def updated_page(page, previous, following):
    text = (ROOT / page).read_text(encoding="utf-8")
    for label, pattern in (("meta", META), ("script", SCRIPT)):
        matches = pattern.findall(text)
        if len(matches) != 1 or matches[0][1] != previous:
            raise ValueError(f"{page}: expected exactly one {label} version {previous}")
        text = pattern.sub(lambda m: m[1] + following + m[3], text, count=1)
    return text


def main():
    previous = read_version()
    following = str(int(previous) + 1)
    # Validate every file before modifying any of them.
    pages = {page: updated_page(page, previous, following) for page in PAGES}
    for page, content in pages.items():
        (ROOT / page).write_text(content, encoding="utf-8")
    (ROOT / "version.json").write_text(
        json.dumps({"version": following}, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Prepared site version {following}. Commit the HTML files and version.json together.")


if __name__ == "__main__":
    main()