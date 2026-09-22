"""ADR-0009 (linkling-api): the public site carries no third-party asset, script
or embed. This reads site/*.html and site/*.css directly rather than a running
container -- the Dockerfile copies site/ into nginx verbatim with no templating
(ADR-0008), so the files on disk are byte-for-byte what gets served.
"""
import re
from pathlib import Path

SITE_DIR = Path(__file__).resolve().parent.parent / "site"

HTML_URL_ATTR = re.compile(
    r"""(?:href|src|srcset)\s*=\s*["']([^"']+)["']""", re.IGNORECASE
)
CSS_URL_FUNC = re.compile(r"""url\(\s*['"]?([^'")]+)['"]?\s*\)""", re.IGNORECASE)
CSS_IMPORT = re.compile(r"""@import\s+["']?([^"';]+)["']?""", re.IGNORECASE)
SCRIPT_TAG = re.compile(r"<script\b", re.IGNORECASE)


def _is_remote(url: str) -> bool:
    return url.strip().lower().startswith(("http://", "https://", "//"))


def _references_remote(attr_value: str) -> bool:
    # srcset is a comma-separated list of "<url> <descriptor>" candidates;
    # href/src/a CSS url() are a single candidate. Checking each element the
    # same way covers both without needing two code paths.
    return any(
        _is_remote((candidate.strip().split() or [""])[0])
        for candidate in attr_value.split(",")
    )


def test_no_third_party_reference_in_served_site():
    html_files = sorted(SITE_DIR.glob("*.html"))
    css_files = sorted(SITE_DIR.glob("*.css"))
    assert html_files, f"blind: no HTML files found in {SITE_DIR} -- nothing was checked"
    assert css_files, f"blind: no CSS files found in {SITE_DIR} -- nothing was checked"

    violations = []

    for path in html_files:
        text = path.read_text(encoding="utf-8")
        for match in HTML_URL_ATTR.finditer(text):
            if _references_remote(match.group(1)):
                violations.append(f"{path.name}: remote reference {match.group(0)!r}")
        if SCRIPT_TAG.search(text):
            violations.append(f"{path.name}: loads a <script>")

    for path in css_files:
        text = path.read_text(encoding="utf-8")
        for match in CSS_URL_FUNC.finditer(text):
            if _is_remote(match.group(1)):
                violations.append(f"{path.name}: remote url() {match.group(0)!r}")
        for match in CSS_IMPORT.finditer(text):
            if _is_remote(match.group(1)):
                violations.append(f"{path.name}: remote @import {match.group(0)!r}")

    assert not violations, "third-party reference(s) found:\n" + "\n".join(violations)
