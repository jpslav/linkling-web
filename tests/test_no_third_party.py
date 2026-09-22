"""ADR-0009 (linkling-api): the public site carries no third-party asset, script
or embed. This reads site/**/*.html and site/**/*.css directly rather than a
running container -- the Dockerfile copies site/ into nginx verbatim with no
templating (ADR-0008), so the files on disk are byte-for-byte what gets served.

Every pattern below runs against every file's full text, not just the file
type "native" to its syntax: an inline style="" attribute or a <style> block
in HTML carries CSS syntax too, and a first pass that only ran the CSS checks
against *.css files missed exactly that.
"""
import re
from pathlib import Path

SITE_DIR = Path(__file__).resolve().parent.parent / "site"

HTML_URL_ATTR = re.compile(
    r"""(?:href|src|srcset)\s*=\s*["']([^"']+)["']""", re.IGNORECASE
)
CSS_URL_FUNC = re.compile(r"""url\(\s*['"]?([^'")]+)['"]?\s*\)""", re.IGNORECASE)
CSS_IMPORT = re.compile(
    r"""@import\s+(?:url\(\s*)?["']([^"']+)["']""", re.IGNORECASE
)
SCRIPT_TAG = re.compile(r"<script\b", re.IGNORECASE)


def _is_remote(url: str) -> bool:
    return url.strip().lower().startswith(("http://", "https://", "//"))


def _references_remote(attr_value: str) -> bool:
    # srcset is a comma-separated list of "<url> <descriptor>" candidates;
    # href/src is a single candidate. Checking each element the same way
    # covers both without needing two code paths.
    return any(
        _is_remote((candidate.strip().split() or [""])[0])
        for candidate in attr_value.split(",")
    )


def test_no_third_party_reference_in_served_site():
    files = sorted(SITE_DIR.rglob("*.html")) + sorted(SITE_DIR.rglob("*.css"))
    assert files, f"blind: no HTML or CSS files found in {SITE_DIR} -- nothing was checked"

    violations = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(SITE_DIR)

        for match in HTML_URL_ATTR.finditer(text):
            if _references_remote(match.group(1)):
                violations.append(f"{rel}: remote reference {match.group(0)!r}")
        for match in CSS_URL_FUNC.finditer(text):
            if _is_remote(match.group(1)):
                violations.append(f"{rel}: remote url() {match.group(0)!r}")
        for match in CSS_IMPORT.finditer(text):
            if _is_remote(match.group(1)):
                violations.append(f"{rel}: remote @import {match.group(0)!r}")
        if SCRIPT_TAG.search(text):
            violations.append(f"{rel}: loads a <script>")

    assert not violations, "third-party reference(s) found:\n" + "\n".join(violations)
